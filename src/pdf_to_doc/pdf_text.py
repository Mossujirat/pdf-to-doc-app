"""Reads the text layer of PDF pages: printed rows, and ruled tables with their cells."""

from dataclasses import dataclass
from typing import Any

import pymupdf

from pdf_to_doc.layout import EDGE_BAND, PageRows, PlacedTable, RawCell, Row, page_blocks
from pdf_to_doc.model import Document, Page
from pdf_to_doc.thai import is_thai

# PyMuPDF's defaults, except that a glyph with no Unicode mapping comes out as
# U+FFFD (visible, and countable when validating the text layer) instead of
# U+0000 (invisible in the output).
_FLAGS = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE
# A gap wider than this share of the font size separates two words; wider than
# the column gap, it separates them whatever their script, as a tab stop does.
_WORD_GAP = 0.2
_COLUMN_GAP = 2.0
# Within a printed line, a gap wider than this share of the font size ends a word,
# for deciding which table cell the word belongs to.
_WORD_BREAK_GAP = 0.5
# Cell edges closer than this (points) are the same grid line.
_GRID_TOLERANCE = 1.0
# Lines whose baselines differ by less than this share of the font size are on one row.
_BASELINE_TOLERANCE = 0.3

# PyMuPDF's table finder otherwise prints a suggestion to install another package.
pymupdf.no_recommend_layout()

Box = tuple[float, float, float, float]


def read_pdf(source: bytes) -> Document:
    with pymupdf.open(stream=source, filetype="pdf") as pdf:
        blocks_by_page = page_blocks([_read_page(page) for page in pdf])
    return Document(
        pages=tuple(
            Page(number=index + 1, kind="text", blocks=blocks)
            for index, blocks in enumerate(blocks_by_page)
        )
    )


@dataclass(frozen=True)
class _Char:
    text: str
    box: Box
    size: float
    bold: bool
    line: int  # index of the printed line it belongs to


@dataclass(frozen=True)
class _Word:
    """Characters that belong together; a word goes to one table cell, never split."""

    chars: tuple[_Char, ...]

    @property
    def start(self) -> float:
        return self.chars[0].box[0]

    @property
    def baseline(self) -> float:
        return max(char.box[3] for char in self.chars)

    def centre_inside(self, box: Box) -> bool:
        x = (min(char.box[0] for char in self.chars) + max(char.box[2] for char in self.chars)) / 2
        y = (min(char.box[1] for char in self.chars) + self.baseline) / 2
        return _inside(x, y, box)

    def starts_inside(self, box: Box) -> bool:
        first = self.chars[0].box
        return _inside((first[0] + first[2]) / 2, (first[1] + first[3]) / 2, box)


def _inside(x: float, y: float, box: Box) -> bool:
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def _read_page(page: pymupdf.Page) -> PageRows:
    """Every character on the page ends up exactly once: in a table cell, or in a row."""
    layout: dict[str, Any] = page.get_text("rawdict", flags=_FLAGS)
    lines = [line for block in layout["blocks"] if block["type"] == 0 for line in block["lines"]]
    words = [word for index, line in enumerate(lines) for word in _words(index, line)]
    taken: set[int] = set()  # positions of words already given to a cell
    tables = tuple(_place_table(table, words, taken) for table in _ruled_tables(page))
    left_by_line: dict[int, list[_Char]] = {}
    for position, word in enumerate(words):
        if position not in taken:
            for char in word.chars:
                left_by_line.setdefault(char.line, []).append(char)
    rows = tuple(
        _row(chars) for _, chars in sorted(left_by_line.items()) if any(not char.text.isspace() for char in chars)
    )
    return PageRows(rows=rows, width=page.rect.width, height=page.rect.height, tables=tables)


def _words(index: int, line: dict[str, Any]) -> list[_Word]:
    """Split a printed line at spaces and wide gaps; spaces stay with the word before them."""
    words: list[list[_Char]] = []
    previous: _Char | None = None
    for span in line["spans"]:
        bold = _is_bold(span)
        for raw in span["chars"]:
            x0, y0, x1, y1 = raw["bbox"]
            char = _Char(raw["c"], (x0, y0, x1, y1), span["size"], bold, index)
            starts_word = (
                previous is None
                or (previous.text.isspace() and not char.text.isspace())
                or char.box[0] - previous.box[2] > _WORD_BREAK_GAP * char.size
            )
            if starts_word:
                words.append([char])
            else:
                words[-1].append(char)
            previous = char
    return [_Word(tuple(chars)) for chars in words]


def _row(chars: list[_Char]) -> Row:
    return Row(
        text=_text_of(chars),
        x0=min(char.box[0] for char in chars),
        y0=min(char.box[1] for char in chars),
        x1=max(char.box[2] for char in chars),
        y1=max(char.box[3] for char in chars),
        size=round(max(char.size for char in chars), 1),
        bold=all(char.bold for char in chars if not char.text.isspace()),
    )


