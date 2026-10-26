"""Builds small PDFs from reference text, so tests know exactly what each page says.

A page is a list of lines, drawn top to bottom:
- a string is drawn as one run of text at the left margin
- a `Spaced` line has pieces drawn one by one with extra room between them, the
  way justified text, tab stops or word-by-word PDF writers place glyphs
- a `Styled` line sets its own size, weight, indent, alignment or position
- a `Grid` is a ruled table; its cells may span rows and columns, and a cell's
  text may hold several lines separated by newlines
- a `Picture` is an image: a photo, a signature, a stamp or a chart
- an empty string leaves a blank line, which starts a new paragraph

A `Scan` page is an image of its lines, as a scanner makes. Its `overlay` lines are
drawn over the image as text: a stamped header, a typed note, or the visible text layer
of a scan made searchable. A `searchable` scan also holds its lines as text no one sees,
as OCR software writes them: drawn invisible over the image, or under it.
A sideways scan prints its lines on a landscape sheet set a quarter turn on the page.

A `Rotated` page is stored on its side and turned upright by the page's rotation,
as some scanners save pages. It shows the same as the page it holds.

A `Drawn` page draws its lines as shapes, with no text layer, as some PDF printers draw text.

A `Pasted` page, of a size of its own, has a plain grey scan pasted over part or all of it.

The same inputs always give the same bytes, so generated files can be committed.

For intake tests, `protected` encrypts a built PDF, which gives different bytes on
every run, and `grown_to` pads one to an exact size. `remapped` rewrites a built
PDF's fonts so that its text layer reports some characters as others. `highlighted`
marks a passage of a built PDF's first page, as a reader does in a PDF editor.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never

import numpy as np
import pymupdf

# PyMuPDF copies its PDF_ constants in at run time, where type checkers cannot see them.
from pymupdf.mupdf import PDF_ENCRYPT_AES_256, PDF_PERM_COPY

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


@dataclass(frozen=True)
class Cell:
    text: str  # newlines start new lines; a tab sets the next piece apart, as a tab stop would
    colspan: int = 1
    rowspan: int = 1
    boxed: bool = True  # False draws the text with no box around it
    align: Literal["left", "right", "centre"] = "left"  # where each line sits in the cell


@dataclass(frozen=True)
class Grid:
    rows: tuple[tuple[Cell | str, ...], ...]
    widths: tuple[float, ...]  # of each column
    # An absolute baseline for the first row; the following lines continue below the table.
    y: float | None = None


@dataclass(frozen=True)
class Picture:
    """An image below the line before, `width` by `height` points.

    A photo fills its box with colour. A signature is a scribble in blue ink, a stamp
    a red ring and a chart a round pie, each on a transparent ground, as scanned ones
    are pasted in.
    """

    kind: Literal["photo", "signature", "stamp", "chart"]
    width: float
    height: float
    x: float = LEFT
    # How far the line after it comes up over its bottom, as a signature line runs under the signature.
    overlap: float = 0.0
    # An absolute top; the following lines continue below the image.
    y: float | None = None
    turn: Literal[0, 90, 180, 270] = 0  # drawn turned this far counter-clockwise, its box as it lies on the page
    dpi: int = 144  # how many of its pixels fit an inch of the page
    cmyk: bool = False  # a photo stored as a CMYK JPEG, as printers' files hold them


Line = str | Spaced | Styled | Grid | Picture


@dataclass(frozen=True)
class Scan:
    lines: Sequence[Line]
    overlay: Sequence[Line] = ()  # drawn over the image as text
    dpi: int = 200
    angle: float = 0.0  # degrees the paper sat askew
    noise: float = 0.0  # standard deviation of the grain, in grey levels
    seed: int = 0
    # A sideways page: the lines are laid out on a landscape sheet, set on the page so
    # that a reader turns the page this many degrees clockwise to read them.
    sideways: Literal[0, 90, 270] = 0
    landscape: bool = False  # the page itself is A4 on its side, its lines laid out across it
    searchable: Literal["over", "under"] | None = None  # where its lines are hidden as text, if they are


@dataclass(frozen=True)
class Rotated:
    """A page stored landscape, its scan image too, and turned upright by a page rotation.

    Its text is drawn turned the other way, so that it reads upright as shown, as a
    PDF editor writes a note typed on such a page.
    """

    page: Sequence[Line] | Scan
    rotation: Literal[90, 270]


@dataclass(frozen=True)
class Drawn:
    lines: Sequence[Line]


@dataclass(frozen=True)
class Pasted:
    """A page `width` by `height` points: a Word page with a scan pasted in, a page larger
    than Word takes, or a logo alone on a page."""

    width: float
    height: float
    box: tuple[float, float, float, float] | None = None  # where the scan sits; all of the page if None
    # A scan of colour noise this many pixels across, as hard as a scan gets to compress, in
    # place of plain grey paper; each seed gives noise of its own.
    noise_pixels: int = 0
    seed: int = 0


def pdf(*pages: Sequence[Line] | Scan | Rotated | Drawn | Pasted, font_file: Path = SARABUN) -> bytes:
    doc = pymupdf.open()
    doc.set_metadata({})
    for content in pages:
        if isinstance(content, Drawn):
            _draw_as_shapes(doc.new_page(), content.lines, font_file)
            continue
        if isinstance(content, Pasted):
            pasted = doc.new_page(width=content.width, height=content.height)
            scan = _noise(content.noise_pixels, content.seed) if content.noise_pixels else _grey_scan()
            pasted.insert_image(pymupdf.Rect(content.box) if content.box else pasted.rect, pixmap=scan)
            continue
        if isinstance(content, Rotated):
            page = _on_its_side(doc)
            page.set_rotation(content.rotation)
            content = content.page
        elif isinstance(content, Scan) and content.landscape:
            page = _on_its_side(doc)
        else:
            page = doc.new_page()
        if isinstance(content, Scan):
            if content.searchable == "under":
                _draw_lines(page, content.lines, font_file)
            # On a rotated page the image is stored on its side, filling the stored page.
            stored = page.rect * page.derotation_matrix
            page.insert_image(stored, stream=_scanned_image(content, font_file, page.rotation))
            if content.searchable == "over":
                _draw_lines(page, content.lines, font_file, invisible=True)
            _draw_lines(page, content.overlay, font_file)
        else:
            _draw_lines(page, content, font_file)
    data: bytes = doc.tobytes(garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return data


def _draw_lines(page: pymupdf.Page, lines: Sequence[Line], font_file: Path, invisible: bool = False) -> None:
    """Draw the lines top to bottom, as text no one sees if `invisible`, as OCR software hides its text."""
    y: float = TOP
    for line in lines:
        if isinstance(line, Styled):
            y = line.y if line.y is not None else y
            y += _draw_styled(page, y, line, font_file, invisible)
            continue
        if isinstance(line, Grid):
            y = _draw_grid(page, line.y if line.y is not None else y, line, font_file, invisible)
            continue
        if isinstance(line, Picture):
            top = line.y if line.y is not None else y - FONT_SIZE
            box = pymupdf.Rect(line.x, top, line.x + line.width, top + line.height)
            page.insert_image(box * page.derotation_matrix, stream=_picture(line), rotate=(page.rotation + line.turn) % 360)
            y = top + line.height + LINE_HEIGHT - line.overlap
            continue
        if isinstance(line, Spaced):
            x: float = LEFT
            piece_font = _weight(font_file, line.bold)
            for piece in line.pieces:
                _draw(page, x, y, piece, piece_font, FONT_SIZE, invisible)
                x += _width(piece, piece_font, FONT_SIZE) + line.gap
        elif line:
            _draw(page, LEFT, y, line, font_file, FONT_SIZE, invisible)
        y += LINE_HEIGHT


def _on_its_side(doc: pymupdf.Document) -> pymupdf.Page:
    """A new page of A4 on its side."""
    page: pymupdf.Page = doc.new_page(width=842, height=595)
    return page


def _grey_scan() -> pymupdf.Pixmap:
    """A scan of nothing but grey paper, which counts as ink, as scanned paper does."""
    grey = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.IRect(0, 0, 200, 100), False)
    grey.set_rect(grey.irect, (200,))
    return grey


def _noise(across: int, seed: int) -> pymupdf.Pixmap:
    """A square scan of colour noise, `across` pixels each way."""
    pixels = np.random.default_rng(seed).integers(0, 256, (across, across, 3), dtype=np.uint8)
    return pymupdf.Pixmap(pymupdf.csRGB, across, across, pixels.tobytes(), False)


def _draw_as_shapes(page: pymupdf.Page, lines: Sequence[Line], font_file: Path) -> None:
    """The lines drawn as text on a page of their own, turned into paths by way of SVG, and placed on `page`."""
    with pymupdf.open() as paper:
        _draw_lines(paper.new_page(), lines, font_file)
        svg = paper[0].get_svg_image(text_as_path=True)
    with pymupdf.open(stream=svg.encode("utf-8"), filetype="svg") as drawing:
        with pymupdf.open("pdf", drawing.convert_to_pdf()) as shapes:
            page.show_pdf_page(page.rect, shapes, 0)


def _scanned_image(scan: Scan, font_file: Path, rotation: int) -> bytes:
    """The lines as a grey JPEG, rendered at the scan's resolution, askew and grainy,
    turned the other way from how a reader turns a sideways page, and turned back by the page's rotation."""
    with pymupdf.open() as paper:
        _draw_lines(_on_its_side(paper) if scan.sideways or scan.landscape else paper.new_page(), scan.lines, font_file)
        zoom = scan.dpi / 72
        turn = pymupdf.Matrix(zoom, zoom).prerotate(scan.angle - scan.sideways - rotation)
        pix = paper[0].get_pixmap(matrix=turn, colorspace=pymupdf.csGRAY)
    pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    grain = np.random.default_rng(scan.seed).normal(0, scan.noise, pixels.shape) if scan.noise else 0
    grainy = np.clip(pixels + grain, 0, 255).astype(np.uint8)
    image = pymupdf.Pixmap(pymupdf.csGRAY, pix.width, pix.height, grainy.tobytes(), False)
    jpeg: bytes = image.tobytes("jpg", jpg_quality=75)
    return jpeg


