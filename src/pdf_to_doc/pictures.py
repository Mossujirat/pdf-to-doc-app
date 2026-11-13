"""Pictures: the picture finder interface, which finds signatures, stamps and pictures inside a
scan's image, and what tells a picture apart, in a PDF's image or in part of a scan: whether it is
big enough to be one, and whether it is a stamp."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

import cv2
import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:  # `ocr` reads scans with a finder, and so imports this module
    from pdf_to_doc.ocr import PageImage

# What a finder took a region for, in a layout model's own labels: "seal" is its word for a stamp.
# Its other labels, such as text or a table, are no picture.
PictureLabel = Literal["image", "chart", "seal"]
# What a picture was found as: one of those, or coloured ink beside a row to sign on, where the
# finder found nothing (see `coloured_ink`).
FoundAs = PictureLabel | Literal["ink"]

# An image whose shorter side is under this (points) is a rule, a bullet or an ornament.
_SMALLEST_PICTURE = 8.0
# A pixel is ink when it is darker than this share of white, or more coloured than this saturation.
_PAPER = 0.85
_COLOURED = 0.25
# A stamp is a ring in colour: its box is nearly square, its ink well coloured, the
# corners outside the round hold little ink next to the inside, and the ink is densest
# in the round's outer band, where a stamp's border runs. On the sample contracts, a
# square signature's corners held 0.63 of its inside's ink, and a logo's 0.68. A pie
# chart or a photo cropped round has no border denser than its inside.
_SQUARE = (0.75, 1.33)
_STAMP_SATURATION = 0.4
_STAMP_CORNERS = 0.25
_STAMP_BORDER = 0.8  # share of the radius where the outer band starts
_STAMP_BORDER_INK = 1.5  # how many times denser the band's ink is than the ink inside it
# Coloured ink in a scan, as a pen or a stamp leaves it. Every scan of the sample contracts is in
# colour, and their signatures mostly in blue pen (ticket 38, 2026-11-12). It is looked for at this
# resolution, at which it was measured there.
_INK_DPI = 150
# A pixel is clearly coloured, not black, grey or paper, when its brightest channel is this share of
# white above its darkest: scanned black print, its edges tinted by the JPEG, stays well under it.
_INK_CHROMA = 0.2
# Strokes this close, in points, are one mark, as a pen lifts and lands again within a signature.
_INK_JOIN = 3.0
# A mark holds at least this many coloured pixels at `_INK_DPI`; fewer is a speck.
_INK_PIXELS = 1500
# A highlight is no ink: a mark whose box is this share or more bright colour, a channel above
# `_BRIGHT` and saturated above `_BRIGHT_SATURATION`, is the paper marked with a highlighter, and the
# print under it passed for ink. On the samples this dropped what the user checked was right to drop.
_BRIGHT = 0.85
_BRIGHT_SATURATION = 0.15
_HIGHLIGHT = 0.3


@dataclass(frozen=True)
class FoundPicture:
    """A picture a finder found: its box (x0, y0, x1, y1) in the image's pixels, and what it took it for."""

    box: tuple[float, float, float, float]
    label: FoundAs


class PictureFinder(Protocol):
    """Finds the pictures inside a page image: signatures, stamps, logos, photos, charts."""

    def find(self, image: PageImage) -> tuple[FoundPicture, ...]: ...


class NoPictures:
    """A finder that finds none: a scan's pictures are read as OCR reads them."""

    def find(self, image: PageImage) -> tuple[FoundPicture, ...]:
        return ()


def a_picture(width: float, height: float) -> bool:
    """Whether an image this size on the page, in points, is a picture, not a rule, a bullet or an ornament."""
    return min(width, height) >= _SMALLEST_PICTURE


def coloured_ink(rgb: npt.NDArray[np.uint8], dpi: float) -> list[tuple[float, float, float, float]]:
    """The marks of coloured ink in an image, its 8-bit RGB samples `dpi` to the inch: the box
    (x0, y0, x1, y1) of each, in the image's pixels. A mark is coloured pixels close enough to be
    strokes of one, and many enough not to be a speck; highlights are not ink (see `_HIGHLIGHT`)."""
    shrink = min(1.0, _INK_DPI / dpi)
    small = cv2.resize(rgb, None, fx=shrink, fy=shrink, interpolation=cv2.INTER_AREA) if shrink < 1 else rgb
    colours = small.astype(np.float32) / 255
    brightest, darkest = colours.max(axis=2), colours.min(axis=2)
    ink = brightest - darkest > _INK_CHROMA
    bright = (brightest > _BRIGHT) & (brightest - darkest > _BRIGHT_SATURATION * brightest)
    reach = max(1, round(_INK_JOIN * dpi * shrink / 72))
    joined = cv2.dilate(ink.astype(np.uint8), np.ones((2 * reach + 1, 2 * reach + 1), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    least = _INK_PIXELS * (dpi * shrink / _INK_DPI) ** 2
    marks = []
    for label in range(1, count):
        x, y, width, height = (int(value) for value in stats[label][:4])
        ys, xs = np.nonzero(ink[y : y + height, x : x + width] & (labels[y : y + height, x : x + width] == label))
        if len(ys) < least:
            continue
        x0, y0, x1, y1 = x + xs.min(), y + ys.min(), x + xs.max() + 1, y + ys.max() + 1
        if bright[y0:y1, x0:x1].mean() >= _HIGHLIGHT:
            continue
        marks.append((x0 / shrink, y0 / shrink, x1 / shrink, y1 / shrink))
    return marks


def ring_in_colour(rgb: npt.NDArray[np.float64], aspect: float, opaque: npt.NDArray[np.bool_] | None = None) -> bool:
    """Whether the ink of an image, its colours RGB from 0 to 1, is a ring in colour, as a stamp
    leaves (see `_SQUARE` and the rest). `aspect` is its width over its height as the page shows it.
    Only its `opaque` pixels count, when it lets some through; all of a scan's do."""
    if not _SQUARE[0] <= aspect <= _SQUARE[1]:
        return False
    brightest, darkest = rgb.max(axis=2), rgb.min(axis=2)
    saturation = np.where(brightest > 0, (brightest - darkest) / np.maximum(brightest, 1e-6), 0.0)
    ink = (brightest < _PAPER) | (saturation > _COLOURED)
    if opaque is not None:
        ink &= opaque
    if not ink.any() or saturation[ink].mean() < _STAMP_SATURATION:
        return False
    height, width = ink.shape
    y, x = np.mgrid[0:height, 0:width]
    radius = np.hypot((x + 0.5) / width * 2 - 1, (y + 0.5) / height * 2 - 1)  # 1 at the round's edge
    corners, band, inside = radius > 1, (radius > _STAMP_BORDER) & (radius <= 1), radius <= _STAMP_BORDER
    round_mark = ink[corners].mean() <= _STAMP_CORNERS * ink[radius <= 1].mean()
    return bool(round_mark and ink[band].mean() >= _STAMP_BORDER_INK * ink[inside].mean())
