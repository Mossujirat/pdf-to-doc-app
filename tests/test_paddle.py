"""The PaddleOCR engine on simulated scans and other OCR pages; these tests need the models (`pdf-to-doc-models`)."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import pymupdf
import pytest
from generate import CRISP_PAGE, KAR_AS_KAM, RULED_TABLE_PAGES
from markdown_reader import page_texts
from pdf_builder import SARABUN, Drawn, Grid, Line, Scan, pdf, remapped

from pdf_to_doc import convert
from pdf_to_doc.ocr import LANGUAGES, PageImage, render
from pdf_to_doc.ocr_models import models_folder
from pdf_to_doc.paddle import PaddleOcrEngine
from pdf_to_doc.quality import score_page

CORPUS = Path(__file__).parent.parent / "corpus"

pytestmark = pytest.mark.ocr

LINES = [
    "ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้ทุกประการ และส่งรายงาน",
    "ความก้าวหน้าทุกหกเดือนต่อผู้ให้ทุนจนกว่าจะสิ้นสุดระยะเวลาของโครงการวิจัย",
    "ผู้ให้ทุนจะจ่ายเงินเป็นงวดตามความก้าวหน้าของงานที่ได้รับความเห็นชอบแล้ว",
    "ทั้งนี้ผู้รับทุนต้องส่งรายงานฉบับสมบูรณ์ภายในสามสิบวันหลังสิ้นสุดโครงการ",
]


@pytest.mark.parametrize("angle", [-3.0, 3.0])
def test_a_scan_fed_in_askew_reads_its_lines_in_order(angle: float) -> None:
    result = convert(pdf(Scan(LINES, dpi=200, angle=angle, noise=6, seed=1)))

    [page] = page_texts(result.output.decode("utf-8"))
    assert score_page(page, "".join(LINES)).cer < 0.05


# A project timeline whose title and cells sit close together: the crops that tell
# which way a sideways page reads also catch bits of the lines beside them.
TIMELINE: list[Line] = [
    "แผนการดำเนินงาน (Project Timeline)",
    Grid(
        rows=(
            ("กิจกรรม", "เดือนที่ 1-3", "เดือนที่ 4-6", "เดือนที่ 7-9", "เดือนที่ 10-12"),
            ("ทบทวนวรรณกรรม", "ดำเนินการ", "", "", ""),
            ("เก็บข้อมูลภาคสนาม", "", "ดำเนินการ", "ดำเนินการ", ""),
            ("วิเคราะห์และเขียนรายงาน", "", "", "", "ดำเนินการ"),
        ),
        widths=(200, 110, 110, 110, 120),
    ),
]


@pytest.mark.parametrize("drawn", [False, True], ids=["text layer that cannot be trusted", "text drawn as shapes"])
def test_every_line_of_an_ocr_page_that_is_not_a_scan_is_read(drawn: bool) -> None:
    # Read as rendered from the PDF, crisp, this page lost its fifth line: the detector found it, then dropped it.
    source = pdf(Drawn(CRISP_PAGE)) if drawn else remapped(pdf(CRISP_PAGE), KAR_AS_KAM)

    result = convert(source)

    [text] = page_texts(result.output.decode("utf-8"))
    assert [page.kind for page in result.summary.pages] == ["ocr"]
    score = score_page(text, "".join(CRISP_PAGE))
    assert score.broken.missing_text == 0
    assert score.cer < 0.02


@pytest.mark.parametrize("turn", [90, 270])
def test_a_sideways_page_is_turned_the_way_it_reads(turn: Literal[90, 270]) -> None:
    result = convert(pdf(Scan(TIMELINE, dpi=200, angle=0.4, noise=6, seed=8, sideways=turn)))

    [page] = page_texts(result.output.decode("utf-8"))
    in_order = ["แผนการดำเนินงาน (Project Timeline)", "ทบทวนวรรณกรรม", "วิเคราะห์และเขียนรายงาน"]
    assert all(text in page for text in in_order)
    assert [page.index(text) for text in in_order] == sorted(page.index(text) for text in in_order)


# Ruled tables come out as tables. The cells the engine misreads are out of place by their text,
# such as a word that loses its tone mark, or a stray mark boxed apart from its line (ticket 07):
# on the payment schedule, 8 of 12 cells were in place, with every cell where it belongs. A table
# that is missing, or a row out, leaves far fewer.
ENOUGH_CELLS = 0.6
TIMELINE_REFERENCE = (
    "แผนการดำเนินงาน (Project Timeline)\n\n"
    "| กิจกรรม | เดือนที่ 1-3 | เดือนที่ 4-6 | เดือนที่ 7-9 | เดือนที่ 10-12 |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| ทบทวนวรรณกรรม | ดำเนินการ |  |  |  |\n"
    "| เก็บข้อมูลภาคสนาม |  | ดำเนินการ | ดำเนินการ |  |\n"
    "| วิเคราะห์และเขียนรายงาน |  |  |  | ดำเนินการ |"
)


@pytest.mark.parametrize(("lines", "reference"), [RULED_TABLE_PAGES[0], RULED_TABLE_PAGES[1]], ids=["wrapped cells", "merged cells"])
def test_a_ruled_table_on_a_scan_comes_out_as_a_table(lines: list[str | Grid], reference: str) -> None:
    result = convert(pdf(Scan(lines, dpi=200, angle=0.4, noise=6, seed=3)))

    [page] = page_texts(result.output.decode("utf-8"))
    score = score_page(page, reference)
    assert score.cells_right >= ENOUGH_CELLS * score.cells
    assert score.cer < 0.05


@pytest.mark.parametrize("drawn", [False, True], ids=["text layer that cannot be trusted", "text drawn as shapes"])
def test_a_ruled_table_on_an_ocr_page_that_is_not_a_scan_comes_out_as_a_table_with_every_line(drawn: bool) -> None:
    # The payment schedule: its cells' misreads, such as a Thai digit read as a letter, are many
    # on so small a table, so its shape is checked, and its text against the reference.
    lines, reference = RULED_TABLE_PAGES[0]
    result = convert(pdf(Drawn(lines)) if drawn else remapped(pdf(lines), KAR_AS_KAM))

    [page] = page_texts(result.output.decode("utf-8"))
    assert [summary.kind for summary in result.summary.pages] == ["ocr"]
    rows = [line for line in page.splitlines() if line.startswith("| ") and not line.startswith("| ---")]
    assert [row.count(" | ") + 1 for row in rows] == [3, 3, 3, 3]
    score = score_page(page, reference)
    assert score.broken.missing_text == 0
    assert score.cer < 0.05


@pytest.mark.parametrize("turn", [90, 270])
def test_a_ruled_table_printed_sideways_comes_out_as_a_table(turn: Literal[90, 270]) -> None:
    result = convert(pdf(Scan(TIMELINE, dpi=200, angle=0.4, noise=6, seed=8, sideways=turn)))

    [page] = page_texts(result.output.decode("utf-8"))
    score = score_page(page, TIMELINE_REFERENCE)
    assert score.cells_right >= ENOUGH_CELLS * score.cells
    assert score.cer < 0.05


def test_a_scan_under_a_dot_pattern_watermark_is_read_again_blurred() -> None:
    # The pattern's dots join the lines under it into a region the detector drops. Whether a
    # synthetic page shows that hangs on its text and the pattern's size, and this page is one
    # that does; the real certificate pages that showed it gained 21 lines once blurred. What
    # this guards is the reach into PaddleX that finds the dropped regions.
    engine = PaddleOcrEngine(models_folder())
    page = dotted_watermark_page()
    blurred = PageImage(page.width, page.height, page.dpi, cv2.GaussianBlur(pixels(page), (0, 0), WATERMARK_SOFTENING).tobytes())

    with counted(engine) as reads:
        boxes = engine.read(page, LANGUAGES)

    assert len(reads) == 2
    assert boxes == engine.read(blurred, LANGUAGES)


def test_no_scan_in_the_corpus_is_read_twice() -> None:
    engine = PaddleOcrEngine(models_folder())
    scans = [
        render(page)
        for path in sorted((CORPUS / "synthetic").glob("*.pdf")) + sorted((CORPUS / "degraded").glob("*.pdf"))
        for page in pymupdf.open(path).pages()
        if page.get_images()
    ]

    with counted(engine) as reads:
        for scan in scans:
            engine.read(scan, LANGUAGES)

    assert len(reads) == len(scans) >= 25


# How much the engine blurs a scan under such a pattern before reading it again.
WATERMARK_SOFTENING = 2.0


@contextmanager
def counted(engine: PaddleOcrEngine) -> Iterator[list[int]]:
    """The PaddleOCR reads the engine makes inside the block, one entry each. How many times
    the engine reads a page is not part of its interface, so this reaches into it on purpose."""
    ocr, reads = engine._ocr, []
    predict = ocr.predict

    def counting(*args: object, **kwargs: object) -> object:
        reads.append(1)
        return predict(*args, **kwargs)

    ocr.predict = counting
    try:
        yield reads
    finally:
        del ocr.predict


WATERMARKED_LINES = 57


def dotted_watermark_page() -> PageImage:
    """Lines in 9-point type on a black-and-white scan at 220 dpi, under large diagonal letters
    filled with a checkerboard of 1-pixel dots, as a certificate scanned in black and white."""
    dpi = 220
    with pymupdf.open() as paper:
        page = paper.new_page()
        page.insert_font(fontname="sarabun", fontfile=str(SARABUN))
        for number in range(WATERMARKED_LINES):
            page.insert_text((60, 90 + number * 12.5), LINES[number % len(LINES)], fontname="sarabun", fontsize=9)
        scan = page.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72).prerotate(0.3), colorspace=pymupdf.csGRAY)
    grey = np.frombuffer(scan.samples, np.uint8).reshape(scan.height, scan.width)
    height, width = grey.shape
    letters: np.ndarray = np.zeros(grey.shape, np.uint8)
    font, scale, thickness = cv2.FONT_HERSHEY_DUPLEX, 60 * dpi / 300, int(300 * dpi / 300)
    (text_width, text_height), _ = cv2.getTextSize("COPY", font, scale, thickness)
    cv2.putText(letters, "COPY", ((width - text_width) // 2, (height + text_height) // 2), font, scale, (255,), thickness, cv2.LINE_AA)
    letters = cv2.warpAffine(letters, cv2.getRotationMatrix2D((width // 2, height // 2), 35, 1.0), (width, height))
    rows, columns = np.indices(grey.shape)
    ink = (grey < 140) | ((letters > 127) & ((rows + columns) % 2 == 0))
    black_and_white = pymupdf.Pixmap(pymupdf.csGRAY, width, height, np.where(ink, 0, 255).astype(np.uint8).tobytes(), False)
    with pymupdf.open() as document:
        document.new_page().insert_image(pymupdf.paper_rect("a4"), stream=black_and_white.tobytes("png"))
        return render(document[0])


def pixels(image: PageImage) -> np.ndarray:
    return np.frombuffer(image.samples, np.uint8).reshape(image.height, image.width, 3)
