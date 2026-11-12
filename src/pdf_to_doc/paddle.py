"""The default OCR engine: PaddleOCR with the PP-OCRv5 mobile models, on the CPU. And the default
picture finder, which reads scans beside it: PaddleX's PP-DocLayout_plus-L (see `PaddleLayoutFinder`).

The settings come from the October 2026 benchmark (docs/research):
- The detector's input is capped at 1280 px on its longest side. At full
  resolution it splits Thai marks into boxes of their own, and merges or skips lines.
- Orientation, unwarping and text-line orientation are off. A page fed in askew
  still has its boxes straightened (see `_straightened`).
- The Thai recogniser reads English words and digits on the same line correctly,
  so it serves both languages; the English recogniser cannot read Thai at all.
- A scan under a fine dot pattern, such as a certificate's watermark, is blurred and
  read again (see `_watermarked`).
- A line the detector found but dropped, scored just under its threshold, is looked for
  again on the page blurred, and only what is read there is added (see `lost_lines`).
"""

import logging
import math
import os
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple, get_args

import cv2
import numpy as np

from pdf_to_doc.ocr import Box, Language, OcrEngine, PageImage, TextBox
from pdf_to_doc.ocr_models import DETECTOR, LAYOUT, THAI_RECOGNISER, model_path, models_folder
from pdf_to_doc.pictures import FoundPicture, PictureFinder, PictureLabel

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
# The detector also drops single lines that score just under the threshold, on clean scans too
# (ticket 42): a dropped region this many of the page's lines tall, and at least this share of
# the page wide, is shaped like a lost line. On the samples' scans, 46 regions were: 18 held text a
# blurred reading found, 13 text read already, and 15 nothing, such as highlights and rules. Dots
# and rules are thinner, logos and blocks taller, and a word or two narrower.
_LOST_LINE_HEIGHTS = (0.5, 2.5)
_LOST_LINE_WIDTH = 0.05
# A page with lost lines is read again blurred by this much, in pixels, and only what that reading
# finds in them is added; the rest of the page stays as first read. A blur of 1.0 or 1.5 read the
# lost line of a sample's clean scan exactly, as a crisp page is softened (see `ocr.softened`).
_LOST_LINE_SOFTENING = 1.5
# A box a second reading finds counts as read in a lost line when this share of it lies inside one:
# half, as the samples' boxes were counted when measured. The sample's lost line lies wholly inside
# its region.
_INSIDE_A_LOST_LINE = 0.5
# It was read already when this share of it lies inside the boxes the first reading read, all
# together: such a region, over cells or labels each read on its own, would give their text twice.
# On the samples, the boxes a blurred reading found in a lost line lay 0–22% inside a box already
# read, or 77–100%.
_READ_ALREADY = 0.5
# And it is text when read this surely, with this many characters. The text the samples' blurred
# readings found in lost lines read at 0.67 or more, all but one piece at 0.7 or more; the junk
# read from signatures at 0.24–0.60. A lone letter, read surely, was a stray mark.
_RECOVERED_CONFIDENCE = 0.7
_RECOVERED_CHARACTERS = 2
# Any region the detector finds scores above this: a score of 0 means "the default".
_EVERY_REGION = 0.01
# How many CPU threads OCR uses, when this environment variable is set. PaddleOCR
# otherwise starts 10, whatever the CPUs, and under a 4-CPU limit that read a page
# almost three times slower (ADR 0004); the sandbox sets it to its CPU limit.
THREADS_VARIABLE = "PDF_TO_DOC_OCR_THREADS"

# The layout model's labels for a picture (see `PictureLabel`).
_PICTURE_LABELS: frozenset[str] = frozenset(get_args(PictureLabel))

# A region the detector found: its four corners on the image, and how it scored.
Region = tuple[np.ndarray, float]


class Reading(NamedTuple):
    """What the engine read in one box: its text, how sure it is of it, and the box's four
    corners on the image, as the detector found them."""

    text: str
    confidence: float
    corners: np.ndarray


