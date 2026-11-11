"""Columns: where text is set in columns, and the order a reader takes it in. Shared by OCR pages,
which find them among the engine's boxes, and text pages, among the text layer's rows (see
`in_reading_order`)."""

import math
import re
from bisect import bisect
from dataclasses import dataclass, replace
from itertools import combinations
from statistics import median
from typing import Protocol

from pdf_to_doc.layout import SIGNATURE_LINE, PageRows, Row
from pdf_to_doc.thai import DIGITS

Box = tuple[float, float, float, float]

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
# Boxes whose centres are closer than this share of a box height sit on one printed line.
_SAME_LINE = 0.5
# A side panel beside body text is a column too, though its lines are as short as labels':
# narrower than the body, and set in smaller type, its boxes at most this share as tall at the
# median. The 110-page sample contract's panel was 0.53 as tall as its body; the test fixtures'
# 9 points beside 12, 0.75.
_SMALLER_TYPE = 0.85
# The body beside a panel runs to at least this many lines: two, on a form's heading, did not.
_BODY_LINES = 3
# And its lines and the body's mostly keep apart: fewer than this share of the panel's lines
# share a baseline with a body line, and not every body line shares one with a panel line. Labels
# and values share their rows' baselines, however small the values; on synthetic scans, 41 to 47%
# of a smaller panel's lines did (ticket 18). On the 110-page sample contract, columns of smaller
# type without the rest were tables set apart without rules.
_ON_SHARED_LINES = 0.75
# Lines share a baseline when their centres are closer than this share of a box height: lines of
# two sizes on one baseline are, as are the lines that `_SAME_LINE` groups, more loosely, into one
# printed line; lines a line of the smaller type apart are not.
_SAME_BASELINE = 0.25
# A panel in the body's own type, such as blocks of bank details under their headings beside the
# signatories, keeps rows of its own (ticket 39): fewer than this share of each side's lines share
# a baseline with the other side. On the five-page sample agreement, 25 and 29% did; on the
# 110-page sample contract, tables set apart without rules, in one type, had 44% or more.
_OWN_ROWS = 0.35
# And its blocks start on rows of their own, where a table's rows start together on both sides: on
# the five-page sample agreement, the nearest block starts on the two sides lay 0.44 box heights
# apart; on the 110-page sample contract's tables, 0.1 at most (see `_SAME_BASELINE`). A block
# starts at a side's first line, and at a line this many of the side's box heights or more below
# the one before. On the agreement, lines followed one another 0.85 to 1.09 box heights apart, and
# blocks 1.70 and 2.25. Measured in box heights rather than the side's own line pitch, so that a
# side of one-line blocks still has each of them start one.
_BLOCK_GAP = 1.5
# Signature blocks side by side are found by their rows to sign on (see `_signature_blocks`): a
# signing word, or a box that opens with "By:", as English signature blocks name their signer.
# "By:" is not a row to sign on for placeholders: "Photo by" beside a picture is no signature.
_SIGNED_BY = re.compile(r"\s*by\s*:", re.IGNORECASE)


class Placed(Protocol):
    """Text, and the box around it (x0, y0, x1, y1) on the page or image."""

    @property
    def text(self) -> str: ...

    @property
    def box(self) -> Box: ...


def reading_parts[P: Placed](boxes: tuple[P, ...], unit: float) -> list[tuple[P, ...]]:
    """The boxes in the parts a reader reads one after the other: down the page, and where
    it is set in columns of body text, each column to its end before the one to its right,
    each column read the same way in turn. Signature blocks side by side are read one block
    after the other, and a side panel beside body text after it. Text without columns is one
    part. Distances are measured in `unit`, the height of a usual line's box."""
    found: list[tuple[P, ...]] = []
    run: list[P] = []  # bands not set in columns, read as one part
    for region in _regions(boxes, unit):
        columns = _text_columns(region, unit)
        if not columns and (signing := _signature_blocks(region)):
            above, blocks, after = signing
            found += [part for part in (tuple(run + above), *blocks) if part]
            run = after
            continue
        columns = columns or _panel_columns(region, unit)
        if not columns:
            run += region
            continue
        if run:
            found.append(tuple(run))
            run = []
        found += [part for column in columns for part in reading_parts(column, unit)]
    if run:
        found.append(tuple(run))
    return found if len(found) > 1 else [boxes]


