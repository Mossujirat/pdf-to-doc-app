"""OCR pages: the OCR engine interface, the converter's second seam, and turning what
an engine reads into rows that page layout treats like rows of a text layer."""

from dataclasses import dataclass, replace
from statistics import median
from typing import Literal, Protocol

import numpy as np
import pymupdf

from pdf_to_doc.layout import PageRows, Row
from pdf_to_doc.uncertain import Piece
from pdf_to_doc.words import unknown_words

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
# A box at least this many times as tall as wide runs down the page; a single
# upright digit reaches 1.5. A page is sideways when such boxes hold this share of
# its text's area: sideways pages held 0.79 or more, on the samples and synthetic
# ones alike, and synthetic upright ones 0.12 at most, a table with sideways column
# headers among them. No upright page of the samples was taken for sideways.
_TALL = 2.0
_SIDEWAYS = 0.5
# Which way a sideways page reads is told by how sure the engine is of its largest
# tall box, read as it was and read turned a quarter turn: a line read upright has
# the engine's confidence, upside down it has not. On the samples' sideways pages
# the two differed by 0.22 or more, on synthetic ones by 0.29 or more, and the
# reading taken for upright was 0.90 sure or more.
_CLEARLY_BETTER = 0.15
_READ_UPRIGHT = 0.8


@dataclass(frozen=True)
class PageImage:
    """A rendered page, or part of one: 8-bit RGB samples, row by row."""

    width: int
    height: int
    dpi: float
    samples: bytes
    turn: int = 0  # degrees it was turned clockwise from the page as shown: 0, 90 or 270


Box = tuple[float, float, float, float]


def turned_box(box: Box, turn: int, width: float, height: float) -> Box:
    """Where a box (x0, y0, x1, y1) on a page or image `width` by `height` lies once that
    is turned `turn` degrees clockwise: 0, 90, 180 or 270."""
    x0, y0, x1, y1 = box
    if turn == 90:
        return height - y1, x0, height - y0, x1
    if turn == 180:
        return width - x1, height - y1, width - x0, height - y0
    if turn == 270:
        return y0, width - x1, y1, width - x0
    return box


@dataclass(frozen=True)
class TextBox:
    """Text an engine read, the box around it (x0, y0, x1, y1) in image pixels, and how sure it is (0 to 1)."""

    text: str
    box: Box
    confidence: float


class OcrEngine(Protocol):
    """Reads the text on a page image, or on part of one, in the given languages."""

    name: str  # shown in the conversion summary

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]: ...


def render(page: pymupdf.Page) -> PageImage:
    zoom = DPI / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB, alpha=False)
    return PageImage(pix.width, pix.height, DPI, pix.samples)


def read_page(engine: OcrEngine, image: PageImage, text_layer: PageRows) -> PageRows:
    """The page's rows, read by the engine; a sideways page is turned upright and read again."""
    boxes = engine.read(image, LANGUAGES)
    turn = _sideways_turn(engine, image, boxes)
    if turn:
        image = _turned(image, turn)
        boxes = engine.read(image, LANGUAGES)
    return _ocr_page(boxes, image, text_layer)


