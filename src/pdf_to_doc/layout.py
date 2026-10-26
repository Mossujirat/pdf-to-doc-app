"""Page layout: turns the printed rows of each page, read from its text layer or with OCR, into document structure."""

import re
from collections import Counter
from dataclasses import dataclass, replace

from pdf_to_doc.model import (
    DEEPEST_HEADING,
    Block,
    Heading,
    KeptImage,
    ListItem,
    PageKind,
    Paragraph,
    Placeholder,
    Span,
    Table,
    TableCell,
)
from pdf_to_doc.thai import DIGITS, MARK, THAI_CONSONANT, THAI_LETTER, join_lines, repair
from pdf_to_doc.uncertain import Piece, uncertain_spans
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
# A numbered list item starts with "1.", "1)", "(1)", "1.2" or "1.2.", or with a Thai
# letter in brackets, "(ก)" or "ก)", followed by a space. "ก." is left out: it is
# also how Thai abbreviates ตำบล, อำเภอ and the like.
_NUMBERED_ITEM = re.compile(rf"^\s*(?:\(?{_NUMBER}(?:\.{_NUMBER})*[.)]|{_NUMBER}(?:\.{_NUMBER})+|\(?{THAI_CONSONANT}\))\s")
# Symbol and Wingdings fonts, which Word draws bullets with, report their glyphs
# as Private Use Area characters in this range.
SYMBOL_FONT_CHARACTERS = f"{chr(0xF000)}-{chr(0xF0FF)}"
_BULLET_ITEM = re.compile(r"^\s*[•●○◦▪■□‣⁃∙\-–*" + SYMBOL_FONT_CHARACTERS + r"]\s+")
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
# A row to sign on: "ลงชื่อ ........", "ลายมือชื่อ", or the English word "Signature".
_SIGNATURE_LINE = re.compile(r"ลงชื่อ|ลายมือชื่อ|\bsignature\b", re.IGNORECASE)
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
# are less than this share of the font size apart, about a third of a line.
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

    top: float
    bottom: float
    rows: tuple[tuple[RawCell, ...], ...]


@dataclass(frozen=True)
class PlacedImage:
    """An image drawn on a text page, and where it sits."""

    x0: float
    top: float
    x1: float
    bottom: float
    stamp_like: bool = False  # a ring in colour, as a stamp leaves
    kept_image: KeptImage | None = None  # the picture itself, with images kept


@dataclass(frozen=True)
class PageRows:
    rows: tuple[Row, ...]  # text outside tables
    width: float
    height: float
    tables: tuple[PlacedTable, ...] = ()
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
    """The page's blocks, with each table and image placed before the first text that starts below it."""
    placed: list[tuple[float, Block]] = [(table.top, _table(table)) for table in page.tables]
    placed += [(image.top, placeholder) for image in page.images if (placeholder := _placeholder(image, page))]
    pending = sorted(placed, key=lambda item: item[0])
    blocks: list[Block] = []
    for group in groups:
        while pending and pending[0][0] <= group[0].y0:
            blocks.append(pending.pop(0)[1])
        blocks.append(_block(group, levels))
    blocks.extend(block for _, block in pending)
    return tuple(blocks)


def _behind_text(image: PlacedImage, rows: tuple[Row, ...]) -> bool:
    """Whether enough rows are printed over the image for it to be the page behind them."""
    over = [
        row
        for row in rows
        if image.x0 <= (row.x0 + row.x1) / 2 <= image.x1 and image.top <= (row.y0 + row.y1) / 2 <= image.bottom
    ]
    return len(over) >= _BACKGROUND_ROWS


def _placeholder(image: PlacedImage, page: PageRows) -> Placeholder | None:
    """What stands in for the image, or None when it is the page behind the text. With images
    kept, it carries the picture.

    A stamp when the image is a ring in colour, wherever it is pressed, even over
    a whole signature block. A signature when it is small and sits on a row to sign on,
    or just above or below one. When it is unclear what an image shows, it is only an
    image: the converter does not guess.
    """
    if image.stamp_like:
        return Placeholder("stamp", image.kept_image)
    if _behind_text(image, page.rows):
        return None
    small = (
        image.x1 - image.x0 <= _SIGNATURE_MAX_WIDTH * page.width
        and image.bottom - image.top <= _SIGNATURE_MAX_HEIGHT * page.height
    )
    if small and any(_SIGNATURE_LINE.search(row.text) and _next_to(image, row) for row in page.rows):
        return Placeholder("signature", image.kept_image)
    return Placeholder("image", image.kept_image)


def _next_to(image: PlacedImage, row: Row) -> bool:
    """Whether the image and the row overlap across the page, and lie less than a row's height apart down it."""
    across = image.x0 < row.x1 and row.x0 < image.x1
    down = row.y0 - image.bottom <= row.size and image.top - row.y1 <= row.size
    return across and down


