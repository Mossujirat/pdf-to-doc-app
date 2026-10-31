"""The default OCR engine: PaddleOCR with the PP-OCRv5 mobile models, on the CPU.

The settings come from the October 2026 benchmark (docs/research):
- The detector's input is capped at 1280 px on its longest side. At full
  resolution it splits Thai marks into boxes of their own, and merges or skips lines.
- Orientation, unwarping and text-line orientation are off. A page fed in askew
  still has its boxes straightened (see `_straightened`).
- The Thai recogniser reads English words and digits on the same line correctly,
  so it serves both languages; the English recogniser cannot read Thai at all.
- A scan under a fine dot pattern, such as a certificate's watermark, is blurred and
  read again (see `_watermarked`).
"""

import logging
import math
import os
import warnings
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from pdf_to_doc.ocr import Language, OcrEngine, PageImage, TextBox
from pdf_to_doc.ocr_models import DETECTOR, THAI_RECOGNISER, model_path, models_folder

_DETECTOR_LONGEST_SIDE = 1280
# Only boxes at least this many times as wide as tall show the slant of the text.
_SLANT_SHOWING_RATIO = 3
# The detector scores each region it finds, and drops those under this score unread.
_BOX_THRESHOLD = 0.6
# Shrunk without smoothing, the dots of a fine dot pattern over a scan, such as a
# certificate's watermark scanned in black and white, turn into blobs like text. They join
# lines to each other and to the pattern, and the regions they make score under the
# threshold, so whole lines are dropped. Such a page shows a dropped region taller than
# this many of the page's lines and wider than this share of the page. On a 110-page
# contract's scans, 5 of the 7 watermarked pages showed one, and so did an ID card copy
# with a line written across it; none of the samples' 101 other scans, nor any of the
# corpus's, did. Blurred, the 2 pages missed would have gained 1 line and none.
_WATERMARK_LINES = 3
_WATERMARK_WIDTH = 0.25
# Such a page is blurred by this much, in pixels, before it is read again, so the dots
# turn grey: the pages that showed the sign gained 21 lines and lost 3. Blurred by 1.5,
# as a crisp page is (see `ocr.softened`), they gained 12.
_WATERMARK_SOFTENING = 2.0
# Any region the detector finds scores above this: a score of 0 means "the default".
_EVERY_REGION = 0.01
# How many CPU threads OCR uses, when this environment variable is set. PaddleOCR
# otherwise starts 10, whatever the CPUs, and under a 4-CPU limit that read a page
# almost three times slower (ADR 0004); the sandbox sets it to its CPU limit.
THREADS_VARIABLE = "PDF_TO_DOC_OCR_THREADS"


def default_engine() -> OcrEngine:
    """PaddleOCR, freshly loaded from the models folder.

    A conversion loads its own engine and drops it when it ends. Paddle keeps
    the last page image it read, and what it read there, in its predictors, so
    an engine kept for the next conversion would keep part of this one's
    document. Loading again takes under a second; importing Paddle, the slow
    part, happens once per process.
    """
    threads = os.environ.get(THREADS_VARIABLE)
    return PaddleOcrEngine(models_folder(), threads=int(threads) if threads else None)


class PaddleOcrEngine:
    name = "PaddleOCR"

    def __init__(self, models: Path, *, threads: int | None = None) -> None:
        """Load the models from the models folder; raises ModelsMissing if they are not there.
        `threads` is how many CPU threads to use, or None for PaddleOCR's default."""
        detector, recogniser = model_path(models, DETECTOR), model_path(models, THAI_RECOGNISER)
        # Never look for the models online, and keep Paddle's own log lines out of the output.
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        os.environ.setdefault("GLOG_minloglevel", "2")
        # Paddle looks for a compiler cache it would only need to build extensions.
        warnings.filterwarnings("ignore", message="No ccache found", category=UserWarning)
        from paddleocr import PaddleOCR

        for logger in ("paddlex", "paddleocr"):
            logging.getLogger(logger).setLevel(logging.ERROR)
        self._ocr = PaddleOCR(
            text_detection_model_name=DETECTOR.name,
            text_detection_model_dir=str(detector),
            text_recognition_model_name=THAI_RECOGNISER.name,
            text_recognition_model_dir=str(recogniser),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_type="max",
            text_det_limit_side_len=_DETECTOR_LONGEST_SIDE,
            device="cpu",
            text_det_box_thresh=_BOX_THRESHOLD,
            **({} if threads is None else {"cpu_threads": threads}),
        )
        self._regions: list[tuple[np.ndarray, float]] = []
        _keep_every_region(self._ocr, self._regions)

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        rgb = np.frombuffer(image.samples, dtype=np.uint8).reshape(image.height, image.width, 3)
        try:
            boxes = self._read_once(rgb, image)
            if _watermarked(self._regions, image.width):
                boxes = self._read_once(cv2.GaussianBlur(rgb, (0, 0), _WATERMARK_SOFTENING), image)
            return boxes
        finally:
            self._regions.clear()

    def _read_once(self, rgb: np.ndarray, image: PageImage) -> tuple[TextBox, ...]:
        [result] = self._ocr.predict(np.ascontiguousarray(rgb[:, :, ::-1]))  # PaddleOCR takes BGR
        boxes = _straightened([np.asarray(polygon, dtype=float) for polygon in result["rec_polys"]], image)
        return tuple(
            TextBox(text, box, float(score)) for text, score, box in zip(result["rec_texts"], result["rec_scores"], boxes)
        )


