"""What a conversion reports as it goes, so that the caller can show how far it has got."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pdf_to_doc.intake import SourceType


@dataclass(frozen=True)
class Opened:
    """The first report: the source file has passed intake, and this is its type and page count."""

    source_type: SourceType
    pages: int


@dataclass(frozen=True)
class Progress:
    """A stage the conversion has reached. In the "ocr" stage, the `current` of `total` OCR pages,
    counting from 1, is about to be read; the other stages have no count."""

    stage: Literal["reading", "ocr", "writing"]
    current: int | None = None
    total: int | None = None


ProgressCallback = Callable[[Opened | Progress], None]
