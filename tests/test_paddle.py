"""The PaddleOCR engine on simulated scans; these tests need the models (`pdf-to-doc-models`)."""

from typing import Literal

import pytest
from markdown_reader import page_texts
from pdf_builder import Grid, Line, Scan, pdf

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


@pytest.mark.parametrize("turn", [90, 270])
def test_a_sideways_page_is_turned_the_way_it_reads(turn: Literal[90, 270]) -> None:
    result = convert(pdf(Scan(TIMELINE, dpi=200, angle=0.4, noise=6, seed=8, sideways=turn)))

    [page] = page_texts(result.output.decode("utf-8"))
    in_order = ["แผนการดำเนินงาน (Project Timeline)", "ทบทวนวรรณกรรม", "วิเคราะห์และเขียนรายงาน"]
    assert all(text in page for text in in_order)
    assert [page.index(text) for text in in_order] == sorted(page.index(text) for text in in_order)