def _quiet_and_offline() -> None:
    """Before Paddle is imported: never look for the models online, and keep Paddle's own log lines
    out of the output."""
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("GLOG_minloglevel", "2")
    # Paddle looks for a compiler cache it would only need to build extensions.
    warnings.filterwarnings("ignore", message="No ccache found", category=UserWarning)
    for logger in ("paddlex", "paddleocr"):
        logging.getLogger(logger).setLevel(logging.ERROR)


def _threads_set() -> int | None:
    """How many CPU threads Paddle may use, as the environment says, or None for its default."""
    threads = os.environ.get(THREADS_VARIABLE)
    return int(threads) if threads else None


def default_picture_finder() -> PictureFinder:
    """PaddleX's layout model, freshly loaded from the models folder, as the engine is, and for the
    same reason (see `default_engine`); raises ModelsMissing if it is not there."""
    return PaddleLayoutFinder(models_folder(), threads=_threads_set())


class PaddleLayoutFinder:
    """Finds pictures inside a page image with PP-DocLayout_plus-L, on the CPU: the regions it
    labels "image", "chart" or "seal", scored at least its own threshold. Its other labels, such as
    text, tables, headers and footers, are no picture.

    On the samples' scans it found most signatures, logos and photos, and no seal at all
    (ticket 38, 2026-11-12); signatures it misses beside a row to sign on are ticket 03's.
    """

    def __init__(self, models: Path, *, threads: int | None = None) -> None:
        """Load the model from the models folder; raises ModelsMissing if it is not there.
        `threads` is how many CPU threads to use, or None for Paddle's default."""
        path = model_path(models, LAYOUT)
        _quiet_and_offline()
        from paddleocr import LayoutDetection

        self._model = LayoutDetection(
            model_name=LAYOUT.name,
            model_dir=str(path),
            device="cpu",
            **({} if threads is None else {"cpu_threads": threads}),
        )

    def find(self, image: PageImage) -> tuple[FoundPicture, ...]:
        rgb = np.frombuffer(image.samples, dtype=np.uint8).reshape(image.height, image.width, 3)
        # Paddle takes an array's colours in OpenCV's order, blue first.
        [result] = self._model.predict(np.ascontiguousarray(rgb[..., ::-1]), batch_size=1)
        return tuple(
            FoundPicture(_box(region["coordinate"]), region["label"])
            for region in result["boxes"]
            if region["label"] in _PICTURE_LABELS
        )


def _box(coordinate: Sequence[float]) -> Box:
    """A region's box as Paddle gives it, its corners (x0, y0, x1, y1) as NumPy numbers, as plain ones."""
    x0, y0, x1, y1 = (float(value) for value in coordinate)
    return x0, y0, x1, y1


def default_engine() -> OcrEngine:
    """PaddleOCR, freshly loaded from the models folder.

    A conversion loads its own engine and drops it when it ends. Paddle keeps
    the last page image it read, and what it read there, in its predictors, so
    an engine kept for the next conversion would keep part of this one's
    document. Loading again takes under a second; importing Paddle, the slow
    part, happens once per process.
    """
    return PaddleOcrEngine(models_folder(), threads=_threads_set())


class PaddleOcrEngine:
    name = "PaddleOCR"

    def __init__(self, models: Path, *, threads: int | None = None) -> None:
        """Load the models from the models folder; raises ModelsMissing if they are not there.
        `threads` is how many CPU threads to use, or None for PaddleOCR's default."""
        detector, recogniser = model_path(models, DETECTOR), model_path(models, THAI_RECOGNISER)
        _quiet_and_offline()
        from paddleocr import PaddleOCR

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
        self._regions: list[Region] = []
        _keep_every_region(self._ocr, self._regions)

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        rgb = np.frombuffer(image.samples, dtype=np.uint8).reshape(image.height, image.width, 3)
        try:
            readings = self._read_once(rgb)
            if _watermarked(self._regions, image.width):
                readings = self._read_blurred(rgb, _WATERMARK_SOFTENING)
            first_corners = [reading.corners for reading in readings]
            if lost := lost_lines(self._regions, image.width):
                readings += recovered(lost, readings, self._read_blurred(rgb, _LOST_LINE_SOFTENING))
            boxes = _straightened([reading.corners for reading in readings], image, slanted_as=first_corners)
            return tuple(TextBox(reading.text, box, reading.confidence) for reading, box in zip(readings, boxes))
        finally:
            self._regions.clear()

    def _read_once(self, rgb: np.ndarray) -> list[Reading]:
        [result] = self._ocr.predict(np.ascontiguousarray(rgb[:, :, ::-1]))  # PaddleOCR takes BGR
        return [
            Reading(text, float(score), np.asarray(polygon, dtype=float))
            for text, score, polygon in zip(result["rec_texts"], result["rec_scores"], result["rec_polys"])
        ]

    def _read_blurred(self, rgb: np.ndarray, softening: float) -> list[Reading]:
        """The page read again, blurred by `softening` pixels."""
        return self._read_once(cv2.GaussianBlur(rgb, (0, 0), softening))


