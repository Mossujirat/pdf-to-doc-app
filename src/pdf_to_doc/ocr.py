"""OCR pages: the OCR engine interface, the converter's second seam, and turning what
an engine reads into rows that page layout treats like rows of a text layer."""

import re
from dataclasses import dataclass, replace
from statistics import median
from typing import Literal, Protocol

import cv2
import numpy as np
import pymupdf

from pdf_to_doc.layout import COLUMN_GAP, PageRows, Row
from pdf_to_doc.thai import DIGITS
from pdf_to_doc.uncertain import Piece
from pdf_to_doc.words import unknown_words

Language = Literal["th", "en"]
LANGUAGES: tuple[Language, ...] = ("th", "en")
# Pages are rendered at this resolution; the detector scales its own input down.
DPI = 300
# A page rendered from the PDF is crisp, unlike a scan. PaddleOCR's detector shrinks a
# page to 1280 pixels on its longest side, about a third of a 300-dpi A4 page, without
# smoothing it first; the thin strokes where upper marks join a line then break up, the
# line scores under the detector's threshold, and is dropped. Blurred first by this much,
# in pixels, every line of such pages was read; 1.0 still lost lines, and 2.0 lost them
# again on pages with tables.
_SOFTENING = 1.5
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
# A page set in columns is cut where its boxes leave room, in median box heights:
# a band across the page this tall parts what is above it from what is below, and a
# gutter down it this wide parts columns. Of the bands tried, 0.5 to 1.2, this one read
# the synthetic scans best. The narrowest gutter that parted two columns on them left
# 0.63 box heights between their boxes; narrower ones, and Thai ones up to 16 pt, had
# boxes running into or across them.
_BAND_GAP = 0.8
_GUTTER = 0.5
# A column holds at least this many printed lines. Fewer, such as initials in the
# margin, belong with the column beside them.
_COLUMN_LINES = 2
# But only where every column is body text, its lines at least this many characters
# long at the median, spaces left out. Labels set apart from their values, as in a
# form, look the same but are read row by row. On synthetic scans the shorter side of
# such layouts measured 18 characters at most, and of side panels, signature blocks and
# bank details beside signatories 18.5, against 27 to 40 for body text.
_BODY_LINE = 24
# And only where most of each column's lines start at one place, or centre on one, give
# or take this many box heights. On the samples' columns they were 0.3 off at most; the
# holes that a diagonal watermark leaves in lines left their text 1.3 or more off.
_LINED_UP = 0.5


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


def softened(image: PageImage) -> PageImage:
    """The image blurred a little, as a scan is: for a page rendered from the PDF, which is crisp."""
    return _image(cv2.GaussianBlur(_pixels(image), (0, 0), _SOFTENING), image.dpi, image.turn)


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

    A page set in columns gives each column's rows in turn, top to bottom (see
    `_reading_parts`); a text-layer row goes with the column it lies in.
    """
    width, height = (text_layer.height, text_layer.width) if image.turn % 180 else (text_layer.width, text_layer.height)
    scale = width / image.width
    # Each text-layer row, and where it lies on the image.
    layer = [(row, _turned_row(row, image.turn, text_layer)) for row in text_layer.rows]
    kept = [(row, on_image) for row, on_image in layer if not _reads_better(boxes, on_image, scale)]
    read = tuple(box for box in boxes if not any(_overlaps(box, on_image, scale) for _, on_image in kept))
    parts = _reading_parts(read, tuple(_LayerRow.of(row, on_image, scale) for row, on_image in kept))
    lines_by_part = [_printed_lines(tuple(box for box in part if not isinstance(box, _LayerRow))) for part in parts]
    lines = [line for part_lines in lines_by_part for line in part_lines]
    size = median(_line_height(line) for line in lines) * scale / _BOX_HEIGHT_PER_FONT_SIZE if lines else 0.0
    rows: list[Row] = []
    for part, part_lines in zip(parts, lines_by_part):
        part_rows = [
            _placed(box.row, width / text_layer.width, height / text_layer.height)
            for box in part
            if isinstance(box, _LayerRow)
        ]
        part_rows = sorted(part_rows + [_row(line, scale, size) for line in part_lines], key=lambda row: row.y0)
        if len(parts) > 1 and part_rows:
            part_rows[0] = replace(part_rows[0], starts_block=True)
        rows += part_rows
    return PageRows(rows=tuple(rows), width=width, height=height, kind="ocr")


@dataclass(frozen=True)
class _LayerRow(TextBox):
    """A text-layer row as a box on the image, so that it is placed in a column with the
    boxes; sure of its text, which the text layer holds exactly."""

    row: Row

    @classmethod
    def of(cls, row: Row, on_image: Row, scale: float) -> "_LayerRow":
        box = (on_image.x0 / scale, on_image.y0 / scale, on_image.x1 / scale, on_image.y1 / scale)
        return cls(row.text, box, 1.0, row)


def _reading_parts(read: tuple[TextBox, ...], layer: tuple[TextBox, ...]) -> list[tuple[TextBox, ...]]:
    """The engine's boxes and the text layer's rows in the parts a reader reads one after
    the other: down the page, and where it is set in columns, each column to its end
    before the one to its right. A page without columns is one part. Distances are
    measured in the engine's median box height."""
    read = tuple(box for box in read if box.text.strip())
    boxes = read + tuple(box for box in layer if box.text.strip())
    return _parts(boxes, median(_height(box) for box in read)) if read else [boxes]


