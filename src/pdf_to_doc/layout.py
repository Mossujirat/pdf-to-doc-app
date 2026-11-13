"""Page layout: turns the printed rows of each page, read from its text layer or with OCR, into document structure."""

import re
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass, replace
from difflib import SequenceMatcher

from pdf_to_doc.model import (
    DEEPEST_HEADING,
    Block,
    Heading,
    IncompleteTable,
    KeptImage,
    ListItem,
    PageKind,
    Paragraph,
    Placeholder,
    Span,
    Table,
    TableCell,
)
from pdf_to_doc.thai import DIGITS, MARK, THAI_CONSONANT, THAI_LETTER, THAI_WORD_START, join_lines, repair
from pdf_to_doc.uncertain import LOW_CONFIDENCE, Piece, uncertain_spans
from pdf_to_doc.words import first_word

# Rows this close to the top or bottom edge (share of page height) can be page furniture.
EDGE_BAND = 0.10
_NUMBER = DIGITS
_DASHES = r"[\s\-–—|]*"
# A page counter at the end of a row: "หน้าที่ 2/7", "หน้า 3 จาก 9", "Page 4 of 10",
# "Page | 6". The word must not end another Thai word, as in "ล่วงหน้า".
_PAGE_COUNTER = re.compile(
    rf"(?<!{THAI_LETTER})(?:หน้า(?:ที่)?|page){_DASHES}(?P<page>{_NUMBER})"
    rf"(?:\s*(?:/|จาก|of)\s*{_NUMBER})?{_DASHES}$",
    re.IGNORECASE,
)
# A row that is only a page number, such as "7", "- 7 -" or "7/12".
_BARE_PAGE_NUMBER = re.compile(rf"{_DASHES}(?P<page>{_NUMBER})(?:\s*/\s*{_NUMBER})?{_DASHES}")
# A number at the end of a row, after a space, with no word for "page" before it, as a form's
# footer numbers its pages: "Form 1.3 5", "Ref: 0042 2/7". On an OCR page it can be a page number.
_TRAILING_NUMBER = re.compile(rf"\s(?P<page>{_NUMBER})(?:\s*/\s*{_NUMBER})?$")
# On an OCR page, page furniture is also found where OCR reads it a little differently on each
# page, and a little further in than the edge band: within this reach, a share of the page's
# height from an edge, as on a scan pasted into a larger page. Measured on the sample contracts
# (2026-11-11): footers 81% of the way down, page numbers at 87-89%, a header's second line at 10.7%.
_OCR_EDGE_REACH = 0.20
# Rows that OCR read within the reach are the same furniture when their middles lie less than this
# share of the page's height apart: the same furniture moved by up to 1% from page to page on the
# sample contracts, as the scans sat a little differently.
_SAME_HEIGHT = 0.015
# They must also say alike what OCR is sure of: the same, or, when both are at least
# `_ALIKE_LENGTH` characters long, this alike by difflib's ratio, unless they differ in their
# digits alone, which says different numbers. On the sample contracts, letterheads and footers
# OCR misread a little scored 0.9 or more; two lines of a body that differ in a word scored 0.81,
# and a form's label repeated in the body 0.79-0.85. Letterheads OCR garbled worse, at 0.80-0.89,
# are left in. Shorter rows, such as a word or a page number, must be the same: one letter
# misread already changes their ratio by a fifth or more.
_ALIKE = 0.9
_ALIKE_LENGTH = 8
# Inside the edge band, a row OCR read is furniture when another page has the same furniture.
# Beyond it, or with its page number found only at the end of the row, it must repeat on at
# least this many pages, one of them next to its own: a form's label repeated on every other
# page, as on the pages of researchers' résumés, is its content. On the sample contracts such
# labels sat at 12-14% on alternate pages.
_FURTHER_IN_PAGES = 3
_DIGIT = re.compile(r"\d")  # Thai digits too
# A numbered list item starts with "1.", "1)", "(1)", "1.2" or "1.2.", or with a Thai
# letter in brackets, "(ก)" or "ก)", followed by a space. "ก." is left out: it is
# also how Thai abbreviates ตำบล, อำเภอ and the like.
_NUMBERED_ITEM = re.compile(rf"^\s*(?:\(?{_NUMBER}(?:\.{_NUMBER})*[.)]|{_NUMBER}(?:\.{_NUMBER})+|\(?{THAI_CONSONANT}\))\s")
# A word at the end of a row that a number follows as a reference, as in "ตามข้อ / 4.2",
# seen on a contract exported from Word: the number on the next row carries on the sentence.
# The words may end another, as in "ตามข้อ" and "หัวข้อ", but not "ทุก", every, which points at
# no number; "หน้า" must end none, as in "ล่วงหน้า". The English words are their counterparts.
_REFERENCE_AT_END = re.compile(
    rf"(?:(?<!ทุก)(?:ข้อ(?:ที่)?|มาตรา|วรรค|หมวด(?:ที่)?|ภาคผนวก|ตารางที่|รูปที่)|(?<!{THAI_LETTER})หน้า"
    r"|\b(?:clause|section|article|paragraph|item|table|figure|annex|appendix|page|no\.))\s*$",
    re.IGNORECASE,
)
# Symbol and Wingdings fonts, which Word draws bullets with, report their glyphs
# as Private Use Area characters in this range.
SYMBOL_FONT_CHARACTERS = f"{chr(0xF000)}-{chr(0xF0FF)}"
# The bullets that start a list item even joined to their word (see `_JOINED_MARKER`). A bullet
# item can also start with "*" or a Symbol font's glyph, but only with a space after it: "*" also
# marks a note, and only a text layer holds those glyphs.
_BULLETS = r"•●○◦▪■□‣⁃∙\-–"
_BULLET_ITEM = re.compile(rf"^\s*[{_BULLETS}*{SYMBOL_FONT_CHARACTERS}]\s+")
# A list marker OCR read joined to the word after it, at the start of a row: "(1)คำ", "(ก)คำ" or
# "-คำ". PaddleOCR drops the space when the marker is set close to the word, as on a sample contract
# and the corpus's `list-markers-scans`. Only before the first letter of a Thai word: a dash before
# a digit is a minus sign. Left out, as running text reads the same:
# - "1." and "1.2": an amount such as "2.5ล้าน", or a wrapped reference such as "4.2ของ";
# - "1)" and "ก)" with no opening bracket: the end of a bracket wrapped onto the row, as in
#   "(ฉบับที่ / 2)ซึ่ง" or "(ภาคผนวก / ก)ซึ่ง".
_JOINED_MARKER = re.compile(rf"^\s*(?:\((?:{_NUMBER}|{THAI_CONSONANT})\)|[{_BULLETS}])(?={THAI_WORD_START})")
# Font sizes closer than this (points) count as the same size within a paragraph.
_SIZE_STEP = 0.5
# Text this much larger than the body can be a heading; heading sizes closer than
# the step (points) share a level; a heading is at most this many rows long.
_HEADING_SCALE = 1.06
_HEADING_SIZE_STEP = 0.6
_HEADING_MAX_ROWS = 2
# An image with this many rows of text printed over it is the page behind the text,
# as on a scan made searchable, or a watermark: not a picture of its own.
_BACKGROUND_ROWS = 3
# A row to sign on: "ลงชื่อ ........", "ลายมือชื่อ", or the English word "Signature". On an OCR
# page the Thai words may have lost their mai ek, the commonest misread: "ลงชือ". Not any mark,
# or "ลงช่อง" ("in the box") would count.
SIGNATURE_LINE = re.compile(r"ลงชื่?อ|ลายมือชื่?อ|\bsignature\b", re.IGNORECASE)
# A signature is at most this share of the page's width and height. On the sample
# contracts the largest was 199 pt wide and 118 pt tall.
_SIGNATURE_MAX_WIDTH = 0.4
_SIGNATURE_MAX_HEIGHT = 0.2
# Images at one edge of two pages are the same furniture when each side differs by
# less than this share, and their centres by less than this many points each way.
# Initials signed at the foot of every page of a sample contract moved up to 21 pt.
_SAME_IMAGE_SIZE = 0.2
_SAME_IMAGE_PLACE = 36.0
# Lines whose baselines differ by less than this share of the font size are on one
# row; a gap wider than this many character widths sets the row out in columns, on
# text pages and OCR pages alike.
_BASELINE_TOLERANCE = 0.3
COLUMN_GAP = 2.0
# A gap between rows this share of the font size wider than the document's usual
# line spacing ends a paragraph. The usual spacing counts for at most the cap: in a
# short document most gaps may be between paragraphs. (Double-spaced text, rare in
# office documents, therefore splits into one paragraph per line.)
_PARAGRAPH_GAP = 0.4
_LINE_GAP_CAP = 0.75
# Items stacked in two cells of a row are on the same sub-row when the middles of their lines
# are less than this share of the font size apart. Lines of one sub-row share a baseline, and
# the next sub-row is a whole line lower, 1.4 font sizes on the corpus's tables.
_SAME_SUB_ROW = 0.4
_THAI_MARK = re.compile(MARK)


