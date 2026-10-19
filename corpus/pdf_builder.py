"""Builds small PDFs from reference text, so tests know exactly what each page says.

A page is a list of lines, drawn top to bottom:
- a string is drawn as one run of text at the left margin
- a `Spaced` line has pieces drawn one by one with extra room between them, the
  way justified text, tab stops or word-by-word PDF writers place glyphs
- a `Styled` line sets its own size, weight, indent, alignment or position
- an empty string leaves a blank line, which starts a new paragraph

The same inputs always give the same bytes, so generated files can be committed.
"""

from dataclasses import dataclass
from pathlib import Path

import pymupdf

FONTS = Path(__file__).parent / "fonts"
SARABUN = FONTS / "Sarabun-Regular.ttf"
SARABUN_BOLD = FONTS / "Sarabun-Bold.ttf"
NIRAMIT = FONTS / "Niramit-Regular.ttf"
FONT_SIZE = 16
LINE_HEIGHT = 22
LEFT = 72
TOP = 100


@dataclass(frozen=True)
class Spaced:
    pieces: tuple[str, ...]
    gap: float
    bold: bool = False


@dataclass(frozen=True)
class Styled:
    text: str
    size: float = FONT_SIZE
    bold: bool = False
    x: float = LEFT
    # An absolute baseline position; the following lines continue below it.
    y: float | None = None
    centered: bool = False


Line = str | Spaced | Styled


def pdf(*pages: list[Line], font_file: Path = SARABUN) -> bytes:
    doc = pymupdf.open()
    doc.set_metadata({})
    for lines in pages:
        page = doc.new_page()
        y: float = TOP
        for line in lines:
            if isinstance(line, Styled):
                y = line.y if line.y is not None else y
                y += _draw_styled(page, y, line, font_file)
                continue
            if isinstance(line, Spaced):
                x: float = LEFT
                piece_font = _weight(font_file, line.bold)
                for piece in line.pieces:
                    _draw(page, x, y, piece, piece_font, FONT_SIZE)
                    x += _width(piece, piece_font, FONT_SIZE) + line.gap
            elif line:
                _draw(page, LEFT, y, line, font_file, FONT_SIZE)
            y += LINE_HEIGHT
    data: bytes = doc.tobytes(garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return data


def _draw_styled(page: pymupdf.Page, y: float, line: Styled, font_file: Path) -> float:
    """Draw a styled line and return how far down the next line goes."""
    font_file = _weight(font_file, line.bold)
    x = line.x
    if line.centered:
        x = (page.rect.width - _width(line.text, font_file, line.size)) / 2
    _draw(page, x, y, line.text, font_file, line.size)
    return max(LINE_HEIGHT, line.size * 1.4)


def _weight(font_file: Path, bold: bool) -> Path:
    """Bold text is always set in Sarabun Bold, whatever the page's regular font."""
    return SARABUN_BOLD if bold else font_file


def _width(text: str, font_file: Path, size: float) -> float:
    width: float = pymupdf.Font(fontfile=str(font_file)).text_length(text, fontsize=size)
    return width


def _draw(page: pymupdf.Page, x: float, y: float, text: str, font_file: Path, size: float) -> None:
    page.insert_text((x, y), text, fontfile=str(font_file), fontname=font_file.stem, fontsize=size)
