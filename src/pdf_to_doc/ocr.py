"""OCR pages: the OCR engine interface, the converter's second seam, and turning what
an engine reads into rows that page layout treats like rows of a text layer."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from statistics import median
from typing import Literal, Protocol

import cv2
import numpy as np
import pymupdf

from pdf_to_doc.columns import printed_lines, reading_parts
from pdf_to_doc.grids import Grid, GridCell, PartRules, Rules, ruled_tables
from pdf_to_doc.layout import COLUMN_GAP, CellLine, PageRows, PlacedIncompleteTable, PlacedTable, RawCell, Row
from pdf_to_doc.thai import UPPER_MARK
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
# A detector's box also reaches about this share of the font size past each end of its text:
# PaddleOCR's boxes in the synthetic scans' table cells reached 3 to 7 points past text 16 points tall.
_BOX_PADDING = 0.3
# A rule more than this many font sizes inside both ends of a box runs through its text, not its
# padding or its marks. PaddleOCR's boxes reached 0.44 of the font size past text in the synthetic
# scans' cells; on the real samples, one reached 0.53 past the rule beside its text, in small
# print, and two boxes of lines whose upper marks stack high, in tight rows, 0.58 and 0.62 over
# the rule above them. The one box there that held the text of two cells reached 2.9 font sizes
# past the rule on its shorter side.
_THROUGH_A_RULE = 1.0
# A box less tall than this share of the page's usual box can be a copy of a line's marks, boxed
# apart from the line (see `_without_stray_marks`). On the synthetic table pages, such copies were
# 0.45 of the usual box at most.
_STRAY_MARKS = 0.5
# Where such a copy lies along its line is judged by its share of the line's characters, give or
# take this many: marks take no room, so that share is off by a mark or two, and every copy on the
# synthetic table pages lay within 3 characters of an upper vowel or tone mark of its line's.
_MARKS_NEAR = 3
_UPPER_MARK = re.compile(UPPER_MARK)
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

    A ruled table on the image (see `grids`) takes the boxes whose centres lie in its
    cells, and the text-layer rows too, such as a note typed in a cell of a scanned table;
    the boxes and rows outside every cell are the page's rows. Copies of a line's upper marks,
    boxed apart from it, are dropped (see `_without_stray_marks`), a cell's apart from the
    rest, so that none is taken across a rule. A grid none of whose cells holds text is no table.

    A table whose text cannot be placed in its cells with certainty is an incomplete table of its
    printed lines: a grid with a box that runs through one of its rules (see `_through_a_rule`), or
    with text within it that no cell holds, as where a scan lost part of a rule; and rules that make
    no whole grid, with the rows set out under them (see `_part_ruled`).
    """
    width, height = (text_layer.height, text_layer.width) if image.turn % 180 else (text_layer.width, text_layer.height)
    scale = width / image.width
    # Each text-layer row, and where it lies on the image.
    layer = [(row, _turned_row(row, image.turn, text_layer)) for row in text_layer.rows]
    kept = [(row, on_image) for row, on_image in layer if not _reads_better(boxes, on_image, scale)]
    read = tuple(box for box in boxes if not any(_overlaps(box, on_image, scale) for _, on_image in kept))
    texts = [box for box in read if box.text.strip()]
    unit = median(map(_height, texts)) if texts else 0.0
    rules = ruled_tables(_pixels(image), unit) if texts else Rules()
    layer_rows = [_LayerRow.of(row, on_image, scale) for row, on_image in kept]
    in_cells, outside = _in_cells([*texts, *layer_rows], rules.grids)
    # A cell's boxes are looked at apart from the rest, so no copy is taken across a rule.
    in_cells = {cell: _without_stray_marks(boxes_in_cell, unit) for cell, boxes_in_cell in in_cells.items()}
    outside = tuple(_without_stray_marks(outside, unit))
    reach = _THROUGH_A_RULE * unit / _BOX_HEIGHT_PER_FONT_SIZE
    whole: list[Grid] = []
    incomplete: list[list[TextBox]] = []
    # Rules round no text, such as the printed dots of a watermark, make no table.
    for grid in (grid for grid in rules.grids if any(in_cells.get(cell) for cell in grid.cells)):
        stray = [box for box in outside if _centred_in(box, grid.box)]
        if stray or any(_through_a_rule(box, cell, reach) for cell in grid.cells for box in in_cells.get(cell, [])):
            outside = _without(outside, stray)
            incomplete.append([*(box for cell in grid.cells for box in in_cells.pop(cell, [])), *stray])
        else:
            whole.append(grid)
    grids = tuple(whole)
    for part_rules in rules.parts:
        taken, outside = _part_ruled(part_rules, outside, unit, reach)
        incomplete.append(taken)
    lines_by_table = [printed_lines(tuple(boxes)) for boxes in incomplete if boxes]
    read = tuple(box for box in outside if not isinstance(box, _LayerRow))
    parts = _reading_parts(read, tuple(box for box in outside if isinstance(box, _LayerRow)))
    lines_by_part = [printed_lines(tuple(box for box in part if not isinstance(box, _LayerRow))) for part in parts]
    lines = [line for part_lines in lines_by_part for line in part_lines]
    lines_in_cells = {cell: printed_lines(tuple(boxes_in_cell)) for cell, boxes_in_cell in in_cells.items()}
    # The font size is told by the engine's boxes; a text-layer row's height is its own font's.
    cell_lines = [
        line
        for printed in lines_in_cells.values()
        for line in printed
        if not all(isinstance(box, _LayerRow) for box in line)
    ]
    table_lines = [line for table in lines_by_table for line in table if not all(isinstance(box, _LayerRow) for box in line)]
    line_heights = [_line_height(line) for line in [*lines, *cell_lines, *table_lines]]
    size = median(line_heights) * scale / _BOX_HEIGHT_PER_FONT_SIZE if line_heights else 0.0
    tables = tuple(_table(grid, lines_in_cells, scale, size) for grid in grids)
    incomplete_tables = tuple(_incomplete_table(table, scale, size) for table in lines_by_table)
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
    return PageRows(
        rows=tuple(rows), width=width, height=height, tables=tables, incomplete_tables=incomplete_tables, kind="ocr"
    )