def in_reading_order(page: PageRows) -> PageRows:
    """A text page's rows in reading order.

    Most PDF writers draw text in reading order, one column after the other, and the
    rows keep that order. Some draw columns line by line across the page instead; where
    they do, the rows are taken column by column, as on an OCR page (see
    `reading_parts`), measured in the page's median row height. Each column then
    starts a paragraph or list item, as on an OCR page.
    """
    drawn = tuple(_Drawn(row.text, (row.x0, row.y0, row.x1, row.y1), order) for order, row in enumerate(page.rows))
    if len(drawn) < 2:
        return page
    parts = reading_parts(drawn, median(_height(box) for box in drawn))
    if not _drawn_across(parts):
        return page
    rows: list[Row] = []
    for part in parts:
        in_part = [page.rows[box.order] for box in sorted(part, key=lambda box: box.order)]
        rows += [replace(in_part[0], starts_block=True), *in_part[1:]]
    return replace(page, rows=tuple(rows))


@dataclass(frozen=True)
class _Drawn:
    """A row as a box for the column finder, and its place in the order the PDF draws the rows."""

    text: str
    box: Box
    order: int


def _drawn_across(parts: list[tuple[_Drawn, ...]]) -> bool:
    """Whether the PDF draws parts set side by side line by line across them: a row of one
    part drawn after a row of a part to its right, which a reader reads after it."""
    for first, then in combinations(parts, 2):
        side_by_side = _top(first) < _bottom(then) and _top(then) < _bottom(first)
        if side_by_side and max(box.order for box in first) > min(box.order for box in then):
            return True
    return False


def _regions[P: Placed](boxes: tuple[P, ...], unit: float) -> list[tuple[P, ...]]:
    """The boxes cut into bands down the page, each band taken with the columns above it when it is more of them."""
    regions: list[tuple[P, ...]] = []
    for band in _cut(boxes, 1, _BAND_GAP * unit):
        if regions and _more_of(regions[-1], band, unit):
            regions[-1] += band
        else:
            regions.append(band)
    return regions


def _more_of[P: Placed](above: tuple[P, ...], band: tuple[P, ...], unit: float) -> bool:
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


def _under_the_longest[P: Placed](columns: list[tuple[P, ...]], band: tuple[P, ...], unit: float) -> bool:
    """Whether the band lies under the column that reaches further down than the others, clear of their sides."""
    bottoms = [_bottom(column) for column in columns]
    longest = bottoms.index(max(bottoms))
    if any(bottoms[longest] - bottom < _BAND_GAP * unit for number, bottom in enumerate(bottoms) if number != longest):
        return False
    left = _right(columns[longest - 1]) if longest > 0 else float("-inf")
    right = _left(columns[longest + 1]) if longest + 1 < len(columns) else float("inf")
    return left < _left(band) and _right(band) < right


def _text_columns[P: Placed](boxes: tuple[P, ...], unit: float) -> list[tuple[P, ...]]:
    """The boxes' columns, left to right, when they are set in columns of body text; otherwise none."""
    columns = _lined_up_columns(boxes, unit)
    return columns if all(map(_body_text, columns)) else []


def _lined_up_columns[P: Placed](boxes: tuple[P, ...], unit: float) -> list[tuple[P, ...]]:
    """The boxes' columns, left to right, when there are two or more and each is lined up; otherwise none."""
    columns = _columns(boxes, unit)
    return columns if len(columns) > 1 and all(_lined_up(column, unit) for column in columns) else []


