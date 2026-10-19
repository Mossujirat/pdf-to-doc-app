"""The default OCR engine: PaddleOCR with the PP-OCRv5 mobile models, on the CPU.

The settings come from the October 2026 benchmark (docs/research):
- The detector's input is capped at 1280 px on its longest side. At full
  resolution it splits Thai marks into boxes of their own, and merges or skips lines.
- Orientation, unwarping and text-line orientation are off. A page fed in askew
  still has its boxes straightened (see `_straightened`).
- The Thai recogniser reads English words and digits on the same line correctly,
  so it serves both languages; the English recogniser cannot read Thai at all.
"""

import logging
import math
import os
import warnings
from functools import cache
from pathlib import Path

import numpy as np

from pdf_to_doc.ocr import Language, OcrEngine, PageImage, TextBox
from pdf_to_doc.ocr_models import DETECTOR, THAI_RECOGNISER, model_path, models_folder

_DETECTOR_LONGEST_SIDE = 1280
# Only boxes at least this many times as wide as tall show the slant of the text.
_SLANT_SHOWING_RATIO = 3


def default_engine() -> OcrEngine:
    """PaddleOCR from the models folder, loaded the first time a page needs it, then kept."""
    return _engine(models_folder())


@cache
def _engine(models: Path) -> OcrEngine:
    return PaddleOcrEngine(models)


class PaddleOcrEngine:
    name = "PaddleOCR"

    def __init__(self, models: Path) -> None:
        """Load the models from the models folder; raises ModelsMissing if they are not there."""
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
        )

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        rgb = np.frombuffer(image.samples, dtype=np.uint8).reshape(image.height, image.width, 3)
        [result] = self._ocr.predict(np.ascontiguousarray(rgb[:, :, ::-1]))  # PaddleOCR takes BGR
        boxes = _straightened([np.asarray(polygon, dtype=float) for polygon in result["rec_polys"]], image)
        return tuple(
            TextBox(text, box, float(score)) for text, score, box in zip(result["rec_texts"], result["rec_scores"], boxes)
        )


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
