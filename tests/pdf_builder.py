"""Builds small PDFs from reference text, so tests know exactly what each page says.

A page is a list of lines. A line is either a string, drawn as one run of text,
or a `Spaced` line whose pieces are drawn one by one with extra room between
them, the way justified text or word-by-word PDF writers place glyphs.
An empty string leaves a blank line, which starts a new paragraph.
"""

from dataclasses import dataclass
from pathlib import Path

import pymupdf

FONT_FILE = Path(__file__).parent / "fonts" / "Sarabun-Regular.ttf"
FONT_SIZE = 16
LINE_HEIGHT = 22
LEFT = 72
TOP = 100


@dataclass(frozen=True)
class Spaced:
    pieces: tuple[str, ...]
    gap: float


Line = str | Spaced


def pdf(*pages: list[Line]) -> bytes:
    doc = pymupdf.open()
    font = pymupdf.Font(fontfile=str(FONT_FILE))
    for lines in pages:
        page = doc.new_page()
        y = TOP
        for line in lines:
            if isinstance(line, Spaced):
                x: float = LEFT
                for piece in line.pieces:
                    _draw(page, x, y, piece)
                    x += font.text_length(piece, fontsize=FONT_SIZE) + line.gap
            elif line:
                _draw(page, LEFT, y, line)
            y += LINE_HEIGHT
    data: bytes = doc.tobytes()
    doc.close()
    return data


def _draw(page: pymupdf.Page, x: float, y: float, text: str) -> None:
    page.insert_text(
        (x, y), text, fontfile=str(FONT_FILE), fontname="sarabun", fontsize=FONT_SIZE
    )
