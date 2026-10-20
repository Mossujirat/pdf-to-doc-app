"""The PaddleOCR engine on simulated scans; these tests need the models (`pdf-to-doc-models`)."""

import pytest
from markdown_reader import page_texts
from pdf_builder import Scan, pdf

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
