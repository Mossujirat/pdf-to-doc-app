"""Ruled grids in a page image: the cells that a table's rules make, for tables on OCR pages.

Long horizontal and vertical rules are found in the image, and the cells are the
spaces they close off, with row and column spans where a rule is left out to merge cells.
Rules that make no whole grid can still show a table, whose text cannot be placed in cells.
"""

import math
from dataclasses import dataclass

import cv2
import numpy as np

from pdf_to_doc.layout import EDGE_BAND

Box = tuple[float, float, float, float]

# The image is searched at half its resolution, each pixel the darkest of the four it stands
# for, so that rules a pixel or two wide stay dark: it takes a quarter of the time.
_SHRINK = 2
# A pixel darker than this grey level is ink. Rules on synthetic scans of 150 dpi or more were
# darker. A lighter grey kept the rules of 100-dpi scans too, but took a table's header shaded
# 30% grey for ink, and lost the table.
_INK = 160
# A piece of rule thicker than this many pixels across its length, or this share of a box height
# where that is more, is no rule. Set while grilling, when a dark photo made an empty table: here,
# the dark wall between a photo's lit windows.
_THICKEST_PIXELS = 8
_THICKEST_SHARE = 0.15
# Cell edges closer than this share of a box height lie on one grid line: the edges of two cells
# lie either side of the rule between them, a few pixels apart, and no row is so short.
_SAME_LINE = 0.5
# The page's slant is measured on rules found allowing for it: thickened down the page by this
# many pixels, a rule 3 degrees askew still runs along a row of pixels for twice a box height.
_SLANT_ALLOWANCE = 5


@dataclass(frozen=True)
class GridCell:
    """A cell of a grid: where it lies, between the middles of the rules around it, and the
    row and column it starts in, counted along the grid's lines, with its spans."""

    box: Box
    row: int
    column: int
    rowspan: int = 1
    colspan: int = 1


@dataclass(frozen=True)
class Grid:
    """A table's grid of rules: its cells, and how many rows and columns its lines make."""

    box: Box
    rows: int
    columns: int
    cells: tuple[GridCell, ...]


@dataclass(frozen=True)
class PartRules:
    """Rules that show a table but make no whole grid of it: a boxed row of two or more cells
    with no ruled rows under it, as a table whose header alone is boxed, or rules that close off
    a space that is no rectangle, as when part of a rule is missing. Where they lie, the lines
    their columns' edges lie on, left to right, and how many rows of cells they rule."""

    box: Box
    columns: tuple[float, ...]
    rows: int


@dataclass(frozen=True)
class Rules:
    """The ruled tables on a page: whole grids, and rules that make no whole grid."""

    grids: tuple[Grid, ...] = ()
    parts: tuple[PartRules, ...] = ()


