"""Reads text pages of a PDF from their text layer."""

from typing import Any

import pymupdf

from pdf_to_doc.model import Document, Page, Paragraph
from pdf_to_doc.thai import is_thai, join_lines, repair

# PyMuPDF's defaults, except that a glyph with no Unicode mapping comes out as
# U+FFFD (visible, and countable when validating the text layer) instead of
# U+0000 (invisible in the output).
_FLAGS = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE
# A gap wider than this share of the font size separates two words.
_WORD_GAP = 0.2


def read_pdf(source: bytes) -> Document:
    with pymupdf.open(stream=source, filetype="pdf") as pdf:
        pages = tuple(
            Page(number=index + 1, kind="text", blocks=_paragraphs(page))
            for index, page in enumerate(pdf)
        )
    return Document(pages=pages)


def _paragraphs(page: pymupdf.Page) -> tuple[Paragraph, ...]:
    layout: dict[str, Any] = page.get_text("rawdict", flags=_FLAGS)
    paragraphs = []
    for block in layout["blocks"]:
        if block["type"] != 0:
            continue
        text = repair(join_lines([_line_text(line) for line in block["lines"]]))
        if text.strip():
            paragraphs.append(Paragraph(text))
    return tuple(paragraphs)


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