def _picture(picture: Picture) -> bytes:
    """The picture as a PNG, or a CMYK photo as a JPEG. A photo is opaque; the others lie on a
    transparent ground. A picture turned a quarter turn is as tall as its box is wide."""
    zoom = picture.dpi / 72
    sides = (picture.height, picture.width) if picture.turn % 180 else (picture.width, picture.height)
    width, height = round(sides[0] * zoom), round(sides[1] * zoom)
    y, x = np.mgrid[0:height, 0:width] / np.array([height, width]).reshape(2, 1, 1)
    radius = np.hypot(x - 0.5, y - 0.5) * 2  # 1 at the edge of the round that fits the box
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    match picture.kind:
        case "photo":
            rgba[...] = np.stack([x * 200 + 30, y * 160 + 60, np.full_like(x, 150), np.full_like(x, 255)], axis=-1)
        case "signature":
            # Loops along a wavering line, as a pen leaves them.
            t = np.linspace(0, 1, 4000)
            curve_x = 0.05 + 0.9 * t + 0.03 * np.sin(t * 60)
            curve_y = 0.5 + 0.3 * np.sin(t * 23) * np.cos(t * 5)
            pen = max(1, round(1.2 * zoom))
            for cx, cy in zip((curve_x * width).astype(int), (curve_y * height).astype(int)):
                rgba[max(0, cy - pen) : cy + pen, max(0, cx - pen) : cx + pen] = (25, 45, 160, 255)
        case "stamp":
            # A ring with a thinner ring inside it, and a mark in the middle.
            ink = ((radius > 0.82) & (radius < 0.96)) | ((radius > 0.62) & (radius < 0.68)) | (radius < 0.12)
            rgba[ink] = (200, 30, 45, 255)
        case "chart":
            # A pie chart: a filled round cut into three coloured slices.
            slices = np.digitize(np.arctan2(y - 0.5, x - 0.5), [-1.0, 1.5])
            colours = np.array([(220, 80, 60, 255), (60, 120, 200, 255), (240, 180, 40, 255)], dtype=np.uint8)
            disc = radius < 0.96
            rgba[disc] = colours[slices[disc]]
        case _:
            assert_never(picture.kind)
    if picture.kind == "photo":
        image = pymupdf.Pixmap(pymupdf.csRGB, width, height, rgba[..., :3].tobytes(), False)
        if picture.cmyk:
            jpeg: bytes = pymupdf.Pixmap(pymupdf.csCMYK, image).tobytes("jpg")
            return jpeg
    else:
        image = pymupdf.Pixmap(pymupdf.csRGB, width, height, rgba.tobytes(), True)
    png: bytes = image.tobytes("png")
    return png