@dataclass(frozen=True)
class Row:
    """One printed line of text and where it sits on the page."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    bold: bool = False  # every character in the row is bold
    in_columns: bool = False  # parts of the row are set apart in columns, as with tab stops
    # What the row was read from, in reading order: the OCR engine's boxes, and text
    # from the text layer beside them. Empty for a row taken from the text layer alone.
    pieces: tuple[Piece, ...] = ()
    # The reading order comes to the row from elsewhere on the page, as to the top of a
    # column: it starts a paragraph or list item, as the first row of a page does.
    starts_block: bool = False


@dataclass(frozen=True)
class CellLine:
    """One printed line of a table cell, and where it sits on the page."""

    text: str
    x0: float
    x1: float
    centre: float  # half way down the line
    size: float
    # What the line was read from, as a row's pieces: empty on a text page, whose text layer holds it.
    pieces: tuple[Piece, ...] = ()


@dataclass(frozen=True)
class RawCell:
    """A table cell as printed: its lines of text, before they are joined and repaired."""

    lines: tuple[CellLine, ...]
    rowspan: int = 1
    colspan: int = 1
    box: tuple[float, float, float, float] | None = None  # its ruled edges (x0, y0, x1, y1)


@dataclass(frozen=True)
class PlacedTable:
    """A table found on the page, where it sits, and its cells row by row.

    Each row holds the cells that start in it; a merged cell covers the
    positions its spans reach in the rows and columns after it.
    """

    x0: float
    top: float
    x1: float
    bottom: float
    rows: tuple[tuple[RawCell, ...], ...]


@dataclass(frozen=True)
class PlacedIncompleteTable:
    """An incomplete table found on an OCR page, where it sits, and its printed lines as rows."""

    x0: float
    top: float
    x1: float
    bottom: float
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class PlacedImage:
    """An image drawn on a text page, or on an OCR page that is not a scan, and where it sits."""

    x0: float
    top: float
    x1: float
    bottom: float
    stamp_like: bool = False  # a ring in colour, as a stamp leaves
    kept_image: KeptImage | None = None  # the picture itself, with images kept
    in_scan: bool = False  # found inside a scan's image, where OCR read its ink as junk


@dataclass(frozen=True)
class PageRows:
    rows: tuple[Row, ...]  # text outside tables
    width: float
    height: float
    tables: tuple[PlacedTable, ...] = ()
    incomplete_tables: tuple[PlacedIncompleteTable, ...] = ()  # on OCR pages only
    images: tuple[PlacedImage, ...] = ()
    # On an OCR page the font size is estimated, so it cannot tell headings apart.
    kind: PageKind = "text"


def page_blocks(pages: list[PageRows]) -> list[tuple[Block, ...]]:
    """The blocks of each page: page furniture removed, rows grouped into headings,
    list items and paragraphs. Headings come from text pages only."""
    pages = remove_page_furniture([replace(page, rows=_join_on_baselines(page.rows)) for page in pages])
    line_gap = _usual_line_gap(pages)
    groups_by_page = [_group_rows(page, line_gap) for page in pages]
    text_pages = [(groups, page) for groups, page in zip(groups_by_page, pages) if page.kind == "text"]
    levels = _heading_levels(
        [group for groups, _ in text_pages for group in groups], _body_size([page for _, page in text_pages])
    )
    return [
        _in_reading_order(groups, page, levels if page.kind == "text" else {})
        for groups, page in zip(groups_by_page, pages)
    ]


def _in_reading_order(groups: list[list[Row]], page: PageRows, levels: dict[float, int]) -> tuple[Block, ...]:
    """The page's blocks, with each image placed before the first text that starts below it, and
    each table, incomplete ones too, in the text of its own column (see `_table_place`)."""
    placed: list[tuple[int, float, Block]] = [(_table_place(table, groups), table.top, _table(table)) for table in page.tables]
    placed += [
        (_table_place(table, groups), table.top, _incomplete_table(table)) for table in page.incomplete_tables
    ]
    placed += [
        (_place(image.top, groups), image.top, placeholder)
        for image in page.images
        if (placeholder := _placeholder(image, page))
    ]
    placed.sort(key=lambda item: item[:2])
    blocks: list[Block] = []
    for index, group in enumerate(groups):
        while placed and placed[0][0] <= index:
            blocks.append(placed.pop(0)[2])
        blocks.append(_block(group, levels))
    blocks.extend(block for *_, block in placed)
    return tuple(blocks)


def _place(top: float, groups: list[list[Row]]) -> int:
    """Where something whose top is at `top` goes among the groups: before the first that starts below it."""
    return next((index for index, group in enumerate(groups) if top <= group[0].y0), len(groups))


def _table_place(table: PlacedTable | PlacedIncompleteTable, groups: list[list[Row]]) -> int:
    """Where the table goes among the groups, which are in reading order, a column at a time on a page
    set in columns: before the first that starts below its top and lies under it, or else after the
    last above it that does, so that it is read in its own column. A table under no text is placed
    by its top alone."""
    under = [index for index, group in enumerate(groups) if any(_across(table, row) for row in group)]
    below = [index for index in under if table.top <= groups[index][0].y0]
    if below:
        return below[0]
    return under[-1] + 1 if under else _place(table.top, groups)


def _across(table: PlacedTable | PlacedIncompleteTable, row: Row) -> bool:
    """Whether the row and the table overlap across the page, one above the other."""
    return table.x0 < row.x1 and row.x0 < table.x1


def stands_in(image: PlacedImage, rows_over: int) -> bool:
    """Whether a placeholder stands for the image, with this many rows printed over it: always for a
    stamp, wherever it is pressed, even over a whole signature block; for any other image, unless
    enough rows are printed over it for it to be the page behind them."""
    return image.stamp_like or rows_over < _BACKGROUND_ROWS


def _rows_over(image: PlacedImage, rows: tuple[Row, ...]) -> int:
    """How many of the rows are printed over the image: their middles lie within it."""
    return sum(
        image.x0 <= (row.x0 + row.x1) / 2 <= image.x1 and image.top <= (row.y0 + row.y1) / 2 <= image.bottom
        for row in rows
    )


def _placeholder(image: PlacedImage, page: PageRows) -> Placeholder | None:
    """What stands in for the image, or None when it is the page behind the text (see `stands_in`).
    With images kept, it carries the picture.

    A stamp when the image is a ring in colour. A signature when it is small and sits on a row to
    sign on, or just above or below one. When it is unclear what an image shows, it is only an
    image: the converter does not guess.
    """
    if not stands_in(image, _rows_over(image, page.rows)):
        return None
    if image.stamp_like:
        return Placeholder("stamp", image.kept_image)
    small = (
        image.x1 - image.x0 <= _SIGNATURE_MAX_WIDTH * page.width
        and image.bottom - image.top <= _SIGNATURE_MAX_HEIGHT * page.height
    )
    if small and any(SIGNATURE_LINE.search(row.text) and next_to(image, row) for row in page.rows):
        return Placeholder("signature", image.kept_image)
    return Placeholder("image", image.kept_image)


def next_to(image: PlacedImage, row: Row) -> bool:
    """Whether the image and the row overlap across the page, and lie less than a row's height apart down it."""
    across = image.x0 < row.x1 and row.x0 < image.x1
    down = row.y0 - image.bottom <= row.size and image.top - row.y1 <= row.size
    return across and down