def _parts(boxes: tuple[TextBox, ...], unit: float) -> list[tuple[TextBox, ...]]:
    """The boxes in reading order, as `_reading_parts` gives them; each column is read the same way in turn."""
    parts: list[tuple[TextBox, ...]] = []
    run: list[TextBox] = []  # bands not set in columns, read as one part
    for region in _regions(boxes, unit):
        columns = _text_columns(region, unit)
        if not columns:
            run += region
            continue
        if run:
            parts.append(tuple(run))
            run = []
        parts += [part for column in columns for part in _parts(column, unit)]
    if run:
        parts.append(tuple(run))
    return parts if len(parts) > 1 else [boxes]


def _regions(boxes: tuple[TextBox, ...], unit: float) -> list[tuple[TextBox, ...]]:
    """The boxes cut into bands down the page, each band taken with the columns above it when it is more of them."""
    regions: list[tuple[TextBox, ...]] = []
    for band in _cut(boxes, 1, _BAND_GAP * unit):
        if regions and _more_of(regions[-1], band, unit):
            regions[-1] += band
        else:
            regions.append(band)
    return regions


def _more_of(above: tuple[TextBox, ...], band: tuple[TextBox, ...], unit: float) -> bool:
    """Whether the band is more of the columns of body text above it: set in the same
    columns, as when the paragraphs of two columns end on the same line, or body text
    under the one column that reaches further down than the others, as when the last
    column on a page ends early. Labels and values, or signatures, under them are not."""
    columns = _text_columns(above, unit)
    if not columns:
        return False
    if band_columns := _text_columns(band, unit):
        return any(a0 < b1 and b0 < a1 for a0, a1 in _gutters(columns) for b0, b1 in _gutters(band_columns))
    return _under_the_longest(columns, band, unit) and _body_text(band) and _lined_up(band, unit)


def _under_the_longest(columns: list[tuple[TextBox, ...]], band: tuple[TextBox, ...], unit: float) -> bool:
    """Whether the band lies under the column that reaches further down than the others, clear of their sides."""
    bottoms = [_bottom(column) for column in columns]
    longest = bottoms.index(max(bottoms))
    if any(bottoms[longest] - bottom < _BAND_GAP * unit for number, bottom in enumerate(bottoms) if number != longest):
        return False
    left = _right(columns[longest - 1]) if longest > 0 else float("-inf")
    right = _left(columns[longest + 1]) if longest + 1 < len(columns) else float("inf")
    return left < _left(band) and _right(band) < right


def _text_columns(boxes: tuple[TextBox, ...], unit: float) -> list[tuple[TextBox, ...]]:
    """The boxes' columns, left to right, when they are set in columns of body text; otherwise none."""
    columns = _columns(boxes, unit)
    if len(columns) > 1 and all(_body_text(column) and _lined_up(column, unit) for column in columns):
        return columns
    return []


