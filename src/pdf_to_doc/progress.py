"""What a conversion reports as it goes, so that the caller can show how far it has got."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pdf_to_doc.intake import SourceType

Stage = Literal["reading", "images", "ocr", "writing"]


@dataclass(frozen=True)
class Opened:
    """The first report: the source file has passed intake, and this is its type and page count."""

    source_type: SourceType
    pages: int


@dataclass(frozen=True)
class Progress:
    """A stage the conversion has reached. In the "images" stage, the image of the `current` of
    `total` pages kept as images, counting from 1, is about to be made; in the "ocr" stage, the
    `current` of `total` OCR pages is about to be read. The other stages have no count."""

    stage: Stage
    current: int | None = None
    total: int | None = None


ProgressCallback = Callable[[Opened | Progress], None]
