"""The PaddleOCR engine on simulated scans and other OCR pages; these tests need the models (`pdf-to-doc-models`)."""

from typing import Literal

import pytest
from generate import CRISP_PAGE, RULED_TABLE_PAGES
from markdown_reader import page_texts
from pdf_builder import Drawn, Grid, Line, Scan, pdf, remapped

from pdf_to_doc import convert
from pdf_to_doc.quality import score_page

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


SARA_AA = chr(0x0E32)
SARA_AM = chr(0x0E33)


@pytest.mark.parametrize("drawn", [False, True], ids=["text layer that cannot be trusted", "text drawn as shapes"])
def test_every_line_of_an_ocr_page_that_is_not_a_scan_is_read(drawn: bool) -> None:
    # Read as rendered from the PDF, crisp, this page lost its fifth line: the detector found it, then dropped it.
    source = pdf(Drawn(CRISP_PAGE)) if drawn else remapped(pdf(CRISP_PAGE), {SARA_AA: SARA_AM})

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


@pytest.mark.parametrize("turn", [90, 270])
def test_a_ruled_table_printed_sideways_comes_out_as_a_table(turn: Literal[90, 270]) -> None:
    result = convert(pdf(Scan(TIMELINE, dpi=200, angle=0.4, noise=6, seed=8, sideways=turn)))

    [page] = page_texts(result.output.decode("utf-8"))
    score = score_page(page, TIMELINE_REFERENCE)
    assert score.cells_right >= ENOUGH_CELLS * score.cells
    assert score.cer < 0.05