def _signature_blocks[P: Placed](band: tuple[P, ...]) -> tuple[list[P], list[tuple[P, ...]], list[P]] | None:
    """Signature blocks side by side in the band, what lies above them, and what follows them; None
    when it holds none.

    A row of blocks starts at each printed line that opens with a row to sign on and holds another,
    each in a box of its own, and runs to the next. A line that opens otherwise, as a table's
    header row with two signing columns does, starts none. Its blocks are read left to right, a
    row of blocks after the one above, so that each signer stays beside the witness set beside them.
    Each block takes the boxes whose centres lie from its signing word to the next one's. Stamps and
    signatures that OCR reads as text overlap the gaps between blocks, and rows of blocks follow one
    another without a gap, so the gaps between them are no clear gutters. Body text in one box that
    runs across a block's start, below the blocks, ends them: it and what follows it are no block's.
    """
    lines = printed_lines(band)
    rows = [signs for line in lines if len(signs := _signing_boxes(line)) >= 2 and signs[0] is line[0]]
    if not rows:
        return None
    tops = [min(box.box[1] for box in signs) for signs in rows]
    starts = [[sign.box[0] for sign in signs[1:]] for signs in rows]
    end = min(
        (
            box.box[1]
            for box in band
            if _centre(box) > tops[0] and _body_text((box,)) and _across(box, starts[bisect(tops, _centre(box)) - 1])
        ),
        default=math.inf,
    )
    above: list[P] = []
    after: list[P] = []
    blocks: list[list[list[P]]] = [[[] for _ in signs] for signs in rows]
    for box in band:
        row = bisect(tops, _centre(box)) - 1
        if row < 0:
            above.append(box)
        elif _centre(box) >= end:
            after.append(box)
        else:
            blocks[row][bisect(starts[row], (box.box[0] + box.box[2]) / 2)].append(box)
    return above, [tuple(block) for row_blocks in blocks for block in row_blocks if block], after


def _across(box: Placed, starts: list[float]) -> bool:
    """Whether the box runs across where one of the blocks starts, by a box height or more each way.
    A block's own lines may start a little left of its signing word: the five-page sample's by 3
    pixels."""
    reach = _height(box)
    return any(box.box[0] + reach < start < box.box[2] - reach for start in starts)


def _signing_boxes[P: Placed](line: list[P]) -> list[P]:
    """The boxes of a printed line that hold a row to sign on, left to right: a signing word, or
    "By:" before the signer's name, as English agreements set it."""
    return [box for box in line if SIGNATURE_LINE.search(box.text) or _SIGNED_BY.match(box.text)]


def _panel_columns[P: Placed](boxes: tuple[P, ...], unit: float) -> list[tuple[P, ...]]:
    """The boxes' columns, left to right, when they are body text and a side panel beside it;
    otherwise none. Unlike columns of body text, they never take in the band below them (see
    `_more_of`)."""
    columns = _lined_up_columns(boxes, unit)
    return columns if columns and _body_and_side_panel(columns) else []


def _body_and_side_panel[P: Placed](columns: list[tuple[P, ...]]) -> bool:
    """Whether the columns are body text and a side panel beside it: two columns, one of body text of
    a few lines at least, the other narrower, their lines mostly apart. A panel in smaller type
    keeps off the body's baselines (see `_ON_SHARED_LINES`); one in the body's own type keeps rows
    of its own, and its blocks start on rows of their own (see `_OWN_ROWS`). Tables set apart
    without rules have more columns, or none of body text, or rows that start together."""
    if len(columns) != 2:
        return False
    for panel, body in (columns, columns[::-1]):
        narrower = _right(panel) - _left(panel) < _right(body) - _left(body)
        if narrower and len(printed_lines(body)) >= _BODY_LINES and _body_text(body):
            panel_lines, body_lines = printed_lines(panel), printed_lines(body)
            if median(map(_height, panel)) <= _SMALLER_TYPE * median(map(_height, body)):
                return _on_shared_baselines(panel_lines, body) < _ON_SHARED_LINES and (
                    _on_shared_baselines(body_lines, panel) < 1
                )
            return (
                _on_shared_baselines(panel_lines, body) < _OWN_ROWS
                and _on_shared_baselines(body_lines, panel) < _OWN_ROWS
                and not any(
                    _on_one_baseline(start, other) for start in _block_starts(panel_lines) for other in _block_starts(body_lines)
                )
            )
    return False


def _block_starts[P: Placed](lines: list[list[P]]) -> list[P]:
    """The first box of each block of the lines: the first line, and each line at least `_BLOCK_GAP`
    of their box heights below the one before."""
    centres = [_centre(line[0]) for line in lines]
    gap = _BLOCK_GAP * median(_height(box) for line in lines for box in line)
    return [lines[0][0]] + [line[0] for line, before, after in zip(lines[1:], centres, centres[1:]) if after - before >= gap]