def _ruled_tables(page: pymupdf.Page) -> list[Any]:
    """Ruled tables on the page, leaving out tables inside other tables, and boxes at
    the page edge, which are ruled headers and footers (page furniture) more often."""
    if not _has_rules(page):
        return []
    found = page.find_tables().tables
    band = EDGE_BAND * page.rect.height
    return [
        table
        for table in found
        if not any(other is not table and pymupdf.Rect(other.bbox).contains(pymupdf.Rect(table.bbox)) for other in found)
        and not (table.bbox[3] <= band or table.bbox[1] >= page.rect.height - band)
    ]


def _has_rules(page: pymupdf.Page) -> bool:
    """Whether the page draws any lines or boxes; a ruled table needs them."""
    return any(item[0] in ("l", "re", "qu") for drawing in page.get_cdrawings() for item in drawing["items"])


def _place_table(table: Any, words: list[_Word], taken: set[int]) -> PlacedTable:
    """The table's cells with their spans, and the words that belong in each.

    Words are assigned whole, never clipped to the cell box: vowels and tone
    marks reach past a tight box, and text can spill over a rule. A word belongs
    to the cell holding its centre, or else to the cell it starts in, as when
    the last column's text runs past the table's edge. A position with no box of
    its own and no merged cell over it becomes an empty cell, so the columns
    stay aligned.
    """
    boxes = [box for row in table.rows for box in row.cells if box]
    words_in: list[list[_Word]] = [[] for _ in boxes]  # by the box's place in `boxes`
    for position, word in enumerate(words):
        if position in taken:
            continue
        home = next((index for index, box in enumerate(boxes) if word.centre_inside(box)), None)
        if home is None:
            home = next((index for index, box in enumerate(boxes) if word.starts_inside(box)), None)
        if home is not None:
            taken.add(position)
            words_in[home].append(word)
    column_lines = _grid_lines([box[0] for box in boxes] + [box[2] for box in boxes])
    row_lines = _grid_lines([box[1] for box in boxes] + [box[3] for box in boxes])
    covered: set[tuple[int, int]] = set()
    box_index = -1
    rows = []
    for row_index, row in enumerate(table.rows):
        cells = []
        for column_index, box in enumerate(row.cells):
            if box:
                box_index += 1
            if (row_index, column_index) in covered:
                continue
            if not box:
                cells.append(RawCell(lines=()))
                continue
            rowspan = _span(row_lines, box[1], box[3])
            colspan = _span(column_lines, box[0], box[2])
            covered.update(
                (r, c)
                for r in range(row_index, row_index + rowspan)
                for c in range(column_index, column_index + colspan)
            )
            cells.append(RawCell(lines=_cell_lines(words_in[box_index]), rowspan=rowspan, colspan=colspan))
        rows.append(tuple(cells))
    return PlacedTable(top=table.bbox[1], bottom=table.bbox[3], rows=tuple(rows))


def _grid_lines(edges: list[float]) -> list[float]:
    lines: list[float] = []
    for edge in sorted(edges):
        if not lines or edge - lines[-1] > _GRID_TOLERANCE:
            lines.append(edge)
    return lines


def _span(grid: list[float], start: float, end: float) -> int:
    """How many grid intervals lie between two edges."""
    return max(1, sum(1 for line in grid if start + _GRID_TOLERANCE < line < end + _GRID_TOLERANCE))


def _cell_lines(words: list[_Word]) -> tuple[str, ...]:
    """A cell's printed lines, top to bottom.

    Words keep their own characters together, in the order they were printed.
    Words that a wide gap set apart, as a tab stop does, are joined with a space.
    """
    lines: list[list[_Word]] = []
    for word in sorted(words, key=lambda word: (word.baseline, word.start)):
        if lines and abs(word.baseline - lines[-1][0].baseline) <= _BASELINE_TOLERANCE * word.chars[0].size:
            lines[-1].append(word)
        else:
            lines.append([word])
    texts = []
    for line in lines:
        text = ""
        for word in sorted(line, key=lambda word: word.start):
            piece = _text_of(list(word.chars))
            if text and not text[-1].isspace() and not piece[:1].isspace():
                text += " "
            text += piece
        texts.append(text)
    return tuple(texts)


def _is_bold(span: dict[str, Any]) -> bool:
    return bool(span["flags"] & pymupdf.TEXT_FONT_BOLD) or "bold" in span["font"].lower()


def _text_of(chars: list[_Char]) -> str:
    """Characters of one printed line, with spaces where words are set apart.

    PyMuPDF already separates Latin words that are set apart without a space
    character, and never splits Thai. It does not separate Thai from a
    neighbouring Latin word, nor pieces set apart by tab stops, so those
    boundaries are handled here.
    """
    text = ""
    previous_end = 0.0
    for char in chars:
        start, end = char.box[0], char.box[2]
        if text and _starts_a_new_word(text[-1], char.text, start - previous_end, char.size):
            text += " "
        text += char.text
        previous_end = end
    return text


def _starts_a_new_word(before: str, after: str, gap: float, font_size: float) -> bool:
    if before.isspace() or after.isspace():
        return False
    return gap > _COLUMN_GAP * font_size or (gap > _WORD_GAP * font_size and is_thai(before) != is_thai(after))
