"""Check boxes in a page image, for OCR pages: small squares drawn beside a choice, ticked or not.

OCR reads no text in a check box: PaddleOCR boxes one with no text, or takes it into the text
beside it and drops it. So they are found in the image: short straight rules that close off a
small square, the size of a line of text. A box with ink inside is ticked.
"""

from dataclasses import dataclass

import cv2
import numpy as np

Box = tuple[float, float, float, float]

# How outputs show a ticked and an empty check box.
TICKED = "☒"
EMPTY = "☐"

# A pixel darker than this grey level is ink, as for a table's rules (see `grids`).
_INK = 160
# A check box's side is this share of a box height of text, at least and at most. On the 110-page
# sample contract its boxes were 0.67 to 0.75 of a line's box height, and letters and marks that
# made squares too, such as a bold "o", 0.44 to 0.51; in the test fixtures, boxes are 0.67.
_SMALLEST = 0.6
_LARGEST = 1.2
# Its sides are as long as each other, give or take this share.
_SQUARE = 0.25
# Each side is a rule along this share of the box at least: a letter's strokes are curved or
# broken, and a square's are not. The sample contract's boxes had 0.95 at least, and the pattern
# printed behind a certificate, 0.82.
_WHOLE_SIDE = 0.9
# How deep a side may be, as a share of the box: a rule a few pixels thick.
_SIDE_DEPTH = 0.2
# The rules close off an inside at least this share of the box: a square's is most of it, and a
# bold letter's, whose straight strokes can make a square too, is small. On the sample contract,
# boxes closed off 0.37 to 0.51, the least those drawn with a shadow on two sides; bold letters
# 0.29 at most.
_INSIDE = 0.33
# Ink inside is measured clear of the rules by this many pixels, for their blurred edges.
_CLEAR = 2
# A box is ticked when ink covers at least this share of its inside, and empty when it covers at
# most this share. Between the two, as with a speck or a faint mark, it is ticked, unsure. In the
# test fixtures, read at 300 dpi, a tick 1.4 points wide across a 12-point box covers about a
# third of it, and a speck under a tenth.
_TICK_INK = 0.15
_EMPTY_INK = 0.01
# Ink covering more than this share of its inside is a block within a square, as at a QR code's
# corners, which held 0.59 to 0.71 on the sample contract, against 0.35 at most for a tick.
_FULL = 0.5
# A box stands apart from what is beside it: across this share of its side to its left and right,
# over its middle rows, ink covers at most `_BESIDE_INK`. On the sample contract none of its boxes
# had any; a bold "0" in "20" and a logo's "D" had their neighbours' ink there, 0.16 and 0.98.
# Text may come as close as a tenth of a box to it.
_BESIDE = 0.1
_BESIDE_INK = 0.05
# Boxes set side by side, at least this many in a row, each less than its side from the next, are
# boxes a character is written in, a digit to a box, as a tax number is: not boxes to tick. On the
# sample contract, boxes in a row stood two sides apart or more.
_IN_A_ROW = 3
# The rules reach each corner of a box, within this share of its side: a square's meet there, and
# those of a bold "0" or a logo's "D", rounded, stop short.
_CORNER = 0.12


@dataclass(frozen=True)
class CheckBox:
    """A check box found in a page image: its square (x0, y0, x1, y1) in image pixels, whether it
    is ticked, and whether that is sure."""

    box: Box
    ticked: bool
    sure: bool