def _without_stray_marks(boxes: Sequence[TextBox], unit: float) -> list[TextBox]:
    """The boxes without the copies of a line's upper marks that the detector boxed apart from the
    line, and read as junk such as "ญ": the line's own reading already holds them. A box is such a
    copy only when it is short, and sits over the top half of another box, which spans it across the
    page and whose text holds upper vowels or tone marks where it lies. Short text of its own, such
    as a "-" or a footnote's number, has no such box around it, or sits lower."""
    return [box for box in boxes if not any(_copies_marks_of(under, box, unit) for under in boxes)]


def _copies_marks_of(under: TextBox, box: TextBox, unit: float) -> bool:
    """Whether the box is a copy of the upper marks of the box under it, as `_without_stray_marks` tells them."""
    if _height(box) >= _STRAY_MARKS * unit:
        return False
    spanned = under.box[0] <= box.box[0] and box.box[2] <= under.box[2]
    over_its_top = under.box[1] < box.box[3] and _centre(box) < _centre(under)
    if not (spanned and over_its_top):
        return False
    at = round((_centre_across(box) - under.box[0]) / _width(under) * len(under.text))
    return bool(_UPPER_MARK.search(under.text[max(0, at - _MARKS_NEAR) : at + _MARKS_NEAR + 1]))