def _table(placed: PlacedTable) -> Table:
    """The table as a reader takes it: items stacked in a row's cells that line up across them
    are sub-rows, and each cell's printed lines are joined into its items. What OCR read in a
    cell can be uncertain, as in a paragraph."""
    return Table(rows=tuple(tuple(_table_cell(cell) for cell in row) for row in _with_sub_rows(placed.rows)))


def _incomplete_table(placed: PlacedIncompleteTable) -> IncompleteTable:
    """The incomplete table as a reader takes it: each printed line a paragraph of its own."""
    texts = [(repair(row.text), row) for row in placed.rows]
    return IncompleteTable(rows=tuple(Paragraph(text, _uncertain(text, [row])) for text, row in texts if text))


def _table_cell(cell: RawCell) -> TableCell:
    text = _cell_text(cell)
    uncertain = uncertain_spans(text, [piece for line in cell.lines for piece in line.pieces])
    return TableCell(text, cell.rowspan, cell.colspan, uncertain)


def _with_sub_rows(rows: tuple[tuple[RawCell, ...], ...]) -> list[list[RawCell]]:
    """The rows, each row whose cells stack items that line up across them split into a sub-row
    per item. The row's other cells, and the cells above that reach into it, span its sub-rows."""
    splits = [_sub_rows(row) for row in rows]
    counts = [count for count, _ in splits]
    split_rows: list[list[RawCell]] = []
    for row_index, (row, (count, lined_up)) in enumerate(zip(rows, splits)):
        parts: list[list[RawCell]] = [[] for _ in range(count)]
        for cell_index, cell in enumerate(row):
            if cell_index in lined_up:
                for part, line in zip(parts, cell.lines):
                    part.append(replace(cell, lines=(line,)))
            else:
                parts[0].append(replace(cell, rowspan=sum(counts[row_index : row_index + cell.rowspan])))
        split_rows += parts
    return split_rows