def _keep_every_region(ocr: Any, found: list[tuple[np.ndarray, float]]) -> None:
    """Have the detector also put in `found` every region it finds on the image it reads,
    with its score, before it drops those that score low. Its probability map is made once
    either way; only finding the regions on it runs twice. On the corpus's scans, both runs
    took 25 ms a page at most, of a read that took 1.4 s.

    This reaches into PaddleX: `paddleocr` is pinned, and `uv.lock` holds PaddleX at the
    version this was written for. The new step holds `found`, not the engine, so the engine
    and its predictors are freed as soon as it is dropped."""
    detector = ocr.paddlex_pipeline._pipeline.text_det_model
    drop_low = detector.post_op

    def post_op(preds, shapes, *, thresh, box_thresh, unclip_ratio):  # type: ignore[no-untyped-def]
        [polygons], [scores] = drop_low(preds, shapes, thresh=thresh, box_thresh=_EVERY_REGION, unclip_ratio=unclip_ratio)
        found[:] = [(np.asarray(polygon, dtype=float), float(score)) for polygon, score in zip(polygons, scores)]
        return drop_low(preds, shapes, thresh=thresh, box_thresh=box_thresh, unclip_ratio=unclip_ratio)

    detector.post_op = post_op


def _watermarked(regions: list[tuple[np.ndarray, float]], width: int) -> bool:
    """Whether the detector dropped a region much taller than the page's lines and wide
    across the page, as it does where a fine dot pattern joins lines together."""
    heights = [_extent(polygon, 1) for polygon, score in regions if score >= _BOX_THRESHOLD]
    if not heights:
        return False
    line = float(np.median(heights))
    return any(
        score < _BOX_THRESHOLD
        and _extent(polygon, 1) > _WATERMARK_LINES * line
        and _extent(polygon, 0) > _WATERMARK_WIDTH * width
        for polygon, score in regions
    )


def _extent(polygon: np.ndarray, axis: int) -> float:
    """How far a polygon reaches across (axis 0) or down (axis 1) the image."""
    return float(polygon[:, axis].max() - polygon[:, axis].min())


def _straightened(polygons: list[np.ndarray], image: PageImage) -> list[tuple[float, float, float, float]]:
    """Each box's bounds as if the page lay straight.

    The detector draws a slanted four-cornered box around each line of a page
    fed in askew. Upright bounds around slanted boxes are too tall, and lines
    run into each other. So the boxes are turned back by the page's slant, the
    median slant of the wide boxes' top edges, around the page's centre.
    """
    slants = [
        math.atan2(polygon[1, 1] - polygon[0, 1], polygon[1, 0] - polygon[0, 0])
        for polygon in polygons
        if _width(polygon) >= _SLANT_SHOWING_RATIO * _height(polygon)
    ]
    slant = float(np.median(slants)) if slants else 0.0
    turn = np.array([[math.cos(slant), math.sin(slant)], [-math.sin(slant), math.cos(slant)]])
    centre = np.array([image.width / 2, image.height / 2])
    bounds = []
    for polygon in polygons:
        points = (polygon - centre) @ turn.T + centre
        xs, ys = points[:, 0], points[:, 1]
        bounds.append((float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())))
    return bounds


def _width(polygon: np.ndarray) -> float:
    return float(np.hypot(*(polygon[1] - polygon[0])))


def _height(polygon: np.ndarray) -> float:
    return float(np.hypot(*(polygon[3] - polygon[0])))
