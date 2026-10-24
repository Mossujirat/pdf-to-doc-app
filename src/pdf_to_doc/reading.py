"""Reads a PDF page by page: a text page from its text layer, an OCR page with the OCR engine.

A page whose text layer is there but cannot be trusted is also an OCR page. With images
kept, a scan is kept as an image of the page instead, and not read at all.
"""

from collections.abc import Callable
from dataclasses import replace

import numpy as np
import numpy.typing as npt
import pymupdf

from pdf_to_doc.layout import EDGE_BAND, PageRows, body_text_share, page_blocks
from pdf_to_doc.model import Document, KeptImage, Page, PageKind, Placeholder
from pdf_to_doc.ocr import OcrEngine, read_page, render
from pdf_to_doc.pdf_text import text_rows
from pdf_to_doc.progress import Progress
from pdf_to_doc.validation import trusted

# The body is the page outside the edge bands, where stamped headers and page
# counters sit. A page is an OCR page when its text layer covers little of the
# body, and the body shows more outside that text than the text itself covers:
# a scan, or text drawn as shapes. Text over a scan, such as a stamp, a note or
# a caption, is then still taken from the text layer. A text layer covering more
# than this share of the page is the page's text, as on a scan made searchable.
_OCR_MAX_TEXT_SHARE = 0.05
# What the body shows is measured on a low-resolution grey render, of 50 dpi: a
# pixel lighter than this grey level counts as blank paper.
_DRAWN_ZOOM = 50 / 72
_BLANK = 245
# A page that needs OCR is a scan when at least this share of what its body shows
# outside its text lies in its images. Text drawn as shapes lies outside them.
_SCAN_INK_IN_IMAGES = 0.5
# A kept page's image: the page as it is shown, as a JPEG of this resolution and quality.
_KEPT_DPI = 150
_KEPT_QUALITY = 75


def read_pdf(
    pdf: pymupdf.Document,
    ocr: Callable[[], OcrEngine],
    progress: Callable[[Progress], None],
    *,
    keep_images: bool = False,
) -> Document:
    """Read every page. `ocr` gives the engine, and is called once, when the first OCR page needs one.
    With `keep_images`, a scan is kept as an image of the page instead. `progress` hears before each
    page image is made, and before each OCR page is read."""
    pages = list(pdf.pages())
    rows = [text_rows(page) for page in pages]
    # A scan's text layer is checked too, as the text laid over it is kept.
    untrusted = {index for index, page_rows in enumerate(rows) if not trusted(page_rows)}
    kinds = [_kind(page, rows[index], index in untrusted, keep_images) for index, page in enumerate(pages)]
    kept: dict[int, KeptImage] = {}
    kept_pages = [index for index, kind in enumerate(kinds) if kind == "kept"]
    for count, index in enumerate(kept_pages, start=1):
        progress(Progress(stage="images", current=count, total=len(kept_pages)))
        kept[index] = _kept_image(pages[index])
        # The scan behind its text is the page itself, not a picture on it.
        rows[index] = replace(rows[index], images=(), kind="kept")
    ocr_pages = [index for index, kind in enumerate(kinds) if kind == "ocr"]
    engines: dict[int, str] = {}
    # The engine lives only as long as this call: an engine holds what it last read.
    engine: OcrEngine | None = None
    for count, index in enumerate(ocr_pages, start=1):
        progress(Progress(stage="ocr", current=count, total=len(ocr_pages)))
        if engine is None:
            engine = ocr()
        image = render(pages[index])
        # An untrusted text layer passes on nothing, not even its stamps.
        text_layer = replace(rows[index], rows=(), tables=()) if index in untrusted else rows[index]
        rows[index] = read_page(engine, image, text_layer)
        engines[index] = engine.name
    return Document(
        pages=tuple(
            Page(
                number=index + 1,
                kind=rows[index].kind,
                # A kept page's own text, such as a note typed over it, follows its placeholder.
                blocks=(Placeholder("scan", kept[index]), *blocks) if index in kept else blocks,
                engine=engines.get(index),
                untrusted_text_layer=index in untrusted,
            )
            for index, blocks in enumerate(page_blocks(rows))
        )
    )


def _kind(page: pymupdf.Page, rows: PageRows, untrusted: bool, keep_images: bool) -> PageKind:
    """How the page is read: from its text layer, unless that cannot be trusted or covers little of
    the body while the body shows more outside it; then with OCR, or, with images kept, not at all
    when the page is a scan."""
    if untrusted:
        return "ocr"
    text = body_text_share(rows)
    if text >= _OCR_MAX_TEXT_SHARE:
        return "text"
    inked = _ink_beyond_text(page, rows)
    if _body(inked).mean() <= text:
        return "text"
    return "kept" if keep_images and _is_scan(inked, rows) else "ocr"


def _kept_image(page: pymupdf.Page) -> KeptImage:
    """The page as it is shown, annotations and all, compressed at once: its pixels are not kept."""
    pix = page.get_pixmap(dpi=_KEPT_DPI, colorspace=pymupdf.csRGB, alpha=False)
    return KeptImage(pix.tobytes("jpg", jpg_quality=_KEPT_QUALITY), page.rect.width, page.rect.height)


def _ink_beyond_text(page: pymupdf.Page, rows: PageRows) -> npt.NDArray[np.bool_]:
    """Which pixels of a low-resolution render of the page are drawn on outside the text layer's
    rows and tables: images, drawings, and text drawn as shapes."""
    zoom = _DRAWN_ZOOM  # pixels per point
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY, alpha=False)
    pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, : pix.width]
    inked = pixels < _BLANK
    covered = [(row.x0, row.y0, row.x1, row.y1) for row in rows.rows]
    covered += [(0.0, table.top, rows.width, table.bottom) for table in rows.tables]
    for x0, y0, x1, y1 in covered:
        inked[int(y0 * zoom) : int(y1 * zoom) + 1, int(x0 * zoom) : int(x1 * zoom) + 1] = False
    return inked


def _is_scan(inked: npt.NDArray[np.bool_], rows: PageRows) -> bool:
    """Whether what the body shows outside the text, as `_ink_beyond_text` found it, lies mostly in
    the page's images: a picture of a page, unlike text drawn as shapes. A page that shows nothing
    but a picture, such as a logo alone, counts as one too: its image is all there is to keep."""
    pictured = np.zeros_like(inked)
    for image in rows.images:
        top, bottom, left, right = (int(edge * _DRAWN_ZOOM) for edge in (image.top, image.bottom, image.x0, image.x1))
        pictured[top : bottom + 1, left : right + 1] = True
    ink = _body(inked)
    return bool(ink.any()) and (ink & _body(pictured)).sum() >= _SCAN_INK_IN_IMAGES * ink.sum()


def _body(pixels: npt.NDArray[np.bool_]) -> npt.NDArray[np.bool_]:
    """The rows of a render outside the edge bands, where stamped headers and page counters sit."""
    band = int(EDGE_BAND * len(pixels))
    return pixels[band : len(pixels) - band]