def _sub_rows(row: tuple[RawCell, ...]) -> tuple[int, set[int]]:
    """How many sub-rows the row splits into, and which of its cells hold them: two or more cells
    that each stack as many items, more than one, on lines that line up across them. A cell whose
    lines wrap holds a sentence, not items. (1, no cells) when the row does not split."""
    itemised = [
        cell_index
        for cell_index, cell in enumerate(row)
        if cell.rowspan == 1
        and len(cell.lines) > 1
        and not any(_wraps(line, following, cell) for line, following in zip(cell.lines, cell.lines[1:]))
    ]
    for cell_index in itemised:
        lined_up = {other for other in itemised if _lines_up(row[cell_index], row[other])}
        if len(lined_up) > 1:
            return len(row[cell_index].lines), lined_up
    return 1, set()


def _lines_up(cell: RawCell, other: RawCell) -> bool:
    return len(cell.lines) == len(other.lines) and all(
        abs(line.centre - beside.centre) <= _SAME_SUB_ROW * max(line.size, beside.size)
        for line, beside in zip(cell.lines, other.lines)
    )


def _cell_text(cell: RawCell) -> str:
    """The cell's printed lines as a reader takes them: a line that wraps joins the next by the
    Thai line rules, and a line that ends short of its cell ends an item, which keeps its break."""
    items: list[list[str]] = []
    for previous, line in zip((None, *cell.lines), cell.lines):
        if previous and _wraps(previous, line, cell):
            items[-1].append(line.text)
        else:
            items.append([line.text])
    return "\n".join(text for text in (repair(join_lines(item)) for item in items) if text)


