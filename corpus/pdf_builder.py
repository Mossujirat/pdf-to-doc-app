"""Builds small PDFs from reference text, so tests know exactly what each page says.

A page is a list of lines. A line is either a string, drawn as one run of text,
or a `Spaced` line whose pieces are drawn one by one with extra room between
them, the way justified text or word-by-word PDF writers place glyphs.
An empty string leaves a blank line, which starts a new paragraph.

The same inputs always give the same bytes, so generated files can be committed.
"""

from dataclasses import dataclass
from pathlib import Path

import pymupdf

FONTS = Path(__file__).parent / "fonts"
SARABUN = FONTS / "Sarabun-Regular.ttf"
NIRAMIT = FONTS / "Niramit-Regular.ttf"
FONT_SIZE = 16
LINE_HEIGHT = 22
LEFT = 72
TOP = 100


@dataclass(frozen=True)
class Spaced:
    pieces: tuple[str, ...]
    gap: float


Line = str | Spaced


def pdf(*pages: list[Line], font_file: Path = SARABUN) -> bytes:
    doc = pymupdf.open()
    doc.set_metadata({})
    font = pymupdf.Font(fontfile=str(font_file))
    for lines in pages:
        page = doc.new_page()
        y = TOP
        for line in lines:
            if isinstance(line, Spaced):
                x: float = LEFT
                for piece in line.pieces:
                    _draw(page, x, y, piece, font_file)
                    x += font.text_length(piece, fontsize=FONT_SIZE) + line.gap
            elif line:
                _draw(page, LEFT, y, line, font_file)
            y += LINE_HEIGHT
    data: bytes = doc.tobytes(garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return data


def _draw(page: pymupdf.Page, x: float, y: float, text: str, font_file: Path) -> None:
    page.insert_text((x, y), text, fontfile=str(font_file), fontname=font_file.stem, fontsize=FONT_SIZE)