def _table(placed: PlacedTable) -> Table:
    """The table as a reader takes it: items stacked in a row's cells that line up across them
    are sub-rows, and each cell's printed lines are joined into its items."""
    return Table(
        rows=tuple(
            tuple(TableCell(_cell_text(cell), cell.rowspan, cell.colspan) for cell in row)
            for row in _with_sub_rows(placed.rows)
        )
    )


def _with_sub_rows(rows: tuple[tuple[RawCell, ...], ...]) -> list[list[RawCell]]:
    """The rows, each row whose cells stack items that line up across them split into a sub-row
    per item. The row's other cells, and the cells above that reach into it, span its sub-rows."""
    splits = [_sub_rows(row) for row in rows]
    counts = [count for count, _ in splits]
    split_rows: list[list[RawCell]] = []
    for number, (row, (count, stacked)) in enumerate(zip(rows, splits)):
        parts: list[list[RawCell]] = [[] for _ in range(count)]
        for index, cell in enumerate(row):
            if index in stacked:
                for part, line in zip(parts, cell.lines):
                    part.append(replace(cell, lines=(line,)))
            else:
                parts[0].append(replace(cell, rowspan=sum(counts[number : number + cell.rowspan])))
        split_rows += parts
    return split_rows


def _sub_rows(row: tuple[RawCell, ...]) -> tuple[int, set[int]]:
    """How many sub-rows the row splits into, and which of its cells hold them: two or more cells
    that each stack as many items, more than one, on lines that line up across them. A cell whose
    lines wrap holds a sentence, not items. (1, no cells) when the row does not split."""
    stacked = [
        index
        for index, cell in enumerate(row)
        if cell.rowspan == 1
        and len(cell.lines) > 1
        and not any(_wraps(line, following, cell) for line, following in zip(cell.lines, cell.lines[1:]))
    ]
    for index in stacked:
        lined_up = {other for other in stacked if _lines_up(row[index], row[other])}
        if len(lined_up) > 1:
            return len(row[index].lines), lined_up
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
    """Whether the line wraps into the next, as Word wraps a line: the next line's first word
    would not have fitted in the room left after it. The room ends where the cell's text would,
    as far in from its right edge as the text starts from its left."""
    if cell.box is None:
        return True
    left, _, right, _ = cell.box
    room = right - (min(each.x0 for each in cell.lines) - left) - line.x1
    return room < _first_word_width(following)


def _first_word_width(line: CellLine) -> float:
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

    Page numbers must follow the pages: a printed number repeats only if it
    stays the same distance from the PDF's own page number. A row near the edge
    of only one page is kept, unless the whole row is a page counter. So is an
    image near the edge of only one page.
    """
    keys = [[_furniture_key(row, page, number) for row in page.rows] for number, page in enumerate(pages, 1)]
    pages_per_key = Counter(key for page_keys in keys for key in set(page_keys) if key)
    images = [[(image, _edge(image.top, image.bottom, page)) for image in page.images] for page in pages]
    return [
        replace(
            page,
            rows=tuple(
                row
                for row, key in zip(page.rows, page_keys)
                if not (key and (pages_per_key[key] >= 2 or _is_counter_only(row)))
            ),
            images=tuple(
                image
                for image, edge in page_images
                if not (edge and any(_repeats(image, edge, others) for others in images if others is not page_images))
            ),
        )
        for page, page_keys, page_images in zip(pages, keys, images)
    ]


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
    if counter := _BARE_PAGE_NUMBER.fullmatch(text) or _PAGE_COUNTER.search(text):
        offset = int(counter["page"]) - number
        return f"{edge}|{text[: counter.start()].strip()}|page{offset:+d}"
    return f"{edge}|{text}"


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
        # A paragraph never runs across a table that starts between two of its rows.
        table_between = bool(groups) and any(
            groups[-1][-1].y0 < table.top <= row.y0 for table in page.tables
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
    """A bullet always starts an item. A number starts one after another item or after a
    line that stops short; after a full line it is just a wrapped sentence, as in "2.5 ล้านบาท"."""
    if _BULLET_ITEM.match(row.text):
        return True
    if not _NUMBERED_ITEM.match(row.text):
        return False
    stops_short = previous.x1 < right_edge - 2 * row.size
    return in_list_item or stops_short


def _centred(row: Row, page: PageRows) -> bool:
    return abs((row.x0 + row.x1) / 2 - page.width / 2) <= row.size


def _starts_list_item(text: str) -> bool:
    return bool(_NUMBERED_ITEM.match(text) or _BULLET_ITEM.match(text))


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