def _in_cells(boxes: list[TextBox], grids: tuple[Grid, ...]) -> tuple[dict[GridCell, list[TextBox]], tuple[TextBox, ...]]:
    """The boxes in each cell of the grids, and the boxes outside every cell: the engine's, and
    text-layer rows as boxes. A box goes to the cell that holds its centre: the engine's boxes reach
    over the rules around their text only by the detector's padding, and no box crossed a rule
    through its middle on the test pages."""
    in_cells: dict[GridCell, list[TextBox]] = {}
    outside: list[TextBox] = []
    for box in boxes:
        x, y = _centre_across(box), _centre(box)
        home = next(
            (
                cell
                for grid in grids
                for cell in grid.cells
                if cell.box[0] <= x <= cell.box[2] and cell.box[1] <= y <= cell.box[3]
            ),
            None,
        )
        if home:
            in_cells.setdefault(home, []).append(box)
        else:
            outside.append(box)
    return in_cells, tuple(outside)


def _through_a_rule(box: TextBox, cell: GridCell, reach: float) -> bool:
    """Whether the box runs through a rule of its cell, more than `reach` inside both its ends, so
    that its text would belong to the cell beyond too, or, past the table's frame, to what lies
    beside the table. Reaching past a rule by a detector's padding, or by marks stacked over a
    line, it does not."""
    x0, y0, x1, y1 = cell.box
    left, top, right, bottom = box.box
    return any(_through(left, right, edge, reach) for edge in (x0, x1)) or any(
        _through(top, bottom, edge, reach) for edge in (y0, y1)
    )


def _centred_in(box: TextBox, area: Box) -> bool:
    x0, y0, x1, y1 = area
    return x0 <= _centre_across(box) <= x1 and y0 <= _centre(box) <= y1


def _through(start: float, end: float, rule: float, reach: float) -> bool:
    return start + reach < rule < end - reach


def _part_ruled(
    part: PartRules, outside: tuple[TextBox, ...], unit: float, reach: float
) -> tuple[list[TextBox], tuple[TextBox, ...]]:
    """The boxes of the incomplete table that part rules show, and the boxes left outside it.

    It takes the boxes whose centres lie within the rules, and the printed lines that follow
    under them, each less than a box height below the last, with no box running through a
    column's rule: so a sentence under the table ends it. The first such line must be set out in
    two or more columns, as a row is; later ones may lie in one, as the wrapped line of a cell
    does. A boxed row with no row under it shows no table, and its text is read as lines.
    Only boxes whose centres lie across the rules' width are looked at, so the column beside a
    table in a column is left to be read on its own."""
    x0, y0, x1, y1 = part.box
    within = [box for box in outside if x0 <= _centre_across(box) <= x1]
    taken = [box for box in within if y0 <= _centre(box) <= y1]
    rows, bottom = part.rows, y1  # rows counts ruled rows and lines taken under them
    for line in printed_lines(tuple(box for box in within if _centre(box) > y1)):
        # Which of the spaces between the rules each box's centre lies in.
        set_out = {sum(edge < _centre_across(box) for edge in part.columns) for box in line}
        if (
            min(box.box[1] for box in line) - bottom >= unit
            or (len(set_out) < 2 and rows == part.rows)
            or any(_through(box.box[0], box.box[2], edge, reach) for box in line for edge in part.columns)
        ):
            break
        taken += line
        rows, bottom = rows + 1, max(box.box[3] for box in line)
    if rows < 2:
        return [], outside
    return taken, _without(outside, taken)


def _without(boxes: tuple[TextBox, ...], taken: list[TextBox]) -> tuple[TextBox, ...]:
    """The boxes but those taken, each told by itself: two boxes can read the same."""
    return tuple(box for box in boxes if not any(box is other for other in taken))


def _incomplete_table(lines: list[list[TextBox]], scale: float, size: float) -> PlacedIncompleteTable:
    """The printed lines of an incomplete table as rows on the page, in points, and where it lies."""
    boxes = [box for line in lines for box in line]
    return PlacedIncompleteTable(
        x0=min(box.box[0] for box in boxes) * scale,
        top=min(box.box[1] for box in boxes) * scale,
        x1=max(box.box[2] for box in boxes) * scale,
        bottom=max(box.box[3] for box in boxes) * scale,
        rows=tuple(_row(line, scale, size) for line in lines),
    )