def _on_shared_baselines[P: Placed](lines: list[list[P]], beside: tuple[P, ...]) -> float:
    """The share of the lines that share a baseline with a box beside them."""
    return sum(any(_on_one_baseline(line[0], box) for box in beside) for line in lines) / len(lines)


def _on_one_baseline(box: Placed, other: Placed) -> bool:
    return abs(_centre(box) - _centre(other)) <= _SAME_BASELINE * _height(box)


def _gutters[P: Placed](columns: list[tuple[P, ...]]) -> list[tuple[float, float]]:
    """Where the gutters between the columns run across the page, left to right."""
    return [(_right(before), _left(after)) for before, after in zip(columns, columns[1:])]


def _columns[P: Placed](band: tuple[P, ...], unit: float) -> list[tuple[P, ...]]:
    """The band cut at its gutters, left to right; a piece of too few lines is joined to
    the piece across the narrower gutter beside it."""
    pieces = _cut(band, 0, _GUTTER * unit)
    while len(pieces) > 1:
        short = [number for number, piece in enumerate(pieces) if len(printed_lines(piece)) < _COLUMN_LINES]
        if not short:
            break
        number = short[0]
        after = number + 1 < len(pieces) and (
            number == 0 or _gutter(pieces[number], pieces[number + 1]) < _gutter(pieces[number - 1], pieces[number])
        )
        first = number if after else number - 1
        pieces[first : first + 2] = [pieces[first] + pieces[first + 1]]
    return pieces


def _gutter[P: Placed](before: tuple[P, ...], after: tuple[P, ...]) -> float:
    return _left(after) - _right(before)


def _left[P: Placed](boxes: tuple[P, ...]) -> float:
    return min(box.box[0] for box in boxes)


def _right[P: Placed](boxes: tuple[P, ...]) -> float:
    return max(box.box[2] for box in boxes)


def _top[P: Placed](boxes: tuple[P, ...]) -> float:
    return min(box.box[1] for box in boxes)


def _bottom[P: Placed](boxes: tuple[P, ...]) -> float:
    return max(box.box[3] for box in boxes)


def _body_text[P: Placed](column: tuple[P, ...]) -> bool:
    """Whether the column reads as body text: long lines, mostly not digits, unlike a column of amounts."""
    lines = ["".join("".join(box.text for box in line).split()) for line in printed_lines(column)]
    digits = sum(len(run) for line in lines for run in re.findall(DIGITS, line))
    return median(map(len, lines)) >= _BODY_LINE and 2 * digits < sum(map(len, lines))


def _lined_up[P: Placed](column: tuple[P, ...], unit: float) -> bool:
    """Whether most of the column's lines start at one place, or centre on one when set
    centred, as a column's lines do; not wherever holes in the lines happen to end."""
    lines = printed_lines(column)
    starts = [line[0].box[0] for line in lines]
    centres = [(line[0].box[0] + line[-1].box[2]) / 2 for line in lines]
    return any(
        2 * sum(abs(place - median(places)) < _LINED_UP * unit for place in places) > len(places)
        for places in (starts, centres)
    )


def _cut[P: Placed](boxes: tuple[P, ...], axis: int, gap: float) -> list[tuple[P, ...]]:
    """The boxes cut where they leave a stretch at least `gap` wide free of boxes: across
    the page (axis 0), into columns, or down it (axis 1), into bands."""
    groups: list[list[P]] = []
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


def printed_lines[P: Placed](boxes: tuple[P, ...]) -> list[list[P]]:
    """Boxes grouped into printed lines, top to bottom, each line left to right."""
    lines: list[list[P]] = []
    for box in sorted((box for box in boxes if box.text.strip()), key=_centre):
        if lines and abs(_centre(box) - _centre(lines[-1][0])) <= _SAME_LINE * _height(lines[-1][0]):
            lines[-1].append(box)
        else:
            lines.append([box])
    return [sorted(line, key=lambda box: box.box[0]) for line in lines]


def _centre(box: Placed) -> float:
    return (box.box[1] + box.box[3]) / 2


def _height(box: Placed) -> float:
    return box.box[3] - box.box[1]