def _wraps(line: CellLine, following: CellLine, cell: RawCell) -> bool:
    """Whether the line wraps into the next, as Word wraps a line: the line and the next line's
    first word would not have fitted across the cell together. Judged by widths, so it holds
    for text set flush left, flush right or centred. The cell's padding is the least room its
    text leaves at either edge, at most half a font size, as short centred lines leave more."""
    assert cell.box, "a cell that holds lines has a box"
    left, _, right, _ = cell.box
    padding = min(min(each.x0 for each in cell.lines) - left, right - max(each.x1 for each in cell.lines), line.size / 2)
    return line.x1 - line.x0 + _first_word_width(following) > right - left - 2 * max(padding, 0.0)


def _first_word_width(line: CellLine | Row) -> float:
    """How wide the line's first word is, by its share of the line's letters. Marks above and
    below the letters take no room."""
    letters = len(_THAI_MARK.sub("", line.text.strip()))
    return (line.x1 - line.x0) * len(_THAI_MARK.sub("", first_word(line.text))) / letters if letters else 0.0


def _heading_levels(groups: list[list[Row]], body_size: float) -> dict[float, int]:
    """Heading level by font size: the largest size is level 1."""
    sizes = sorted(
        {group[0].size for group in groups if len(group) <= _HEADING_MAX_ROWS and group[0].size >= body_size * _HEADING_SCALE},
        reverse=True,
    )
    levels: dict[float, int] = {}
    level = 0
    for index, size in enumerate(sizes):
        if index == 0 or sizes[index - 1] - size > _HEADING_SIZE_STEP:
            level += 1
        levels[size] = level
    return levels


def _join_on_baselines(rows: tuple[Row, ...]) -> tuple[Row, ...]:
    """Rejoin pieces of one printed line.

    PyMuPDF splits a printed line at wide gaps, such as tab stops, into separate
    lines; consecutive pieces on one baseline, left to right, become one row.
    """
    joined: list[Row] = []
    for row in rows:
        previous = joined[-1] if joined else None
        if previous and abs(row.y1 - previous.y1) <= _BASELINE_TOLERANCE * row.size and row.x0 >= previous.x1:
            joined[-1] = replace(
                previous,
                text=f"{previous.text.rstrip()} {row.text.lstrip()}",
                x1=row.x1,
                y0=min(previous.y0, row.y0),
                y1=max(previous.y1, row.y1),
                bold=previous.bold and row.bold,
                in_columns=previous.in_columns or row.x0 - previous.x1 > COLUMN_GAP * row.size,
                pieces=_pieces(previous) + _pieces(row) if previous.pieces or row.pieces else (),
            )
        else:
            joined.append(row)
    return tuple(joined)


def body_text_share(page: PageRows) -> float:
    """The share of the page that its rows and tables cover outside the edge bands."""
    area = sum(
        (row.x1 - row.x0) * (row.y1 - row.y0) for row in page.rows if row.text.strip() and not _edge(row.y0, row.y1, page)
    )
    area += sum((table.bottom - table.top) * page.width for table in page.tables)
    return area / (page.width * page.height)


def _edge(top: float, bottom: float, page: PageRows) -> str | None:
    """The edge whose band a row or image from `top` to `bottom` starts or ends in, where page furniture sits."""
    band = EDGE_BAND * page.height
    return "top" if top <= band else "bottom" if bottom >= page.height - band else None


def remove_page_furniture(pages: list[PageRows]) -> list[PageRows]:
    """Drop page furniture: rows at the same edge (top or bottom) that repeat on two or more
    pages, and images of the same size in about the same place at an edge of two or more pages.
    On OCR pages, rows that OCR read alike are furniture too, some of them further in and on
    three pages or more (see `_furniture_read_alike`).

    Page numbers must follow the pages: a printed number repeats only if it
    stays the same distance from the PDF's own page number. A row near the edge
    of only one page is kept, unless the whole row is a page counter. So is an
    image near the edge of only one page.

    Pictures found in scans, such as initials at the foot of each page, go with what OCR read in
    them (see `_read_in_furniture`).
    """
    keys = [[_furniture_key(row, page, number) for row in page.rows] for number, page in enumerate(pages, 1)]
    pages_per_key = Counter(key for page_keys in keys for key in set(page_keys) if key)
    read_alike = _furniture_read_alike(pages)
    images = [[(image, _edge(image.top, image.bottom, page)) for image in page.images] for page in pages]
    furniture = [
        [image for image, edge in page_images if edge and any(_repeats(image, edge, others) for others in images if others is not page_images)]
        for page_images in images
    ]
    in_scans = [[image for image in page_furniture if image.in_scan] for page_furniture in furniture]
    everywhere = [image for page_in_scans in in_scans for image in page_in_scans]
    return [
        replace(
            page,
            rows=tuple(
                row
                for row_index, (row, key) in enumerate(zip(page.rows, page_keys))
                if not (key and (pages_per_key[key] >= 2 or _is_counter_only(row)))
                and (page_index, row_index) not in read_alike
                and not _read_in_furniture(row, own, everywhere)
            ),
            images=tuple(image for image in page.images if image not in page_furniture),
        )
        for page_index, (page, page_keys, page_furniture, own) in enumerate(zip(pages, keys, furniture, in_scans))
    ]