def check_boxes(pixels: np.ndarray, unit: float) -> list[CheckBox]:
    """The check boxes in an RGB page image, left to right down the page, where `unit` is the height
    of a usual line's box, in pixels."""
    ink = (cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY) < _INK).astype(np.uint8)
    rule = max(round(_SMALLEST * _WHOLE_SIDE * unit), 3)
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, rule), np.uint8))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((rule, 1), np.uint8))
    outlines = cv2.dilate(cv2.bitwise_or(horizontal, vertical), np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(outlines, connectivity=8)
    found: list[CheckBox] = []
    for label in range(1, count):
        x, y, width, height, _ = stats[label]
        if not (_SMALLEST * unit <= min(width, height) and max(width, height) <= _LARGEST * unit):
            continue
        if abs(width - height) > _SQUARE * max(width, height):
            continue
        outline = labels[y : y + height, x : x + width] == label
        drawn = ink[y : y + height, x : x + width]
        if not (_closed(outline) and _square_corners(outline) and _set_apart(ink, (x, y, width, height))):
            continue
        inside = _inside(outline)
        if inside is None:
            continue
        clear = cv2.erode(inside.astype(np.uint8), np.ones((2 * _CLEAR + 1, 2 * _CLEAR + 1), np.uint8)).astype(bool)
        share = float(drawn[clear].mean()) if clear.any() else 0.0
        if share > _FULL:
            continue
        ticked, sure = share > _EMPTY_INK, share <= _EMPTY_INK or share >= _TICK_INK
        found.append(CheckBox((float(x), float(y), float(x + width), float(y + height)), ticked, sure))
    return sorted(_not_in_rows(found), key=lambda found_box: (found_box.box[1], found_box.box[0]))


def _not_in_rows(found: list[CheckBox]) -> list[CheckBox]:
    """The boxes, without those set side by side in a row of `_IN_A_ROW` or more, each less than its
    side from the next on one line, as boxes a character is written in are."""
    rows: list[list[CheckBox]] = []
    for box in sorted(found, key=lambda found_box: (found_box.box[1], found_box.box[0])):
        last = rows[-1][-1].box if rows else None
        side = box.box[2] - box.box[0]
        if last and abs(box.box[1] - last[1]) < side / 2 and 0 <= box.box[0] - last[2] < side:
            rows[-1].append(box)
        else:
            rows.append([box])
    return [box for row in rows if len(row) < _IN_A_ROW for box in row]


def _closed(outline: np.ndarray) -> bool:
    """Whether the rules make a square: each side a rule along most of it."""
    height, width = outline.shape
    depth_y, depth_x = max(round(_SIDE_DEPTH * height), 2), max(round(_SIDE_DEPTH * width), 2)
    sides = (
        outline[:depth_y].any(axis=0),
        outline[height - depth_y :].any(axis=0),
        outline[:, :depth_x].any(axis=1),
        outline[:, width - depth_x :].any(axis=1),
    )
    return all(side.mean() >= _WHOLE_SIDE for side in sides)


def _set_apart(ink: np.ndarray, square: tuple[int, int, int, int]) -> bool:
    """Whether little ink lies just left and right of the square (x, y, width, height), as beside a
    check box, unlike a letter among the letters of a word."""
    x, y, width, height = square
    reach = max(round(_BESIDE * width), 2)
    rows = slice(y + height // 4, y + height - height // 4)
    beside = (ink[rows, max(0, x - reach) : x], ink[rows, x + width : x + width + reach])
    return all(part.size == 0 or part.mean() <= _BESIDE_INK for part in beside)


def _square_corners(outline: np.ndarray) -> bool:
    """Whether the rules reach into each corner of the box, as a square's meet there. A rounded
    corner's curve is no rule, so the straight rules either side stop short of it."""
    height, width = outline.shape
    reach_y, reach_x = max(round(_CORNER * height), 2), max(round(_CORNER * width), 2)
    corners = (
        outline[:reach_y, :reach_x],
        outline[:reach_y, width - reach_x :],
        outline[height - reach_y :, :reach_x],
        outline[height - reach_y :, width - reach_x :],
    )
    return all(corner.any() for corner in corners)


def _inside(outline: np.ndarray) -> np.ndarray | None:
    """The inside the rules close off: the largest space within them, clear of the box's edges. None
    when it is too small for a square's, as within a bold letter."""
    count, spaces, stats, _ = cv2.connectedComponentsWithStats((~outline).astype(np.uint8), connectivity=4)
    height, width = outline.shape
    enclosed = [
        label
        for label in range(1, count)
        if stats[label, cv2.CC_STAT_LEFT] > 0
        and stats[label, cv2.CC_STAT_TOP] > 0
        and stats[label, cv2.CC_STAT_LEFT] + stats[label, cv2.CC_STAT_WIDTH] < width
        and stats[label, cv2.CC_STAT_TOP] + stats[label, cv2.CC_STAT_HEIGHT] < height
    ]
    if not enclosed:
        return None
    largest = max(enclosed, key=lambda label: stats[label, cv2.CC_STAT_AREA])
    if stats[largest, cv2.CC_STAT_AREA] < _INSIDE * height * width:
        return None
    return np.asarray(spaces == largest)
