"""Reads a PDF page by page: a text page from its text layer, an OCR page with the OCR engine.

A page whose text layer is there but cannot be trusted is also an OCR page.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
import pymupdf

from pdf_to_doc.layout import EDGE_BAND, PageRows, body_text_share, page_blocks
from pdf_to_doc.model import Document, Page
from pdf_to_doc.ocr import LANGUAGES, OcrEngine, ocr_page, render
from pdf_to_doc.pdf_text import text_rows
from pdf_to_doc.validation import trusted

# The body is the page outside the edge bands, where stamped headers and page
# counters sit. A page is an OCR page when its text layer covers little of the
# body, and the body shows more outside that text than the text itself covers:
# a scan, or text drawn as shapes. Text over a scan, such as a stamp, a note or
# a caption, is then still taken from the text layer. A text layer covering more
# than this share of the page is the page's text, as on a scan made searchable.
_OCR_MAX_TEXT_SHARE = 0.05
# What the body shows is measured on a low-resolution grey render: a pixel
# lighter than this grey level counts as blank paper.
_DRAWN_DPI = 50
_BLANK = 245


@dataclass(frozen=True)
class Progress:
    """How far a conversion has got: the `current` of `total` pages in a stage, counting from 1."""

    stage: Literal["ocr"]
    current: int
    total: int


ProgressCallback = Callable[[Progress], None]


def read_pdf(pdf: pymupdf.Document, ocr: Callable[[], OcrEngine], progress: ProgressCallback | None = None) -> Document:
    """Read every page. `ocr` gives the engine, and is called only if a page needs one.
    `progress` hears before each OCR page is read."""
    pages = list(pdf.pages())
    rows = [text_rows(page) for page in pages]
    # A scan's text layer is checked too, as the text laid over it is kept.
    untrusted = {index for index, page_rows in enumerate(rows) if not trusted(page_rows)}
    ocr_pages = [index for index, page in enumerate(pages) if index in untrusted or _needs_ocr(page, rows[index])]
    engines: dict[int, str] = {}
    for count, index in enumerate(ocr_pages, start=1):
        if progress:
            progress(Progress(stage="ocr", current=count, total=len(ocr_pages)))
        engine = ocr()
        image = render(pages[index])
        # An untrusted text layer passes on nothing, not even its stamps.
        text_layer = replace(rows[index], rows=(), tables=()) if index in untrusted else rows[index]
        rows[index] = ocr_page(engine.read(image, LANGUAGES), image, text_layer)
        engines[index] = engine.name
    return Document(
        pages=tuple(
            Page(
                number=index + 1,
                kind=rows[index].kind,
                blocks=blocks,
                engine=engines.get(index),
                untrusted_text_layer=index in untrusted,
            )
            for index, blocks in enumerate(page_blocks(rows))
        )
    )


def _needs_ocr(page: pymupdf.Page, rows: PageRows) -> bool:
    text = body_text_share(rows)
    return text < _OCR_MAX_TEXT_SHARE and _ink_beyond_text(page, rows) > text


def _ink_beyond_text(page: pymupdf.Page, rows: PageRows) -> float:
    """The share of the body drawn on outside the text layer's rows and tables:
    images, drawings, and text drawn as shapes."""
    zoom = _DRAWN_DPI / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY, alpha=False)
    pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, : pix.width]
    inked = pixels < _BLANK
    covered = [(row.x0, row.y0, row.x1, row.y1) for row in rows.rows]
    covered += [(0.0, table.top, rows.width, table.bottom) for table in rows.tables]
    for x0, y0, x1, y1 in covered:
        inked[int(y0 * zoom) : int(y1 * zoom) + 1, int(x0 * zoom) : int(x1 * zoom) + 1] = False
    band = int(EDGE_BAND * pix.height)
    return float(inked[band : pix.height - band].mean())
