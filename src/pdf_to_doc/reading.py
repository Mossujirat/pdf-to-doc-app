"""Reads a PDF page by page: a text page from its text layer, an OCR page with the OCR engine.

A page whose text layer is there but cannot be trusted is also an OCR page. With images
kept, a scan is kept as an image of the page instead, and not read at all.
"""

from collections.abc import Callable
from dataclasses import replace

import numpy as np
import numpy.typing as npt
import pymupdf

from pdf_to_doc.layout import EDGE_BAND, PageRows, Row, body_text_share, page_blocks
from pdf_to_doc.model import Document, KeptImage, Page, PageKind, Placeholder
from pdf_to_doc.ocr import OcrEngine, read_page, render
from pdf_to_doc.pdf_images import kept_page
from pdf_to_doc.pdf_text import kept_pictures, text_rows
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
# A scan made searchable hides the text of its picture: drawn invisible, or under an
# opaque image drawn after it. Text is under an image when this share of its box lies
# in the image's, nearly all, as a glyph's box reaches a little past what it draws; a row
# is hidden when hidden text covers most of it. Both were set on synthetic pages.
_TEXT_UNDER_AN_IMAGE = 0.9
_HIDDEN_ROW_SHARE = 0.5


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
    for index in untrusted:
        # An untrusted text layer passes on nothing, not even its stamps, whether its page is
        # read with OCR or kept.
        rows[index] = replace(rows[index], rows=(), tables=())
    kept: dict[int, KeptImage] = {}
    kept_pages = [index for index, kind in enumerate(kinds) if kind == "kept"]
    for count, index in enumerate(kept_pages, start=1):
        progress(Progress(stage="images", current=count, total=len(kept_pages)))
        kept[index] = kept_page(pages[index])
        # The scan behind its text is the page itself, not a picture on it.
        rows[index] = replace(rows[index], images=(), kind="kept")
    if keep_images:
        # Pictures on a text page are kept as themselves.
        with_pictures = [index for index, kind in enumerate(kinds) if kind == "text" and rows[index].images]
        for index in with_pictures:
            rows[index] = replace(rows[index], images=kept_pictures(pages[index]))
    ocr_pages = [index for index, kind in enumerate(kinds) if kind == "ocr"]
    engines: dict[int, str] = {}
    # The engine lives only as long as this call: an engine holds what it last read.
    engine: OcrEngine | None = None
    for count, index in enumerate(ocr_pages, start=1):
        progress(Progress(stage="ocr", current=count, total=len(ocr_pages)))
        if engine is None:
            engine = ocr()
        rows[index] = read_page(engine, render(pages[index]), rows[index])
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
    """How the page is read. With images kept, a scan is not read at all: judged by the text a
    reader sees on it, it would be read with OCR, and what it shows outside that text lies mostly
    in its images. So a scan made searchable is kept too, and so is a scan whose text layer cannot
    be trusted. Otherwise a page is read from its text layer, unless that cannot be trusted, or
    covers little of the body while the body shows more outside it; then it is read with OCR."""
    if keep_images:
        shown = _shown(page, rows)
        inked = _ink_needing_ocr(page, shown)
        if inked is not None and _is_scan(inked, shown):
            return "kept"
    if untrusted:
        return "ocr"
    return "text" if _ink_needing_ocr(page, rows) is None else "ocr"


def _ink_needing_ocr(page: pymupdf.Page, rows: PageRows) -> npt.NDArray[np.bool_] | None:
    """What the page shows outside the rows, as `_ink_beyond_text` finds it, when that makes it a page
    to read with OCR: the rows cover little of the body, and the body shows more outside them than
    they cover. None when the rows are the page's text."""
    text = body_text_share(rows)
    if text >= _OCR_MAX_TEXT_SHARE:
        return None
    inked = _ink_beyond_text(page, rows)
    return inked if _body(inked).mean() > text else None


def _shown(page: pymupdf.Page, rows: PageRows) -> PageRows:
    """The rows a reader sees: without those that the text a scan made searchable hides covers."""
    hidden = _hidden_text(page)
    if not hidden:
        return rows

    def seen(row: Row) -> bool:
        box = pymupdf.Rect(row.x0, row.y0, row.x1, row.y1)
        return bool(sum((box & text).get_area() for text in hidden) < _HIDDEN_ROW_SHARE * box.get_area())

    return replace(rows, rows=tuple(row for row in rows.rows if seen(row)))


def _hidden_text(page: pymupdf.Page) -> list[pymupdf.Rect]:
    """Where the page draws text that no one sees, on the page as shown: text drawn invisible, and
    text that an opaque image drawn after it covers.

    PyMuPDF logs what the page draws, in order, on the page as stored. It lists the page's images
    in the same order, saying which have a mask, which lets what lies under the image show through.
    Should the two not hold as many images, no image is taken to hide anything.
    """
    drawn = page.get_bboxlog()
    masked = [image["has-mask"] for image in page.get_image_info()]
    images = sum(1 for what, _ in drawn if what == "fill-image")
    opaque = [not mask for mask in masked] if len(masked) == images else [False] * images
    covering: list[pymupdf.Rect] = []  # the opaque images drawn after the text being looked at
    hidden: list[pymupdf.Rect] = []
    for what, box in reversed(drawn):
        area = pymupdf.Rect(box)
        if what == "fill-image":
            if opaque.pop():
                covering.append(area)
            continue
        under_an_image = sum((area & image).get_area() for image in covering) >= _TEXT_UNDER_AN_IMAGE * area.get_area()
        if what == "ignore-text" or (what in ("fill-text", "stroke-text") and under_an_image):
            hidden.append(area * page.rotation_matrix)
    return hidden


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
    return bool((ink & _body(pictured)).sum() >= _SCAN_INK_IN_IMAGES * ink.sum())


def _body(pixels: npt.NDArray[np.bool_]) -> npt.NDArray[np.bool_]:
    """The rows of a render outside the edge bands, where stamped headers and page counters sit."""
    band = int(EDGE_BAND * len(pixels))
    return pixels[band : len(pixels) - band]
