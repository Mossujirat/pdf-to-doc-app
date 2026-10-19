"""Reads text pages of a PDF from their text layer."""

from typing import Any

import pymupdf

from pdf_to_doc.layout import PageRows, Row, page_blocks
from pdf_to_doc.model import Document, Page
from pdf_to_doc.thai import is_thai

# PyMuPDF's defaults, except that a glyph with no Unicode mapping comes out as
# U+FFFD (visible, and countable when validating the text layer) instead of
# U+0000 (invisible in the output).
_FLAGS = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE
# A gap wider than this share of the font size separates two words.
_WORD_GAP = 0.2


def read_pdf(source: bytes) -> Document:
    with pymupdf.open(stream=source, filetype="pdf") as pdf:
        blocks_by_page = page_blocks([_page_rows(page) for page in pdf])
    return Document(
        pages=tuple(
            Page(number=index + 1, kind="text", blocks=blocks)
            for index, blocks in enumerate(blocks_by_page)
        )
    )


def _page_rows(page: pymupdf.Page) -> PageRows:
    layout: dict[str, Any] = page.get_text("rawdict", flags=_FLAGS)
    rows = []
    for block in layout["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            x0, y0, x1, y1 = line["bbox"]
            size = round(max(span["size"] for span in line["spans"]), 1)
            bold = all(_is_bold(span) for span in line["spans"] if _span_text(span).strip())
            rows.append(Row(_line_text(line), x0, y0, x1, y1, size, bold))
    return PageRows(rows=tuple(rows), width=page.rect.width, height=page.rect.height)


def _is_bold(span: dict[str, Any]) -> bool:
    return bool(span["flags"] & pymupdf.TEXT_FONT_BOLD) or "bold" in span["font"].lower()


def _span_text(span: dict[str, Any]) -> str:
    return "".join(char["c"] for char in span["chars"])


def _line_text(line: dict[str, Any]) -> str:
    """The characters of one printed line, with spaces where words are set apart.

    PyMuPDF already separates Latin words that are set apart without a space
    character, and never splits Thai. It does not separate Thai from a
    neighbouring Latin word, so that boundary is handled here.
    """
    text = ""
    previous_end = 0.0
    for span in line["spans"]:
        for char in span["chars"]:
            c: str = char["c"]
            start, end = char["bbox"][0], char["bbox"][2]
            if text and _starts_a_new_word(text[-1], c, start - previous_end, span["size"]):
                text += " "
            text += c
            previous_end = end
    return text


def _starts_a_new_word(before: str, after: str, gap: float, font_size: float) -> bool:
    return (
        gap > _WORD_GAP * font_size
        and not before.isspace()
        and not after.isspace()
        and is_thai(before) != is_thai(after)
    )
