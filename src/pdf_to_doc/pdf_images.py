"""Reads the images drawn on a PDF page: where each sits, and whether it looks like a stamp. With
images kept, it also makes the images outputs show: a kept page as it is shown, and each picture
as itself."""

import math
from typing import Any

import numpy as np
import numpy.typing as npt
import pymupdf

from pdf_to_doc.layout import PlacedImage
from pdf_to_doc.model import LARGEST_PAGE, KeptImage

# A kept image is no sharper than this, at the size it is shown, and a JPEG of this quality.
KEPT_DPI = 150
_KEPT_QUALITY = 75

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


def placed_images(blocks: list[dict[str, Any]], keep: bool = False) -> tuple[PlacedImage, ...]:
    """The pictures among a page's text-layer blocks, leaving out images too small to be one. With
    `keep`, each carries the picture itself, as kept images show it."""
    images = []
    for block in blocks:
        if block["type"] != 1:
            continue
        x0, top, x1, bottom = block["bbox"]
        width, height = x1 - x0, bottom - top
        if min(width, height) >= _SMALLEST_PICTURE:
            kept_image = _kept_picture(block) if keep else None
            images.append(PlacedImage(x0, top, x1, bottom, _stamp_like(block, width / height), kept_image))
    return tuple(images)


def kept_page(page: pymupdf.Page) -> KeptImage:
    """The page as it is shown, annotations and all, compressed at once: its pixels are not kept.
    It is shown at the page's size, or shrunk, keeping its shape, to the largest page Word takes,
    and is no sharper than `KEPT_DPI` at that size."""
    scale = min(1.0, LARGEST_PAGE / max(page.rect.width, page.rect.height))
    zoom = KEPT_DPI / 72 * scale
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB, alpha=False)
    return KeptImage(_compressed(pix), page.rect.width * scale, page.rect.height * scale)


def lowered(image: KeptImage, dpi: int) -> KeptImage:
    """The image no sharper than `dpi` at the size it is shown, compressed again; the same image
    when it already is."""
    pix = pymupdf.Pixmap(image.data)
    smaller = _no_sharper(pix, image.width, image.height, dpi)
    return image if smaller is pix else KeptImage(_compressed(smaller), image.width, image.height)


def _kept_picture(block: dict[str, Any]) -> KeptImage:
    """The image itself, as the page shows it at its place: in RGB, what its mask lets through left
    transparent, no sharper than `KEPT_DPI`, and turned and flipped as it is drawn on the page as shown.

    Its transform maps the image's top left corner, its right and its down onto the page as shown.
    Drawn upright, its right runs along the page and its down down it. The picture is turned the
    nearest quarter turn to how it is drawn: one set a few degrees off level, as a signature pasted
    by hand often is, is shown level, keeping its shape.

    An image stored as a stencil, drawn in the colour of the moment wherever it is set, comes out
    as it is stored, black and opaque: PyMuPDF does not say what colour drew it.
    """
    pix = pymupdf.Pixmap(block["image"])
    if pix.colorspace is None or pix.colorspace.n != 3:  # grey, CMYK, or another space of colour
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    if block.get("mask"):
        mask = pymupdf.Pixmap(block["mask"])
        if mask.n != 1:
            mask = pymupdf.Pixmap(pymupdf.csGRAY, mask)
        if (mask.width, mask.height) != (pix.width, pix.height):  # a mask can have a resolution of its own
            mask = _resized(mask, pix.width, pix.height)
        pix = pymupdf.Pixmap(pix, mask)
    right_x, right_y, down_x, down_y, _, _ = block["transform"]
    width, height = math.hypot(right_x, right_y), math.hypot(down_x, down_y)  # its own sides on the page, in points
    pix = _no_sharper(pix, width, height, KEPT_DPI)
    quarter_turns = round(math.degrees(math.atan2(right_y, right_x)) / 90) % 4  # of its right, clockwise
    # Turning its right towards its down goes the other way round from the page's: drawn mirrored.
    mirrored = right_x * down_y - right_y * down_x < 0
    shown = (height, width) if quarter_turns % 2 else (width, height)
    return KeptImage(_compressed(_as_drawn(pix, quarter_turns, mirrored)), *shown)


def _no_sharper(pix: pymupdf.Pixmap, width: float, height: float, dpi: float) -> pymupdf.Pixmap:
    """The pixmap scaled down to no more than `dpi` across `width` by `height` points; the same
    pixmap when it is no sharper already."""
    scale = min(width * dpi / 72 / pix.width, height * dpi / 72 / pix.height)
    if scale >= 1:
        return pix
    return _resized(pix, max(1, round(pix.width * scale)), max(1, round(pix.height * scale)))


def _resized(pix: pymupdf.Pixmap, width: int, height: int) -> pymupdf.Pixmap:
    """The pixmap at `width` by `height` pixels: each new pixel the mean of the old ones it covers,
    or, where it grows, a copy of the old one it falls in.

    Not PyMuPDF's own scaled copy: MuPDF 1.28.2's `fz_scale_pixmap` never frees the copy it makes,
    which, lowering every image of a 150-page file a few times over, ran past 2 GiB.
    """
    pixels = _samples(pix)
    for axis, size in ((0, height), (1, width)):
        old = pixels.shape[axis]
        starts = np.arange(size) * old // size  # where each new pixel's share of the old ones starts
        if size < old:
            counts = np.diff(np.append(starts, old)).reshape((-1, 1, 1) if axis == 0 else (1, -1, 1))
            sums = np.add.reduceat(pixels, starts, axis=axis, dtype=np.uint32)
            pixels = ((sums + counts // 2) // counts).astype(np.uint8)
        elif size > old:
            pixels = np.take(pixels, starts, axis=axis)
    return pymupdf.Pixmap(pix.colorspace, width, height, np.ascontiguousarray(pixels).tobytes(), pix.alpha)


def _as_drawn(pix: pymupdf.Pixmap, quarter_turns: int, mirrored: bool) -> pymupdf.Pixmap:
    """The pixmap turned `quarter_turns` quarter turns clockwise, flipped top to bottom first if `mirrored`."""
    if not quarter_turns and not mirrored:
        return pix
    pixels = _samples(pix)
    if mirrored:
        pixels = pixels[::-1]
    pixels = np.ascontiguousarray(np.rot90(pixels, k=-quarter_turns))
    return pymupdf.Pixmap(pix.colorspace, pixels.shape[1], pixels.shape[0], pixels.tobytes(), pix.alpha)


def _compressed(pix: pymupdf.Pixmap) -> bytes:
    """A PNG when the pixmap lets something through, keeping its transparency; otherwise a JPEG."""
    if pix.alpha:
        if _samples(pix)[..., -1].min() < 255:
            png: bytes = pix.tobytes("png")
            return png
        pix = pymupdf.Pixmap(pix, 0)  # every pixel opaque: no transparency to keep
    jpeg: bytes = pix.tobytes("jpg", jpg_quality=_KEPT_QUALITY)
    return jpeg


def _samples(pix: pymupdf.Pixmap) -> npt.NDArray[np.uint8]:
    """The pixmap's values, row by row and pixel by pixel: height by width by values per pixel."""
    rows = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, : pix.width * pix.n]
    return rows.reshape(pix.height, pix.width, pix.n)


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
