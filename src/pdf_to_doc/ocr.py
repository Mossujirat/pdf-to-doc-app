"""OCR pages: the OCR engine interface, the converter's second seam, and turning what
an engine reads into rows that page layout treats like rows of a text layer."""

from dataclasses import dataclass
from statistics import median
from typing import Literal, Protocol

import pymupdf

from pdf_to_doc.layout import PageRows, Row
from pdf_to_doc.validation import unknown_words

Language = Literal["th", "en"]
LANGUAGES: tuple[Language, ...] = ("th", "en")
# Pages are rendered at this resolution; the detector scales its own input down.
DPI = 300
# A detector draws a box about this many times as tall as the font size. Marks
# above and below the letters make a box taller: on real scans, one line in five
# was a fifth taller than the page's usual line, in the same font. So box heights
# cannot tell font sizes apart, and every line of a page gets the same size.
_BOX_HEIGHT_PER_FONT_SIZE = 1.5
# Boxes whose centres are closer than this share of a box height sit on one printed line.
_SAME_LINE = 0.5
# A row of a text layer is about this many times as tall as its font size.
_ROW_HEIGHT_PER_FONT_SIZE = 1.2


@dataclass(frozen=True)
class PageImage:
    """A rendered page: 8-bit RGB samples, row by row."""

    width: int
    height: int
    dpi: float
    samples: bytes


@dataclass(frozen=True)
class TextBox:
    """Text an engine read, the box around it (x0, y0, x1, y1) in image pixels, and how sure it is (0 to 1)."""

    text: str
    box: tuple[float, float, float, float]
    confidence: float


class OcrEngine(Protocol):
    """Reads the text on one page image, in the given languages."""

    name: str  # shown in the conversion summary

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]: ...


def render(page: pymupdf.Page) -> PageImage:
    zoom = DPI / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB, alpha=False)
    return PageImage(pix.width, pix.height, DPI, pix.samples)


def ocr_page(boxes: tuple[TextBox, ...], image: PageImage, text_layer: PageRows) -> PageRows:
    """The page's rows, in PDF points: the text layer's rows, and what the engine read elsewhere.

    Text over a scan, such as a stamped header or a note, is taken from the text
    layer, which holds it exactly, and the engine's boxes that cover it are
    dropped; unless the engine's reading of a row holds fewer words outside the
    word list, as when the row's font reports some letters wrongly. Each row the engine read gets the geometry of a text-layer row: the
    page's font size, estimated from the usual box height, and a height in
    proportion to it.
    """
    scale = text_layer.width / image.width
    kept = [row for row in text_layer.rows if not _reads_better(boxes, row, scale)]
    read = tuple(box for box in boxes if not any(_overlaps(box, row, scale) for row in kept))
    lines = _printed_lines(read)
    rows = list(kept)
    if lines:
        size = median(_line_height(line) for line in lines) * scale / _BOX_HEIGHT_PER_FONT_SIZE
        rows += [_row(line, scale, size) for line in lines]
    return PageRows(
        rows=tuple(sorted(rows, key=lambda row: row.y0)),
        width=text_layer.width,
        height=text_layer.height,
        kind="ocr",
    )


def _printed_lines(boxes: tuple[TextBox, ...]) -> list[list[TextBox]]:
    """Boxes grouped into printed lines, top to bottom, each line left to right."""
    lines: list[list[TextBox]] = []
    for box in sorted((box for box in boxes if box.text.strip()), key=_centre):
        if lines and abs(_centre(box) - _centre(lines[-1][0])) <= _SAME_LINE * _height(lines[-1][0]):
            lines[-1].append(box)
        else:
            lines.append([box])
    return [sorted(line, key=lambda box: box.box[0]) for line in lines]


def _row(line: list[TextBox], scale: float, size: float) -> Row:
    centre = median(_centre(box) for box in line) * scale
    half = _ROW_HEIGHT_PER_FONT_SIZE * size / 2
    return Row(
        text=" ".join(box.text.strip() for box in line),
        x0=line[0].box[0] * scale,
        y0=centre - half,
        x1=line[-1].box[2] * scale,
        y1=centre + half,
        size=size,
    )


def _reads_better(boxes: tuple[TextBox, ...], row: Row, scale: float) -> bool:
    """Whether the engine's reading of the row's place holds fewer words outside the word list."""
    covering = [box.text for box in boxes if _overlaps(box, row, scale)]
    return bool(covering) and unknown_words(" ".join(covering)) < unknown_words(row.text)


def _overlaps(box: TextBox, row: Row, scale: float) -> bool:
    left, top, right, bottom = (edge * scale for edge in box.box)
    return top < row.y1 and row.y0 < bottom and left < row.x1 and row.x0 < right


def _line_height(line: list[TextBox]) -> float:
    return median(_height(box) for box in line)


def _centre(box: TextBox) -> float:
    return (box.box[1] + box.box[3]) / 2


def _height(box: TextBox) -> float:
    return box.box[3] - box.box[1]
