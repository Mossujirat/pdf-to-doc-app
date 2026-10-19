"""Page layout: turns the printed rows of text pages into document structure."""

import re
from collections import Counter
from dataclasses import dataclass, replace

from pdf_to_doc.model import Block, Heading, ListItem, Paragraph, Table, TableCell
from pdf_to_doc.thai import DIGITS, THAI_CONSONANT, THAI_LETTER, join_lines, repair

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
_BULLET_ITEM = re.compile(r"^\s*[•●○◦▪■□‣⁃∙\-–*]\s+")
# Font sizes closer than this (points) count as the same size within a paragraph.
_SIZE_STEP = 0.5
# Text this much larger than the body can be a heading; heading sizes closer than
# the step (points) share a level; a heading is at most this many rows long.
_HEADING_SCALE = 1.06
_HEADING_SIZE_STEP = 0.6
_HEADING_MAX_ROWS = 2
_DEEPEST_HEADING = 6
# Lines whose baselines differ by less than this share of the font size are on one
# row; a gap wider than this many character widths sets the row out in columns.
_BASELINE_TOLERANCE = 0.3
_COLUMN_GAP = 2.0
# A gap between rows this share of the font size wider than the document's usual
# line spacing ends a paragraph. The usual spacing counts for at most the cap: in a
# short document most gaps may be between paragraphs. (Double-spaced text, rare in
# office documents, therefore splits into one paragraph per line.)
_PARAGRAPH_GAP = 0.4
_LINE_GAP_CAP = 0.75


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


@dataclass(frozen=True)
class RawCell:
    """A table cell as printed: its lines of text, before they are joined and repaired."""

    lines: tuple[str, ...]
    rowspan: int = 1
    colspan: int = 1


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
class PageRows:
    rows: tuple[Row, ...]  # text outside tables
    width: float
    height: float
    tables: tuple[PlacedTable, ...] = ()


def page_blocks(pages: list[PageRows]) -> list[tuple[Block, ...]]:
    """The blocks of each page: page furniture removed, rows grouped into headings,
    list items and paragraphs."""
    pages = remove_page_furniture([replace(page, rows=_join_on_baselines(page.rows)) for page in pages])
    line_gap = _usual_line_gap(pages)
    groups_by_page = [_group_rows(page, line_gap) for page in pages]
    levels = _heading_levels([group for groups in groups_by_page for group in groups], _body_size(pages))
    return [_in_reading_order(groups, page.tables, levels) for groups, page in zip(groups_by_page, pages)]


def _in_reading_order(
    groups: list[list[Row]], tables: tuple[PlacedTable, ...], levels: dict[float, int]
) -> tuple[Block, ...]:
    """The page's blocks, with each table placed before the first text that starts below it."""
    pending = sorted(tables, key=lambda placed: placed.top)
    blocks: list[Block] = []
    for group in groups:
        while pending and pending[0].top <= group[0].y0:
            blocks.append(_table(pending.pop(0)))
        blocks.append(_block(group, levels))
    blocks.extend(_table(placed) for placed in pending)
    return tuple(blocks)


def _table(placed: PlacedTable) -> Table:
    """Join each cell's printed lines with the Thai line rules, and repair them."""
    return Table(
        rows=tuple(
            tuple(TableCell(repair(join_lines(list(cell.lines))), cell.rowspan, cell.colspan) for cell in row)
            for row in placed.rows
        )
    )


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
                in_columns=previous.in_columns or row.x0 - previous.x1 > _COLUMN_GAP * row.size,
            )
        else:
            joined.append(row)
    return tuple(joined)


def remove_page_furniture(pages: list[PageRows]) -> list[PageRows]:
    """Drop page furniture: rows at the same edge (top or bottom) that repeat on two or more pages.

    Page numbers must follow the pages: a printed number repeats only if it
    stays the same distance from the PDF's own page number. A row near the edge
    of only one page is kept, unless the whole row is a page counter.
    """
    keys = [[_furniture_key(row, page, number) for row in page.rows] for number, page in enumerate(pages, 1)]
    pages_per_key = Counter(key for page_keys in keys for key in set(page_keys) if key)
    return [
        replace(
            page,
            rows=tuple(
                row
                for row, key in zip(page.rows, page_keys)
                if not (key and (pages_per_key[key] >= 2 or _is_counter_only(row)))
            ),
        )
        for page, page_keys in zip(pages, keys)
    ]


def _furniture_key(row: Row, page: PageRows, number: int) -> str | None:
    """What the row would look like if it were page furniture, or None if it cannot be.

    Furniture sits near the top or bottom edge and says something: a row of
    dashes near the edge is more likely a table cell. Page counters are replaced
    by their distance from the PDF page number, so "หน้าที่ 2/7" on page 2 and
    "หน้าที่ 3/7" on page 3 match.
    """
    band = EDGE_BAND * page.height
    edge = "top" if row.y0 <= band else "bottom" if row.y1 >= page.height - band else None
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
    return same_size and close_below and not indented and not in_columns and not _starts_new_item(
        row, previous, in_list_item, right_edge
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
        return Heading(level=min(levels[group[0].size], _DEEPEST_HEADING), text=text)
    if _starts_list_item(text) and not group[0].in_columns:
        return ListItem(_BULLET_ITEM.sub("", text))
    if short and all(row.bold and not row.in_columns for row in group):
        return Heading(level=min(max(levels.values(), default=0) + 1, _DEEPEST_HEADING), text=text)
    return Paragraph(text)