def _table(grid: Grid, lines_in_cells: dict[GridCell, list[list[TextBox]]], scale: float, size: float) -> PlacedTable:
    """The grid as a table on the page, in points, each cell holding its printed lines. A place
    in the grid that no cell covers is an empty cell, so the columns stay aligned."""
    starts = {(cell.row, cell.column): cell for cell in grid.cells}
    covered = {
        (cell.row + down, cell.column + across)
        for cell in grid.cells
        for down in range(cell.rowspan)
        for across in range(cell.colspan)
    }
    rows = []
    for row in range(grid.rows):
        cells = []
        for column in range(grid.columns):
            if (row, column) in starts:
                cell = starts[(row, column)]
                lines = tuple(_cell_line(line, scale, size) for line in lines_in_cells.get(cell, []))
                x0, y0, x1, y1 = (edge * scale for edge in cell.box)
                cells.append(RawCell(lines, cell.rowspan, cell.colspan, (x0, y0, x1, y1)))
            elif (row, column) not in covered:
                cells.append(RawCell(lines=()))
        rows.append(tuple(cells))
    x0, top, x1, bottom = (edge * scale for edge in grid.box)
    return PlacedTable(x0=x0, top=top, x1=x1, bottom=bottom, rows=tuple(rows))


def _cell_line(line: list[TextBox], scale: float, size: float) -> CellLine:
    """A printed line in a cell, and where its text sits, in points: within its boxes, by the
    detector's padding, as a cell's line on a text page is measured by its characters."""
    x0, x1 = line[0].box[0] * scale, max(box.box[2] for box in line) * scale
    padding = min(_BOX_PADDING * size, (x1 - x0) / 2)
    return CellLine(
        text=" ".join(box.text.strip() for box in line),
        x0=x0 + padding,
        x1=x1 - padding,
        centre=median(_centre(box) for box in line) * scale,
        size=size,
        pieces=_pieces(line),
    )


def _pieces(line: list[TextBox]) -> tuple[Piece, ...]:
    """What a printed line was read from. A text-layer row's text is exact, and never uncertain."""
    return tuple(Piece(box.text) if isinstance(box, _LayerRow) else Piece(box.text, box.confidence) for box in line)


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
    return reading_parts(boxes, median(_height(box) for box in read)) if read else [boxes]


def _turned_row(row: Row, turn: int, page: PageRows) -> Row:
    """Where the row lies once the page is turned `turn` degrees clockwise."""
    x0, y0, x1, y1 = turned_box((row.x0, row.y0, row.x1, row.y1), turn, page.width, page.height)
    return replace(row, x0=x0, y0=y0, x1=x1, y1=y1)


def _placed(row: Row, across: float, down: float) -> Row:
    """The row moved to the same share of a page `across` times as wide and `down` times as tall."""
    return replace(row, x0=row.x0 * across, y0=row.y0 * down, x1=row.x1 * across, y1=row.y1 * down)


def _row(line: list[TextBox], scale: float, size: float) -> Row:
    """The printed line as a row. Boxes set apart by a gap as wide as a text page's tab stops
    set its parts apart (`in_columns`), so it stays a line of its own: a table's row, or a label
    and its value. On the corpus's scans, only such rows, signature lines and junk had a gap
    that wide; the detector cuts body text at ordinary spaces."""
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
        pieces=_pieces(line),
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


def _centre_across(box: TextBox) -> float:
    return (box.box[0] + box.box[2]) / 2


def _height(box: TextBox) -> float:
    return box.box[3] - box.box[1]


def _width(box: TextBox) -> float:
    return box.box[2] - box.box[0]


def _area(box: TextBox) -> float:
    return _width(box) * _height(box)