def _gutters(columns: list[tuple[TextBox, ...]]) -> list[tuple[float, float]]:
    """Where the gutters between the columns run across the page, left to right."""
    return [(_right(before), _left(after)) for before, after in zip(columns, columns[1:])]


def _columns(band: tuple[TextBox, ...], unit: float) -> list[tuple[TextBox, ...]]:
    """The band cut at its gutters, left to right; a piece of too few lines is joined to
    the piece across the narrower gutter beside it."""
    pieces = _cut(band, 0, _GUTTER * unit)
    while len(pieces) > 1:
        short = [number for number, piece in enumerate(pieces) if len(_printed_lines(piece)) < _COLUMN_LINES]
        if not short:
            break
        number = short[0]
        after = number + 1 < len(pieces) and (
            number == 0 or _gutter(pieces[number], pieces[number + 1]) < _gutter(pieces[number - 1], pieces[number])
        )
        first = number if after else number - 1
        pieces[first : first + 2] = [pieces[first] + pieces[first + 1]]
    return pieces


def _gutter(before: tuple[TextBox, ...], after: tuple[TextBox, ...]) -> float:
    return _left(after) - _right(before)


def _left(boxes: tuple[TextBox, ...]) -> float:
    return min(box.box[0] for box in boxes)


def _right(boxes: tuple[TextBox, ...]) -> float:
    return max(box.box[2] for box in boxes)


def _bottom(boxes: tuple[TextBox, ...]) -> float:
    return max(box.box[3] for box in boxes)


def _body_text(column: tuple[TextBox, ...]) -> bool:
    """Whether the column reads as body text: long lines, mostly not digits, unlike a column of amounts."""
    lines = ["".join("".join(box.text for box in line).split()) for line in _printed_lines(column)]
    digits = sum(len(run) for line in lines for run in re.findall(DIGITS, line))
    return median(map(len, lines)) >= _BODY_LINE and 2 * digits < sum(map(len, lines))


def _lined_up(column: tuple[TextBox, ...], unit: float) -> bool:
    """Whether most of the column's lines start at one place, or centre on one when set
    centred, as a column's lines do; not wherever holes in the lines happen to end."""
    lines = _printed_lines(column)
    starts = [line[0].box[0] for line in lines]
    centres = [(line[0].box[0] + line[-1].box[2]) / 2 for line in lines]
    return any(
        2 * sum(abs(place - median(places)) < _LINED_UP * unit for place in places) > len(places)
        for places in (starts, centres)
    )


def _cut(boxes: tuple[TextBox, ...], axis: int, gap: float) -> list[tuple[TextBox, ...]]:
    """The boxes cut where they leave a stretch at least `gap` wide free of boxes: across
    the page (axis 0), into columns, or down it (axis 1), into bands."""
    groups: list[list[TextBox]] = []
    reach = 0.0
    for box in sorted(boxes, key=lambda box: box.box[axis]):
        start, end = box.box[axis], box.box[axis + 2]
        if groups and start - reach < gap:
            groups[-1].append(box)
            reach = max(reach, end)
        else:
            groups.append([box])
            reach = end
    return [tuple(group) for group in groups]


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
    """The printed line as a row. Boxes set apart by a gap wider than a text page's columns
    set the row out in columns, so it stays a line of its own: a table's row, or a label and
    its value. The detector cuts body text at ordinary spaces, never that wide."""
    centre = median(_centre(box) for box in line) * scale
    half = _ROW_HEIGHT_PER_FONT_SIZE * size / 2
    gaps = [(after.box[0] - before.box[2]) * scale for before, after in zip(line, line[1:])]
    return Row(
        text=" ".join(box.text.strip() for box in line),
        x0=line[0].box[0] * scale,
        y0=centre - half,
        x1=line[-1].box[2] * scale,
        y1=centre + half,
        size=size,
        in_columns=any(gap > COLUMN_GAP * size for gap in gaps),
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