def ruled_tables(pixels: np.ndarray, unit: float) -> Rules:
    """The rules of the tables on a page image of 8-bit RGB samples, in its pixels. `unit`
    is the height of the OCR engine's usual box on it: a rule is at least that long, as text
    holds no stroke so long, and a table's rows are taller.

    Rules of a single row make no grid: a frame around a paragraph is boxed text, and a boxed
    row of two or more cells is part rules, as is a grid whose rules close off a space that is
    no rectangle. Rules wholly in the page's top or bottom edge band make neither: as on text
    pages, they are read as rows, so that a ruled header or footer stays page furniture. Rules
    drawn inside a cell of others are part of that cell, as on text pages.

    The grids lie in the same frame as the boxes of an engine that straightens them by the
    page's slant, as PaddleOCR does: the image is turned back by the slant of its rules, about
    its centre, before they are found.
    """
    grey = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
    length = max(round(unit / _SHRINK), 2)
    slant = _slant(_ink(grey), length)
    if slant is None:
        return Rules()
    ink = _ink(_straightened(grey, slant))
    thickest = max(_THICKEST_PIXELS, _THICKEST_SHARE * unit) / _SHRINK
    horizontal = _thin(cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, length), np.uint8)), cv2.CC_STAT_WIDTH, thickest)
    vertical = _thin(cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((length, 1), np.uint8)), cv2.CC_STAT_HEIGHT, thickest)
    # Rules that meet leave no gap at the joint for a cell to leak through.
    rules = cv2.dilate(cv2.bitwise_or(horizontal, vertical), np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(rules, connectivity=8)
    found: list[Grid | PartRules] = []
    band = EDGE_BAND * len(ink)
    for label in range(1, count):
        x, y, width, height, _ = stats[label]
        if width < length or height < length or y + height <= band or y >= len(ink) - band:
            continue
        cells = _cells(labels[y : y + height, x : x + width] == label)
        boxes: list[Box] = [
            (_SHRINK * (x + x0), _SHRINK * (y + y0), _SHRINK * (x + x1), _SHRINK * (y + y1)) for x0, y0, x1, y1 in cells
        ]
        if ruled := _grid(boxes, _SAME_LINE * unit):
            found.append(ruled)
    found = [ruled for ruled in found if not any(other is not ruled and _inside(ruled.box, other.box) for other in found)]
    return Rules(
        tuple(ruled for ruled in found if isinstance(ruled, Grid)),
        tuple(ruled for ruled in found if isinstance(ruled, PartRules)),
    )


def _inside(box: Box, other: Box) -> bool:
    return other[0] <= box[0] and other[1] <= box[1] and box[2] <= other[2] and box[3] <= other[3]


def _slant(ink: np.ndarray, length: int) -> float | None:
    """The page's slant, in radians clockwise: that of its horizontal rules, the longest counting
    most. None when the page has no rule at least twice `length` long, and so no table."""
    allowing = cv2.dilate(ink, np.ones((_SLANT_ALLOWANCE + 1, 1), np.uint8))
    pieces = cv2.morphologyEx(allowing, cv2.MORPH_OPEN, np.ones((1, 2 * length), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(pieces, connectivity=8)
    slants = []
    for label in range(1, count):
        x, y, width, height, _ = stats[label]
        ys, xs = np.nonzero(labels[y : y + height, x : x + width] == label)
        xs, ys = xs - xs.mean(), ys - ys.mean()
        slants.append((0.5 * math.atan2(2 * (xs * ys).mean(), (xs * xs).mean() - (ys * ys).mean()), int(width)))
    if not slants:
        return None
    slants.sort()
    reach, half = 0, sum(width for _, width in slants) / 2
    for slant, width in slants:
        reach += width
        if reach >= half:
            break
    return slant


def _straightened(grey: np.ndarray, slant: float) -> np.ndarray:
    """The image turned back by the slant about its centre, as such an engine turns its boxes."""
    height, width = grey.shape
    turn = cv2.getRotationMatrix2D((width / 2, height / 2), math.degrees(slant), 1.0)
    return cv2.warpAffine(grey, turn, (width, height), flags=cv2.INTER_LINEAR, borderValue=(255,))


def _thin(pieces: np.ndarray, along: int, thickest: float) -> np.ndarray:
    """The pieces no thicker than `thickest` across their length, on average. `along` says which of
    their sides is their length: `cv2.CC_STAT_WIDTH` for pieces across the page, or its height down it."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(pieces, connectivity=8)
    thin = stats[:, cv2.CC_STAT_AREA] <= thickest * stats[:, along]
    thin[0] = False  # the paper around the pieces
    return np.asarray(thin[labels], dtype=np.uint8)


def _ink(grey: np.ndarray) -> np.ndarray:
    """Which pixels of the image, at half its resolution, are ink: 1 for ink, 0 for paper."""
    darkest = cv2.erode(grey, np.ones((_SHRINK, _SHRINK), np.uint8))[::_SHRINK, ::_SHRINK]
    return cv2.threshold(darkest, _INK - 1, 1, cv2.THRESH_BINARY_INV)[1]


def _cells(rules: np.ndarray) -> list[tuple[int, int, int, int]]:
    """The spaces that the rules close off, each as (x0, y0, x1, y1) in the rules' pixels."""
    count, _, stats, _ = cv2.connectedComponentsWithStats((~rules).astype(np.uint8), connectivity=4)
    height, width = rules.shape
    return [
        (int(x), int(y), int(x + cell_width), int(y + cell_height))
        for x, y, cell_width, cell_height, _ in stats[1:count]
        if x > 0 and y > 0 and x + cell_width < width and y + cell_height < height
    ]


def _grid(cells: list[Box], tolerance: float) -> Grid | PartRules | None:
    """The grid the cells make: the lines their edges lie on, each cell's place and spans along
    them. A space too narrow to make a row or column, as between the two rules of a double
    rule, is no cell. Part rules when a cell covers the same place as another, as when part of a
    rule was not found and the space it would have closed off is no rectangle, or when the cells
    make one row of two or more; None when they make one cell, or none."""
    columns = _lines([edge for cell in cells for edge in (cell[0], cell[2])], tolerance)
    rows = _lines([edge for cell in cells for edge in (cell[1], cell[3])], tolerance)
    box = (columns[0], rows[0], columns[-1], rows[-1])
    placed: list[GridCell] = []
    covered: set[tuple[int, int]] = set()
    for x0, y0, x1, y1 in cells:
        left, right = _nearest(columns, x0), _nearest(columns, x1)
        top, bottom = _nearest(rows, y0), _nearest(rows, y1)
        places = {(row, column) for row in range(top, bottom) for column in range(left, right)}
        if not places:
            continue
        if places & covered:
            return PartRules(box, tuple(columns), len(rows) - 1)
        covered |= places
        placed.append(GridCell((columns[left], rows[top], columns[right], rows[bottom]), top, left, bottom - top, right - left))
    if len(placed) < 2:
        return None
    if len(rows) == 2:
        return PartRules(box, tuple(columns), 1)
    return Grid(box, len(rows) - 1, len(columns) - 1, tuple(placed))


def _lines(edges: list[float], tolerance: float) -> list[float]:
    """Where the grid's lines lie: edges closer than the tolerance lie on the same line, which is
    half way between them, as the edges of two cells lie on either side of the rule between them."""
    groups: list[list[float]] = []
    for edge in sorted(edges):
        if groups and edge - groups[-1][-1] <= tolerance:
            groups[-1].append(edge)
        else:
            groups.append([edge])
    return [(group[0] + group[-1]) / 2 for group in groups]


def _nearest(lines: list[float], edge: float) -> int:
    return min(range(len(lines)), key=lambda index: abs(lines[index] - edge))
