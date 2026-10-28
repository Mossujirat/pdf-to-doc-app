"""A fake OCR engine for tests: it reads each page as the next lines it was given, and
crops and turned images of a page as parts of that page."""

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from pdf_builder import FONT_SIZE, LINE_HEIGHT, TOP, Grid, Styled, laid_out_grid

from pdf_to_doc.ocr import Box, Language, PageImage, TextBox, turned_box

# How sure the engine is of a line, unless the line says otherwise.
CONFIDENT = 0.99
# How sure it is of text it reads upside down.
UPSIDE_DOWN = 0.5
# How far, as a share of the font size, a box reaches past each end of a table cell's text,
# as a detector pads its boxes: over the rule beside text set 4 points from it.
DETECTOR_PADDING = 0.3


@dataclass(frozen=True)
class Unsure:
    """A line the engine reads with low confidence, as a real one reads a smudge or handwriting;
    or a table whose every cell it reads so."""

    line: str | Styled | Grid
    confidence: float = 0.5


Line = str | Styled | Grid | Unsure


@dataclass(frozen=True)
class Sideways:
    """A sideways page: its lines lie on a landscape sheet, as `pdf_builder` draws a
    sideways `Scan`, which a reader turns `turn` degrees clockwise to read. Its `shown`
    lines are printed upright on the page as shown, as a note typed over the scan is.
    With `blank_crops`, the engine finds no text in a crop of it, as in a box drawn
    around a scribble."""

    lines: Sequence[Line]
    turn: Literal[90, 270]
    shown: Sequence[Line] = ()
    blank_crops: bool = False


@dataclass(frozen=True)
class Askew:
    """A page scanned `angle` degrees askew, as `pdf_builder` draws a `Scan` at that angle: the
    image turned, then shrunk to fit the page, about its centre. Like PaddleOCR, the engine
    straightens its boxes by the page's slant, so each lies where its line is drawn, brought in
    towards the page's centre as far as the image was shrunk."""

    lines: Sequence[Line]
    angle: float


class FakeEngine:
    """Lays the lines out as `pdf_builder` draws them, one box per line.

    A line is a string, or a `Styled` line with its own size and position; an
    empty string leaves a blank line. Either can be `Unsure`. A `Grid` gives a box
    for each piece of text in its cells, as `pdf_builder` draws them in Sarabun, padded
    so that it reaches over the rules beside the text. A box is as tall as a real
    detector draws it, about one and a half times the font size.

    Each image of a page as shown starts the next page. Like PaddleOCR, it reads a
    line printed sideways as a tall box, which it turns counter-clockwise before
    reading it: so it reads a sideways page right one way and upside down the other.
    Any smaller image is a crop of one of a sideways page's lines: read upright, it
    has the confidence of the least sure of them, and upside down little.
    """

    name = "fake"

    def __init__(self, *pages: Sequence[Line] | Sideways | Askew) -> None:
        self.pages = list(pages)
        self.images: list[PageImage] = []  # every image it was asked to read

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        shown = [seen for seen in self.images if seen.turn == 0]
        if image.turn == 0:
            shown.append(image)
        page, page_image = self.pages[len(shown) - 1], shown[-1]
        self.images.append(image)
        # How far the image's text is turned clockwise from upright.
        off = (image.turn - page.turn) % 360 if isinstance(page, Sideways) else image.turn
        if {image.width, image.height} != {page_image.width, page_image.height}:
            if isinstance(page, Sideways) and page.blank_crops:
                return ()
            lines = page.lines if isinstance(page, (Sideways, Askew)) else page
            upright = min((confidence for _, _, confidence in _laid_out(lines, 1)), default=CONFIDENT)
            return (TextBox("-", (0, 0, image.width, image.height), UPSIDE_DOWN if off else upright),)
        if isinstance(page, Sideways):
            return _read(page.lines, off, image) + _read(page.shown, image.turn, image)
        if isinstance(page, Askew):
            return _straightened(_read(page.lines, off, image), page.angle, image)
        return _read(page, off, image)


def _read(lines: Sequence[Line], off: int, image: PageImage) -> tuple[TextBox, ...]:
    """The lines as read off an image on which they are turned `off` degrees clockwise
    from upright. Turned a quarter turn, they stand tall and are turned counter-clockwise
    to be read, so they read right when turned clockwise."""
    sheet = (image.height, image.width) if off % 180 else (image.width, image.height)
    readable = off in (0, 90)
    return tuple(
        TextBox(text, turned_box(box, off, *sheet), confidence if readable else UPSIDE_DOWN)
        for text, box, confidence in _laid_out(lines, image.dpi / 72)
    )


def _straightened(boxes: tuple[TextBox, ...], angle: float, image: PageImage) -> tuple[TextBox, ...]:
    """The boxes as an engine reads them on a page scanned `angle` degrees askew, once it has
    straightened them (see `Askew`)."""
    turn = math.radians(abs(angle))
    width, height = image.width, image.height
    shrunk = min(
        width / (width * math.cos(turn) + height * math.sin(turn)),
        height / (height * math.cos(turn) + width * math.sin(turn)),
    )

    def brought_in(x: float, y: float) -> tuple[float, float]:
        return width / 2 + shrunk * (x - width / 2), height / 2 + shrunk * (y - height / 2)

    return tuple(replace(box, box=(*brought_in(*box.box[:2]), *brought_in(*box.box[2:]))) for box in boxes)


def _laid_out(lines: Sequence[Line], scale: float) -> list[tuple[str, Box, float]]:
    """Each line's text, box in pixels on the upright sheet, and confidence."""
    boxes = []
    baseline: float = TOP
    for entry in lines:
        line, confidence = (entry.line, entry.confidence) if isinstance(entry, Unsure) else (entry, CONFIDENT)
        if isinstance(line, Grid):
            grid = laid_out_grid(line, line.y if line.y is not None else baseline)
            padding = DETECTOR_PADDING * FONT_SIZE
            for text in (text for cell in grid.cells for text in cell.texts):
                box = _box(text.x - padding, text.x + text.width + padding, text.baseline, FONT_SIZE, scale)
                boxes.append((text.text, box, confidence))
            baseline = grid.next_baseline
            continue
        styled = line if isinstance(line, Styled) else Styled(line)
        baseline = styled.y if styled.y is not None else baseline
        if styled.text:
            right = styled.x + styled.size / 2 * len(styled.text)
            boxes.append((styled.text, _box(styled.x, right, baseline, styled.size, scale), confidence))
        baseline += max(LINE_HEIGHT, styled.size * 1.4) if isinstance(line, Styled) else LINE_HEIGHT
    return boxes


def _box(left: float, right: float, baseline: float, size: float, scale: float) -> Box:
    """The box a detector draws around text from `left` to `right` on the baseline, in points,
    as pixels `scale` to a point: about one and a half times the font size tall."""
    return left * scale, (baseline - 1.1 * size) * scale, right * scale, (baseline + 0.4 * size) * scale


class BlankEngine:
    """Reads every page image as blank, for tests that only look at text pages."""

    name = "blank"

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        return ()


class FailingEngine:
    """Fails on the first page with the given message, which can quote the document, as a library's error might."""

    name = "failing"

    def __init__(self, message: str = "the engine broke") -> None:
        self.message = message

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        raise RuntimeError(self.message)