def _keep_every_region(ocr: Any, found: list[Region]) -> None:
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


def _watermarked(regions: Sequence[Region], width: int) -> bool:
    """Whether the detector dropped a region much taller than the page's lines and wide
    across the page, as it does where a fine dot pattern joins lines together."""
    line = _line_height(regions)
    return line is not None and any(
        score < _BOX_THRESHOLD
        and _extent(polygon, 1) > _WATERMARK_LINES * line
        and _extent(polygon, 0) > _WATERMARK_WIDTH * width
        for polygon, score in regions
    )


def lost_lines(regions: Sequence[Region], width: int) -> list[np.ndarray]:
    """The corners of each region the detector dropped that is shaped like a line of text: about
    as tall as the page's lines, and wide enough to hold more than a word or two (see
    `_LOST_LINE_HEIGHTS`)."""
    line = _line_height(regions)
    if line is None:
        return []
    shortest, tallest = _LOST_LINE_HEIGHTS
    return [
        corners
        for corners, score in regions
        if score < _BOX_THRESHOLD
        and shortest * line <= _extent(corners, 1) <= tallest * line
        and _extent(corners, 0) >= _LOST_LINE_WIDTH * width
    ]


def recovered(lost: Sequence[np.ndarray], first: Sequence[Reading], again: Sequence[Reading]) -> list[Reading]:
    """What a second reading of the page, `again`, read in its lost lines (see `lost_lines`) that
    the first reading did not."""
    return [
        reading
        for reading in again
        if reading.confidence >= _RECOVERED_CONFIDENCE
        and len(reading.text.strip()) >= _RECOVERED_CHARACTERS
        and any(_share_inside(reading.corners, line) >= _INSIDE_A_LOST_LINE for line in lost)
        and sum(_share_inside(reading.corners, read.corners) for read in first) < _READ_ALREADY
    ]


def _line_height(regions: Sequence[Region]) -> float | None:
    """The page's usual line height: the median height of the regions the detector kept, or
    None when it kept none."""
    heights = [_extent(corners, 1) for corners, score in regions if score >= _BOX_THRESHOLD]
    return float(np.median(heights)) if heights else None


def _share_inside(polygon: np.ndarray, other: np.ndarray) -> float:
    """The share of the polygon's area that lies inside the other polygon."""
    area = cv2.contourArea(polygon.astype(np.float32))
    if not area:
        return 0.0
    common, _ = cv2.intersectConvexConvex(polygon.astype(np.float32), other.astype(np.float32))
    return float(common) / area


def _extent(polygon: np.ndarray, axis: int) -> float:
    """How far a polygon reaches across (axis 0) or down (axis 1) the image."""
    return float(polygon[:, axis].max() - polygon[:, axis].min())


def _straightened(
    polygons: list[np.ndarray], image: PageImage, slanted_as: list[np.ndarray]
) -> list[tuple[float, float, float, float]]:
    """Each box's bounds as if the page lay straight.

    The detector draws a slanted four-cornered box around each line of a page
    fed in askew. Upright bounds around slanted boxes are too tall, and lines
    run into each other. So the boxes are turned back by the page's slant, the
    median slant of the wide boxes' top edges among `slanted_as`, around the
    page's centre. Lines recovered after the page was first read are left out of
    `slanted_as`, so that the boxes first read keep their bounds.
    """
    slants = [
        math.atan2(polygon[1, 1] - polygon[0, 1], polygon[1, 0] - polygon[0, 0])
        for polygon in slanted_as
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