def _read_in_furniture(row: Row, own: list[PlacedImage], everywhere: list[PlacedImage]) -> bool:
    """Whether the row is what OCR read in page furniture found in a scan, such as initials: text
    OCR read whose middle lies in such a picture on its own page, however surely; or a row OCR is
    sure of nothing in, such as a row of dots or a stray letter, beside one (see `next_to`). Beside
    one on any page will do, should the finder have missed the initials on the row's own: on a
    sample contract it found them on seven pages and missed them on one. A text layer's rows are
    exact text, never what OCR read in the ink, and stay."""
    if not (row.pieces and all(piece.confidence is not None for piece in row.pieces)):
        return False
    middle_x, middle_y = (row.x0 + row.x1) / 2, (row.y0 + row.y1) / 2
    if any(image.x0 <= middle_x <= image.x1 and image.top <= middle_y <= image.bottom for image in own):
        return True
    return _nothing_sure(row) and any(next_to(image, row) for image in everywhere)


def _nothing_sure(row: Row) -> bool:
    """Whether OCR is sure of no letter or digit in the row it read."""
    sure = (piece.text for piece in row.pieces if piece.confidence is not None and piece.confidence >= LOW_CONFIDENCE)
    return not any(character.isalnum() for text in sure for character in text)


def _repeats(image: PlacedImage, edge: str, others: list[tuple[PlacedImage, str | None]]) -> bool:
    """Whether another page has an image of the same size in about the same place at the same edge."""

    def close(a: float, b: float, share: float = _SAME_IMAGE_SIZE) -> bool:
        return abs(a - b) <= share * max(a, b)

    def near(a: float, b: float) -> bool:
        return abs(a - b) <= _SAME_IMAGE_PLACE

    return any(
        other_edge == edge
        and close(image.x1 - image.x0, other.x1 - other.x0)
        and close(image.bottom - image.top, other.bottom - other.top)
        and near((image.x0 + image.x1) / 2, (other.x0 + other.x1) / 2)
        and near((image.top + image.bottom) / 2, (other.top + other.bottom) / 2)
        for other, other_edge in others
    )


def _furniture_key(row: Row, page: PageRows, number: int) -> str | None:
    """What the row would look like if it were page furniture, or None if it cannot be.

    Furniture sits near the top or bottom edge and says something: a row of
    dashes near the edge is more likely a table cell. Page counters are replaced
    by their distance from the PDF page number, so "หน้าที่ 2/7" on page 2 and
    "หน้าที่ 3/7" on page 3 match.
    """
    edge = _edge(row.y0, row.y1, page)
    text = " ".join(row.text.split())
    if edge is None or not any(char.isalnum() for char in text):
        return None
    if counter := _page_counter(text):
        offset = int(counter["page"]) - number
        return f"{edge}|{text[: counter.start()].strip()}|page{offset:+d}"
    return f"{edge}|{text}"


def _page_counter(text: str) -> re.Match[str] | None:
    """The page number in a row's text, when the row is only one or ends in a page counter."""
    return _BARE_PAGE_NUMBER.fullmatch(text) or _PAGE_COUNTER.search(text)


@dataclass(frozen=True)
class _Reading:
    """How a row that OCR read near an edge would look if it were page furniture: what OCR is sure
    of in it, and its page number's distance from the PDF page number, if it has one."""

    page: int  # index of its page
    row: int  # index of the row on the page
    edge: str
    middle: float  # share of the page's height
    in_band: bool  # it starts or ends in the edge band
    text: str
    offset: int | None = None
    trailing: bool = False  # the page number is a number at the end of the row


def _furniture_read_alike(pages: list[PageRows]) -> set[tuple[int, int]]:
    """The rows on OCR pages, as (page index, row index), that are page furniture by what OCR read:
    rows near the same edge of other OCR pages, at about the same height, say alike what OCR is
    sure of in them (see `_OCR_EDGE_REACH`). So a letterhead read a little differently on each page
    matches, and a footer whose line holds junk OCR read in initials beside it. Text from the text
    layer is matched by `_furniture_key` alone, as on a text page.

    In the edge band, a row that says the same as on one other page will do. A row that is only
    alike, or further in, or with a page number found only at the end of the row, must repeat on
    `_FURTHER_IN_PAGES` pages, one of them next to its own: two lines of a body a word apart can be
    as alike as a letterhead OCR misread. Two pages that share half the lines of either's body or more are copies of one page, such as a
    form filled in for each of several people: what repeats on them is their content, so neither
    counts for the other. Pages that share a line or two, as a signatory's name, are not.
    """
    readings = [reading for index, page in enumerate(pages) if page.kind == "ocr" for reading in _readings(page, index)]
    body_lines = {index: _body_lines(page) for index, page in enumerate(pages) if page.kind == "ocr"}

    def copies(page: int, other: int) -> bool:
        shared = len(body_lines[page] & body_lines[other])
        return shared > 0 and 2 * shared >= min(len(body_lines[page]), len(body_lines[other]))

    by_edge: dict[str, list[_Reading]] = {}
    for reading in sorted(readings, key=lambda reading: reading.middle):
        by_edge.setdefault(reading.edge, []).append(reading)
    found: set[tuple[int, int]] = set()
    for edge_readings in by_edge.values():
        middles = [reading.middle for reading in edge_readings]
        for reading in edge_readings:
            near = edge_readings[bisect_left(middles, reading.middle - _SAME_HEIGHT) : bisect_right(middles, reading.middle + _SAME_HEIGHT)]
            alike = [
                other
                for other in near
                if other.page != reading.page and _alike(reading, other) and not copies(reading.page, other.page)
            ]
            pages_alike = {other.page for other in alike}
            if reading.in_band and not reading.trailing and any(other.text == reading.text for other in alike):
                found.add((reading.page, reading.row))
            elif len(pages_alike) >= _FURTHER_IN_PAGES - 1 and pages_alike & {reading.page - 1, reading.page + 1}:
                found.add((reading.page, reading.row))
    return found


