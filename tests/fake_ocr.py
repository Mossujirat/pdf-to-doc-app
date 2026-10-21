"""A fake OCR engine for tests: it reads each page image as the next lines it was given."""

from collections.abc import Sequence
from dataclasses import dataclass

from pdf_builder import LINE_HEIGHT, TOP, Styled

from pdf_to_doc.ocr import Language, PageImage, TextBox

# How sure the engine is of a line, unless the line says otherwise.
CONFIDENT = 0.99


@dataclass(frozen=True)
class Unsure:
    """A line the engine reads with low confidence, as a real one reads a smudge or handwriting."""

    line: str | Styled
    confidence: float = 0.5


class FakeEngine:
    """Lays the lines out as `pdf_builder` draws them, one box per line.

    A line is a string, or a `Styled` line with its own size and position; an
    empty string leaves a blank line. Either can be `Unsure`. A box is as tall as
    a real detector draws it, about one and a half times the font size.
    """

    name = "fake"

    def __init__(self, *pages: Sequence[str | Styled | Unsure]) -> None:
        self.pages = list(pages)
        self.images: list[PageImage] = []  # every image it was asked to read

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        lines = self.pages[len(self.images)]
        self.images.append(image)
        scale = image.dpi / 72
        boxes = []
        baseline: float = TOP
        for entry in lines:
            line, confidence = (entry.line, entry.confidence) if isinstance(entry, Unsure) else (entry, CONFIDENT)
            styled = line if isinstance(line, Styled) else Styled(line)
            baseline = styled.y if styled.y is not None else baseline
            if styled.text:
                size = styled.size
                box = (styled.x, baseline - 1.1 * size, styled.x + size / 2 * len(styled.text), baseline + 0.4 * size)
                x0, y0, x1, y1 = (edge * scale for edge in box)
                boxes.append(TextBox(styled.text, (x0, y0, x1, y1), confidence))
            baseline += max(LINE_HEIGHT, styled.size * 1.4) if isinstance(line, Styled) else LINE_HEIGHT
        return tuple(boxes)


class BlankEngine:
    """Reads every page image as blank, for tests that only look at text pages."""

    name = "blank"

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        return ()