def remapped(source: bytes, mapping: dict[str, str]) -> bytes:
    """The same PDF, whose fonts report `mapping[c]` wherever they reported `c`.

    The pages still show the right text; only the text layer changes, as with a
    font whose ToUnicode map is wrong, or a legacy font that reports some glyphs
    as Private Use Area characters.
    """
    doc = pymupdf.open(stream=source, filetype="pdf")
    done: set[int] = set()
    for xref in range(1, doc.xref_length()):
        kind, value = doc.xref_get_key(xref, "ToUnicode")
        if kind != "xref" or int(value.split()[0]) in done:
            continue
        cmap = int(value.split()[0])
        done.add(cmap)
        glyphs = _to_unicode(doc.xref_stream(cmap).decode("latin-1"))
        changed = {glyph: "".join(mapping.get(char, char) for char in text) for glyph, text in glyphs.items()}
        doc.update_stream(cmap, _cmap(changed).encode("latin-1"))
    data: bytes = doc.tobytes(garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return data


def highlighted(source: bytes, box: tuple[float, float, float, float]) -> bytes:
    """The same PDF, with a box over its first page filled yellow, as a reader marks a
    passage in a PDF editor. The mark is an annotation, not part of the page."""
    doc = pymupdf.open(stream=source, filetype="pdf")
    mark = doc[0].add_rect_annot(pymupdf.Rect(box))
    mark.set_colors(stroke=(1, 1, 0), fill=(1, 1, 0))
    mark.update()
    data: bytes = doc.tobytes(garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return data


def _to_unicode(cmap: str) -> dict[int, str]:
    """Glyph id to text, from a ToUnicode CMap's bfchar and bfrange entries."""
    glyphs: dict[int, str] = {}
    for block in cmap.split("begin")[1:]:
        if not block.startswith(("bfchar", "bfrange")):
            continue
        tokens = re.findall("<[0-9A-Fa-f]*>", block.split("end")[0])
        if block.startswith("bfchar"):
            for source, target in zip(tokens[0::2], tokens[1::2]):
                glyphs[int(source[1:-1], 16)] = _utf16(target)
            continue
        # PyMuPDF writes each range as a first glyph, a last glyph and the text of the first.
        for low, high, first in zip(tokens[0::3], tokens[1::3], tokens[2::3]):
            text = _utf16(first)
            for offset, glyph in enumerate(range(int(low[1:-1], 16), int(high[1:-1], 16) + 1)):
                glyphs[glyph] = text[:-1] + chr(ord(text[-1]) + offset)
    return glyphs


def _utf16(token: str) -> str:
    return bytes.fromhex(token[1:-1]).decode("utf-16-be")


def _cmap(glyphs: dict[int, str]) -> str:
    entries = [f"<{glyph:04X}> <{text.encode('utf-16-be').hex().upper()}>" for glyph, text in sorted(glyphs.items())]
    blocks = "".join(
        f"{len(entries[start : start + 100])} beginbfchar\n" + "\n".join(entries[start : start + 100]) + "\nendbfchar\n"
        for start in range(0, len(entries), 100)
    )
    return (
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo <</Registry(Adobe)/Ordering(UCS)/Supplement 0>> def\n"
        "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
        "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
        f"{blocks}endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
    )


OWNER_PASSWORD = "owner-password"


def protected(source: bytes, *, open_password: str = "", allow_copy: bool = True) -> bytes:
    """The same PDF, encrypted with `OWNER_PASSWORD`.

    Opening it needs `open_password` unless that is empty. `allow_copy` sets
    whether its permissions let readers copy the text. Encryption is random, so
    unlike the other builders this gives different bytes on every run.
    """
    doc = pymupdf.open(stream=source, filetype="pdf")
    data: bytes = doc.tobytes(
        encryption=PDF_ENCRYPT_AES_256,
        owner_pw=OWNER_PASSWORD,
        user_pw=open_password,
        permissions=-1 if allow_copy else ~PDF_PERM_COPY,
    )
    doc.close()
    return data


def grown_to(source: bytes, size: int) -> bytes:
    """The same PDF, grown to exactly `size` bytes by a stream of spaces that nothing draws."""
    padding = size - len(source)
    grown = _padded(source, padding)
    # The stream's own object adds a few bytes; take them off the padding.
    grown = _padded(source, padding - (len(grown) - size))
    if len(grown) != size:
        raise ValueError(f"cannot grow the PDF to exactly {size} bytes")
    return grown


def _padded(source: bytes, padding: int) -> bytes:
    doc = pymupdf.open(stream=source, filetype="pdf")
    xref = doc.get_new_xref()
    doc.update_object(xref, "<<>>")
    doc.update_stream(xref, b" " * padding, compress=0)
    doc.xref_set_key(doc.pdf_catalog(), "Padding", f"{xref} 0 R")  # referenced, so saving keeps it
    data: bytes = doc.tobytes(garbage=3, no_new_id=True)
    doc.close()
    return data


def _draw_styled(page: pymupdf.Page, y: float, line: Styled, font_file: Path, invisible: bool) -> float:
    """Draw a styled line and return how far down the next line goes."""
    font_file = _weight(font_file, line.bold)
    x = line.x
    if line.centered:
        x = (page.rect.width - _width(line.text, font_file, line.size)) / 2
    _draw(page, x, y, line.text, font_file, line.size, invisible)
    return max(LINE_HEIGHT, line.size * 1.4)


CELL_PADDING = 6.0
TAB_GAP = 24.0


def _draw_grid(page: pymupdf.Page, y: float, grid: Grid, font_file: Path, invisible: bool) -> float:
    """Draw a ruled table whose first row's text sits on the baseline y; return the next baseline."""
    placed: list[tuple[int, int, Cell]] = []  # row, column, cell
    covered: set[tuple[int, int]] = set()
    for row_index, row in enumerate(grid.rows):
        column = 0
        for item in row:
            cell = Cell(item) if isinstance(item, str) else item
            while (row_index, column) in covered:
                column += 1
            placed.append((row_index, column, cell))
            for r in range(row_index, row_index + cell.rowspan):
                for c in range(column, column + cell.colspan):
                    covered.add((r, c))
            column += cell.colspan
    heights = [LINE_HEIGHT + CELL_PADDING] * len(grid.rows)
    for row_index, _, cell in placed:
        if cell.rowspan == 1:
            lines = len(cell.text.splitlines()) or 1
            heights[row_index] = max(heights[row_index], lines * LINE_HEIGHT + CELL_PADDING)
    columns = _running_sum(LEFT, grid.widths)
    edges = _running_sum(y - FONT_SIZE, heights)
    for row_index, column, cell in placed:
        rect = pymupdf.Rect(
            columns[column], edges[row_index], columns[column + cell.colspan], edges[row_index + cell.rowspan]
        )
        if cell.boxed:
            page.draw_rect(rect * page.derotation_matrix, color=(0, 0, 0), width=0.5)
        for line_index, text in enumerate(cell.text.splitlines()):
            pieces = text.split("\t")
            width = sum(_width(piece, font_file, FONT_SIZE) for piece in pieces) + TAB_GAP * (len(pieces) - 1)
            x = {"left": rect.x0 + 4, "right": rect.x1 - 4 - width, "centre": (rect.x0 + rect.x1 - width) / 2}[cell.align]
            for piece in pieces:
                baseline = rect.y0 + 3 + FONT_SIZE + line_index * LINE_HEIGHT
                _draw(page, x, baseline, piece, font_file, FONT_SIZE, invisible)
                x += _width(piece, font_file, FONT_SIZE) + TAB_GAP
    return edges[-1] + LINE_HEIGHT + FONT_SIZE


def _running_sum(start: float, steps: tuple[float, ...] | list[float]) -> list[float]:
    """The edges that the steps reach, from the start."""
    edges = [start]
    for step in steps:
        edges.append(edges[-1] + step)
    return edges


def _weight(font_file: Path, bold: bool) -> Path:
    """Bold text is always set in Sarabun Bold, whatever the page's regular font."""
    return SARABUN_BOLD if bold else font_file


def _width(text: str, font_file: Path, size: float) -> float:
    width: float = pymupdf.Font(fontfile=str(font_file)).text_length(text, fontsize=size)
    return width


def _draw(page: pymupdf.Page, x: float, y: float, text: str, font_file: Path, size: float, invisible: bool) -> None:
    """Draw text whose baseline starts at (x, y) on the page as shown, reading upright."""
    point = pymupdf.Point(x, y) * page.derotation_matrix
    page.insert_text(
        point,
        text,
        fontfile=str(font_file),
        fontname=font_file.stem,
        fontsize=size,
        rotate=page.rotation,
        render_mode=3 if invisible else 0,  # 3 draws nothing
    )
