"""Reads the images drawn on a PDF page: where each sits, and whether it looks like a stamp. With
images kept, it also makes the images outputs show: a kept page as it is shown, and each picture
as itself."""

import math
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import numpy as np
import numpy.typing as npt
import pymupdf

from pdf_to_doc.layout import PlacedImage
from pdf_to_doc.model import LARGEST_PAGE, KeptImage
from pdf_to_doc.pictures import a_picture, ring_in_colour

# A kept image is no sharper than this, at the size it is shown, and a JPEG of this quality.
KEPT_DPI = 150
_KEPT_QUALITY = 75


def placed_images(blocks: list[dict[str, Any]], keep: bool = False) -> tuple[PlacedImage, ...]:
    """The pictures among a page's text-layer blocks, leaving out images too small to be one. With
    `keep`, each carries the picture itself, as kept images show it."""
    images = []
    for block in blocks:
        if block["type"] != 1:
            continue
        x0, top, x1, bottom = block["bbox"]
        width, height = x1 - x0, bottom - top
        if a_picture(width, height):
            kept_image = _kept_picture(block) if keep else None
            rgb, opaque = _pixels(block)
            images.append(PlacedImage(x0, top, x1, bottom, ring_in_colour(rgb, width / height, opaque), kept_image))
    return tuple(images)


@contextmanager
def pictures_hidden(page: pymupdf.Page) -> Iterator[pymupdf.Page]:
    """The page, in a document of its own, with the images `placed_images` takes for pictures
    hidden, so that OCR does not read their ink as text. Each is redacted with its images alone,
    inline ones too: what the page draws over them, such as a signing line under a signature,
    still shows."""
    with pymupdf.open() as copy:
        copy.insert_pdf(page.parent, from_page=page.number, to_page=page.number)
        hidden = copy[0]
        for info in hidden.get_image_info():
            x0, top, x1, bottom = info["bbox"]
            if a_picture(x1 - x0, bottom - top):
                hidden.add_redact_annot(pymupdf.Rect(info["bbox"]))
        hidden.apply_redactions(
            images=pymupdf.mupdf.PDF_REDACT_IMAGE_REMOVE,
            graphics=pymupdf.mupdf.PDF_REDACT_LINE_ART_NONE,
            text=pymupdf.mupdf.PDF_REDACT_TEXT_NONE,
        )
        yield hidden


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