def _readings(page: PageRows, index: int) -> list[_Reading]:
    """Each way a row that OCR read near an edge of the page can be read as furniture: as it stands,
    and, should a number end it, with that number as its page number. A page counter, as
    `_furniture_key` finds one, is read as one only. A row that holds text from the text layer
    too is left to `_furniture_key`, which matches it exactly."""
    readings: list[_Reading] = []
    for row_index, row in enumerate(page.rows):
        top, bottom = row.y0 / page.height, row.y1 / page.height
        edge = "top" if top <= _OCR_EDGE_REACH else "bottom" if bottom >= 1 - _OCR_EDGE_REACH else None
        text = _sure_text(row)
        read = bool(row.pieces) and all(piece.confidence is not None for piece in row.pieces)
        if edge is None or not read or not any(char.isalnum() for char in text):
            continue
        reading = _Reading(index, row_index, edge, (top + bottom) / 2, _edge(row.y0, row.y1, page) is not None, text)
        if counter := _page_counter(text):
            readings.append(replace(reading, text=text[: counter.start()].strip(), offset=int(counter["page"]) - index))
            continue
        readings.append(reading)
        if number := _TRAILING_NUMBER.search(text):
            readings.append(
                replace(reading, text=text[: number.start()].strip(), offset=int(number["page"]) - index, trailing=True)
            )
    return readings


def _body_lines(page: PageRows) -> set[str]:
    """What OCR is sure of in the page's rows away from its edges (see `_OCR_EDGE_REACH`), each at
    least `_ALIKE_LENGTH` characters long, so that a word that repeats, such as a label, is not
    taken for a copied line."""
    lines = (
        _sure_text(row)
        for row in page.rows
        if row.y0 > _OCR_EDGE_REACH * page.height and row.y1 < (1 - _OCR_EDGE_REACH) * page.height
    )
    return {line for line in lines if len(line) >= _ALIKE_LENGTH}


def _sure_text(row: Row) -> str:
    """The row's text without what OCR is unsure of, such as junk read in initials beside a footer;
    all of it when OCR is sure of none."""
    sure = [piece.text for piece in row.pieces if piece.confidence is None or piece.confidence >= LOW_CONFIDENCE]
    return " ".join(" ".join(sure).split()) or " ".join(row.text.split())


def _alike(reading: _Reading, other: _Reading) -> bool:
    """Whether two readings say the same furniture (see `_OCR_EDGE_REACH`)."""
    if reading.offset != other.offset:
        return False
    if reading.text == other.text:
        return True
    if min(len(reading.text), len(other.text)) < _ALIKE_LENGTH or _DIGIT.sub("", reading.text) == _DIGIT.sub("", other.text):
        return False
    matcher = SequenceMatcher(None, reading.text, other.text, autojunk=False)
    return matcher.real_quick_ratio() >= _ALIKE and matcher.quick_ratio() >= _ALIKE and matcher.ratio() >= _ALIKE


def _is_counter_only(row: Row) -> bool:
    """A row that says nothing but "หน้าที่ x/y" or "Page x of y"."""
    counter = _PAGE_COUNTER.search(row.text.strip())
    return bool(counter and counter.start() == 0)