def _turned(image: PageImage, turn: int) -> PageImage:
    """The image turned `turn` degrees clockwise: 90 or 270."""
    return _image(np.rot90(_pixels(image), k=-turn // 90), image.dpi, (image.turn + turn) % 360)


def _sideways_turn(engine: OcrEngine, image: PageImage, boxes: tuple[TextBox, ...]) -> int:
    """How far to turn the page clockwise to read it: 90 or 270 when its text runs
    down the page and the way it reads is clear, and otherwise 0, as for a page that
    reads as it is.

    The engine has read the largest tall box once; it is read again turned a quarter
    turn clockwise. When that reads clearly better, and surely, the page turns that
    way. When the first reading was clearly better, and sure, the engine had turned
    the box the other way itself, as PaddleOCR turns every box at least one and a
    half times as tall as wide counter-clockwise before reading it, and the page turns
    270. An engine that does not would never turn a page 270, rather than turn one
    wrongly. Reading the box turned that way too would cost more: a crop takes a tenth
    to a quarter of the time a page does.
    """
    boxes = tuple(box for box in boxes if box.text.strip())
    tall = [box for box in boxes if _height(box) >= _TALL * _width(box)]
    if not tall or sum(map(_area, tall)) < _SIDEWAYS * sum(map(_area, boxes)):
        return 0
    largest = max(tall, key=_area)
    as_read = _confidence((largest,))
    clockwise = _confidence(engine.read(_turned(_crop(image, largest), 90), LANGUAGES))
    if clockwise >= _READ_UPRIGHT and clockwise - as_read >= _CLEARLY_BETTER:
        return 90
    if as_read >= _READ_UPRIGHT and as_read - clockwise >= _CLEARLY_BETTER:
        return 270
    return 0


def _crop(image: PageImage, box: TextBox) -> PageImage:
    """The part of the image around a box, with a margin of the page around it."""
    x0, y0, x1, y1 = box.box
    margin = min(x1 - x0, y1 - y0) / 2
    left, top = max(0, int(x0 - margin)), max(0, int(y0 - margin))
    right, bottom = min(image.width, int(x1 + margin) + 1), min(image.height, int(y1 + margin) + 1)
    return _image(_pixels(image)[top:bottom, left:right], image.dpi, image.turn)


def _pixels(image: PageImage) -> np.ndarray:
    return np.frombuffer(image.samples, dtype=np.uint8).reshape(image.height, image.width, 3)


def _image(pixels: np.ndarray, dpi: float, turn: int) -> PageImage:
    pixels = np.ascontiguousarray(pixels)
    return PageImage(pixels.shape[1], pixels.shape[0], dpi, pixels.tobytes(), turn)


def _confidence(boxes: tuple[TextBox, ...]) -> float:
    """How sure the engine is of what it read, per character; 0 when it read nothing.
    A crop catches bits of the lines beside it, which count for little."""
    read = [(len(box.text.strip()), box.confidence) for box in boxes if box.text.strip()]
    characters = sum(length for length, _ in read)
    return sum(length * confidence for length, confidence in read) / characters if characters else 0.0


def _ocr_page(boxes: tuple[TextBox, ...], image: PageImage, text_layer: PageRows) -> PageRows:
    """The page's rows, in PDF points: the text layer's rows, and what the engine read elsewhere.

    Text over a scan, such as a stamped header or a note, is taken from the text
    layer, which holds it exactly, and the engine's boxes that cover it are
    dropped; unless the engine's reading of a row holds fewer words outside the
    word list, as when the row's font reports some letters wrongly. Each row the engine read gets the geometry of a text-layer row: the
    page's font size, estimated from the usual box height, and a height in
    proportion to it.

    On an image turned to read a sideways page, the rows lie on the page turned the
    same way. The text layer was written on the page as shown: its rows are compared
    with the boxes where they lie on the turned image, but each keeps its share of the
    page's height and width, so a header still opens the page at its top edge.
    """
    width, height = (text_layer.height, text_layer.width) if image.turn % 180 else (text_layer.width, text_layer.height)
    scale = width / image.width
    # Each text-layer row, and where it lies on the image.
    layer = [(row, _turned_row(row, image.turn, text_layer)) for row in text_layer.rows]
    kept = [(row, on_image) for row, on_image in layer if not _reads_better(boxes, on_image, scale)]
    read = tuple(box for box in boxes if not any(_overlaps(box, on_image, scale) for _, on_image in kept))
    lines = _printed_lines(read)
    rows = [_placed(row, width / text_layer.width, height / text_layer.height) for row, _ in kept]
    if lines:
        size = median(_line_height(line) for line in lines) * scale / _BOX_HEIGHT_PER_FONT_SIZE
        rows += [_row(line, scale, size) for line in lines]
    return PageRows(rows=tuple(sorted(rows, key=lambda row: row.y0)), width=width, height=height, kind="ocr")


def _turned_row(row: Row, turn: int, page: PageRows) -> Row:
    """Where the row lies once the page is turned `turn` degrees clockwise."""
    x0, y0, x1, y1 = turned_box((row.x0, row.y0, row.x1, row.y1), turn, page.width, page.height)
    return replace(row, x0=x0, y0=y0, x1=x1, y1=y1)


def _placed(row: Row, across: float, down: float) -> Row:
    """The row moved to the same share of a page `across` times as wide and `down` times as tall."""
    return replace(row, x0=row.x0 * across, y0=row.y0 * down, x1=row.x1 * across, y1=row.y1 * down)


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
        pieces=tuple(Piece(box.text, box.confidence) for box in line),
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


def _width(box: TextBox) -> float:
    return box.box[2] - box.box[0]


def _area(box: TextBox) -> float:
    return _width(box) * _height(box)
