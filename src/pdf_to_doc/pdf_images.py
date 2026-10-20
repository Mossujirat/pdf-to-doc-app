"""Reads the images drawn on a PDF page: where each sits, and whether it looks like a stamp."""

from typing import Any

import numpy as np
import numpy.typing as npt
import pymupdf

from pdf_to_doc.layout import PlacedImage

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


def placed_images(blocks: list[dict[str, Any]]) -> tuple[PlacedImage, ...]:
    """The pictures among a page's text-layer blocks, leaving out images too small to be one."""
    images = []
    for block in blocks:
        if block["type"] != 1:
            continue
        x0, top, x1, bottom = block["bbox"]
        width, height = x1 - x0, bottom - top
        if min(width, height) >= _SMALLEST_PICTURE:
            images.append(PlacedImage(x0, top, x1, bottom, stamp_like=_stamp_like(block, width / height)))
    return tuple(images)


def _stamp_like(block: dict[str, Any], aspect: float) -> bool:
    if not _SQUARE[0] <= aspect <= _SQUARE[1]:
        return False
    rgb, opaque = _pixels(block)
    brightest, darkest = rgb.max(axis=2), rgb.min(axis=2)
    saturation = np.where(brightest > 0, (brightest - darkest) / np.maximum(brightest, 1e-6), 0.0)
    ink = ((brightest < _PAPER) | (saturation > _COLOURED)) & opaque
    if not ink.any() or saturation[ink].mean() < _STAMP_SATURATION:
        return False
    height, width = ink.shape
    y, x = np.mgrid[0:height, 0:width]
    radius = np.hypot((x + 0.5) / width * 2 - 1, (y + 0.5) / height * 2 - 1)  # 1 at the round's edge
    corners, band, inside = radius > 1, (radius > _STAMP_BORDER) & (radius <= 1), radius <= _STAMP_BORDER
    round_mark = ink[corners].mean() <= _STAMP_CORNERS * ink[radius <= 1].mean()
    return bool(round_mark and ink[band].mean() >= _STAMP_BORDER_INK * ink[inside].mean())


def _pixels(block: dict[str, Any]) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.bool_]]:
    """The image's colours, RGB from 0 to 1, and which pixels are opaque, its soft mask applied.

    Signatures and stamps are often a plain colour whose shape is all in the mask.
    """
    pix = pymupdf.Pixmap(block["image"])
    if pix.colorspace is None or pix.colorspace.n not in (1, 3):  # CMYK, for one
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    rgb = np.repeat(samples[..., :1], 3, axis=2) if pix.n - pix.alpha == 1 else samples[..., :3]
    opaque = samples[..., -1] > 127 if pix.alpha else np.ones((pix.height, pix.width), dtype=bool)
    if block.get("mask"):
        mask = pymupdf.Pixmap(block["mask"])
        values = np.frombuffer(mask.samples, dtype=np.uint8).reshape(mask.height, mask.width, mask.n)[..., 0]
        # The mask can have a resolution of its own.
        rows = np.arange(pix.height) * mask.height // pix.height
        columns = np.arange(pix.width) * mask.width // pix.width
        opaque &= values[rows][:, columns] > 127
    return rgb.astype(np.float64) / 255, opaque