def _usual_line_gap(pages: list[PageRows]) -> float:
    """The usual space between one row and the next, across the whole document.

    Most rows sit inside multi-line paragraphs, so the median is the line
    spacing, whether the document is set single, 1.5 or double spaced.
    """
    gaps = sorted(
        row.y0 - previous.y1
        for page in pages
        for previous, row in zip(page.rows, page.rows[1:])
        if abs(row.size - previous.size) <= _SIZE_STEP and 0 <= row.y0 - previous.y1 < 2 * row.size
    )
    return gaps[len(gaps) // 2] if gaps else 0.0


def _group_rows(page: PageRows, line_gap: float) -> list[list[Row]]:
    """Group the rows of one page into paragraphs and list items, in reading order."""
    rows = [row for row in page.rows if row.text.strip()]
    # Where full lines end, assuming the side margins match.
    right_edge = page.width - min((row.x0 for row in rows), default=0.0)
    groups: list[list[Row]] = []
    for row in rows:
        # A paragraph never runs across a table that starts between two of its rows, under them;
        # beside a table in the next column, it carries on.
        table_between = bool(groups) and any(
            groups[-1][-1].y0 < table.top <= row.y0 and _across(table, row) for table in page.tables
        )
        if groups and not table_between and _continues(groups[-1], row, page, right_edge, line_gap):
            groups[-1].append(row)
        else:
            groups.append([row])
    return groups


def _continues(group: list[Row], row: Row, page: PageRows, right_edge: float, line_gap: float) -> bool:
    """Whether the row carries on the paragraph or list item that the group holds so far."""
    previous = group[-1]
    in_list_item = _starts_list_item(group[0].text)
    same_size = abs(row.size - previous.size) <= _SIZE_STEP
    close_below = row.y0 - previous.y1 <= min(line_gap, _LINE_GAP_CAP * row.size) + _PARAGRAPH_GAP * row.size
    # A first-line indent: the row starts at least one character width further right.
    # Centred lines start wherever their length puts them, so they are not indents,
    # and a list item's later lines may sit under a hanging indent.
    indented = (
        row.x0 - previous.x0 > row.size
        and not (_centred(previous, page) and _centred(row, page))
        and not (in_list_item and row.x0 > group[0].x0)
    )
    # A row set out in columns is a line of its own, like a row of a table.
    in_columns = previous.in_columns or row.in_columns
    return (
        same_size
        and close_below
        and not indented
        and not in_columns
        and not row.starts_block
        and not _starts_new_item(row, previous, in_list_item, right_edge)
    )


def _starts_new_item(row: Row, previous: Row, in_list_item: bool, right_edge: float) -> bool:
    """A bullet always starts an item. Outside an item, a number starts one after a line that
    stops short; after a full line it is just a wrapped sentence, as in "2.5 ล้านบาท". Contract
    clauses often end on a full line, justified, so within an item a number starts the next one
    all the same. After a word that refers to it, as in "ตามข้อ", on a line the number's first
    word would not have fitted on, it is the reference's number, even within an item: a short
    heading such as "ภาคผนวก" is followed by its list."""
    if _BULLET_ITEM.match(row.text):
        return True
    if not _NUMBERED_ITEM.match(row.text):
        return False
    if _REFERENCE_AT_END.search(previous.text) and previous.x1 + _first_word_width(row) > right_edge:
        return False
    stops_short = previous.x1 < right_edge - 2 * row.size
    return in_list_item or stops_short


def _centred(row: Row, page: PageRows) -> bool:
    return abs((row.x0 + row.x1) / 2 - page.width / 2) <= row.size


def _starts_list_item(text: str) -> bool:
    return bool(_NUMBERED_ITEM.match(text) or _BULLET_ITEM.match(text))


def with_marker_spaced(text: str) -> str:
    """The text a row starts with as OCR read it, with the space put back after a list marker read
    joined to the word after it, so that the row is a list item as on a text page."""
    marker = _JOINED_MARKER.match(text)
    return f"{text[: marker.end()]} {text[marker.end() :]}" if marker else text


def _body_size(pages: list[PageRows]) -> float:
    """The font size that most of the text is set in."""
    sizes = Counter[float]()
    for page in pages:
        for row in page.rows:
            sizes[row.size] += len(row.text.strip())
    return sizes.most_common(1)[0][0] if sizes else 0.0


def _block(group: list[Row], levels: dict[float, int]) -> Block:
    """A heading when short and larger than the body; a list item when it starts with a
    number, letter or bullet; a heading again when short and all bold. A row set out in
    columns is a table row, never a list item or bold heading. Bold headings sit one
    level below the size-based ones."""
    text = repair(join_lines([row.text for row in group]))
    short = len(group) <= _HEADING_MAX_ROWS
    if short and group[0].size in levels:
        return Heading(level=min(levels[group[0].size], DEEPEST_HEADING), text=text)
    if _starts_list_item(text) and not group[0].in_columns:
        item = _BULLET_ITEM.sub("", text)
        return ListItem(item, bulleted=bool(_BULLET_ITEM.match(text)), uncertain=_uncertain(item, group))
    if short and all(row.bold and not row.in_columns for row in group):
        return Heading(level=min(max(levels.values(), default=0) + 1, DEEPEST_HEADING), text=text)
    return Paragraph(text, _uncertain(text, group))


def _uncertain(text: str, group: list[Row]) -> tuple[Span, ...]:
    """The uncertain text of a block made of the group's rows. Only text that OCR read can be uncertain."""
    if not any(row.pieces for row in group):
        return ()
    return uncertain_spans(text, [piece for row in group for piece in _pieces(row)])


def _pieces(row: Row) -> tuple[Piece, ...]:
    return row.pieces or (Piece(row.text),)
