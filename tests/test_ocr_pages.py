"""OCR pages: scanned pages are read by the OCR engine, page by page, through the conversion function."""

from pathlib import Path

import pytest
from fake_ocr import FakeEngine
from markdown_reader import page_texts
from pdf_builder import Scan, Styled, pdf

from pdf_to_doc import ConversionResult, Progress, convert
from pdf_to_doc.cli import main


def markdown_pages(result: ConversionResult) -> list[str]:
    return page_texts(result.output.decode("utf-8"))


def test_a_scanned_page_is_read_by_ocr() -> None:
    result = convert(pdf(Scan(["ข้อความจากภาพสแกน"], dpi=50)), ocr=FakeEngine(["ข้อความจากภาพสแกน"]))

    assert markdown_pages(result) == ["ข้อความจากภาพสแกน"]
    assert [(page.number, page.kind, page.engine) for page in result.summary.pages] == [(1, "ocr", "fake")]


# Which pages are OCR pages: never decided from character count alone


def test_a_text_page_is_never_sent_to_ocr() -> None:
    engine = FakeEngine()

    result = convert(pdf(["ข้อความในไฟล์"]), ocr=engine)

    assert markdown_pages(result) == ["ข้อความในไฟล์"]
    assert engine.images == []
    assert [page.kind for page in result.summary.pages] == ["text"]


def test_a_scan_made_searchable_is_read_from_its_text_layer() -> None:
    # The scan's own text layer covers its body, as after OCR in a PDF editor.
    lines = ["ผู้รับทุนตกลงดำเนินงานตามแผน", "และส่งรายงานตามกำหนดเวลา", "ทุกงวดจนจบโครงการ"]
    engine = FakeEngine()

    result = convert(pdf(Scan(lines, overlay=lines, dpi=50)), ocr=engine)

    assert markdown_pages(result) == ["ผู้รับทุนตกลงดำเนินงานตามแผนและส่งรายงานตามกำหนดเวลาทุกงวดจนจบโครงการ"]
    assert engine.images == []


def test_a_header_stamped_over_scans_is_read_from_the_text_layer_and_removed() -> None:
    stamp = Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40)
    misread_stamp = Styled("เอกสารปกปิด ห้ามเผยแพรก่อนได้รับอนุญาต", size=14, y=40)
    pages = [
        (["เนื้อหาหน้าแรกของสัญญา"], Styled("หน้าที่ 1/2", size=14, y=800)),
        (["เนื้อหาหน้าที่สองของสัญญา"], Styled("หน้าที่ 2/2", size=14, y=800)),
    ]
    source = pdf(*(Scan(body, overlay=[stamp, counter], dpi=50) for body, counter in pages))
    # The engine reads the stamp in the image too, and misreads it on one page.
    engine = FakeEngine([stamp, *pages[0][0], pages[0][1]], [misread_stamp, *pages[1][0], pages[1][1]])

    result = convert(source, ocr=engine)

    assert markdown_pages(result) == ["เนื้อหาหน้าแรกของสัญญา", "เนื้อหาหน้าที่สองของสัญญา"]
    assert [page.kind for page in result.summary.pages] == ["ocr", "ocr"]


def test_a_file_mixing_text_pages_and_scans_is_read_page_by_page() -> None:
    engine = FakeEngine(["หน้าที่สแกนมา"])

    result = convert(pdf(["หน้าที่มีข้อความ"], Scan(["หน้าที่สแกนมา"], dpi=50), ["หน้าสุดท้าย"]), ocr=engine)

    assert markdown_pages(result) == ["หน้าที่มีข้อความ", "หน้าที่สแกนมา", "หน้าสุดท้าย"]
    assert [(page.kind, page.engine) for page in result.summary.pages] == [
        ("text", None),
        ("ocr", "fake"),
        ("text", None),
    ]
    assert len(engine.images) == 1


# What OCR reads becomes text like a text page's

NIKHAHIT = chr(0x0E4D)
SARA_AA = chr(0x0E32)
SARA_AM = chr(0x0E33)


def test_ocr_text_is_repaired_and_its_lines_joined_into_paragraphs() -> None:
    engine = FakeEngine(["ผู้รับทุนตกลงดำเนินงาน", f"ตามแผนการท{NIKHAHIT}{SARA_AA}งาน", "", "ย่อหน้าที่สอง"])

    result = convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine)

    assert markdown_pages(result) == [f"ผู้รับทุนตกลงดำเนินงานตามแผนการท{SARA_AM}งาน\n\nย่อหน้าที่สอง"]


# Progress


def test_progress_is_reported_before_each_ocr_page() -> None:
    updates: list[Progress] = []
    source = pdf(["หน้าที่มีข้อความ"], Scan(["หน้าสแกนแรก"], dpi=50), Scan(["หน้าสแกนที่สอง"], dpi=50))

    convert(source, ocr=FakeEngine(["หน้าสแกนแรก"], ["หน้าสแกนที่สอง"]), progress=updates.append)

    assert updates == [Progress(stage="ocr", current=1, total=2), Progress(stage="ocr", current=2, total=2)]


def test_lines_of_a_scan_stay_one_paragraph_whatever_the_height_of_their_boxes() -> None:
    # Marks above and below the letters make some boxes a quarter taller than others.
    engine = FakeEngine(
        [
            Styled("ผู้รับทุนตกลงจะดำเนินการวิจัย", y=100),
            Styled("ตามแผนงานที่ได้รับอนุมัติ", size=20, y=122),
            Styled("และจะรายงานผลทุกหกเดือน", y=144),
        ]
    )

    result = convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine)

    assert markdown_pages(result) == ["ผู้รับทุนตกลงจะดำเนินการวิจัยตามแผนงานที่ได้รับอนุมัติและจะรายงานผลทุกหกเดือน"]


# What the user sees


def test_the_summary_names_the_ocr_pages_and_the_engine() -> None:
    source = pdf(["หน้าที่มีข้อความ"], Scan(["สแกน"], dpi=50), Scan(["สแกน"], dpi=50), ["ข้อความ"], Scan(["สแกน"], dpi=50))

    result = convert(source, ocr=FakeEngine(["หนึ่ง"], ["สอง"], ["สาม"]))

    summary = result.output.decode("utf-8").split("<!-- page 1 -->")[0]
    assert "อ่านด้วย OCR 3 หน้า ได้แก่หน้า 2–3, 5 ด้วย fake" in summary


def test_a_blank_page_is_not_sent_to_ocr() -> None:
    engine = FakeEngine()

    result = convert(pdf(["หน้าแรก"], []), ocr=engine)

    assert [page.kind for page in result.summary.pages] == ["text", "text"]
    assert engine.images == []


def test_the_command_shows_progress_while_ocr_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "scans.pdf"
    source.write_bytes(pdf(Scan(["หน้าสแกนแรก"], dpi=50), Scan(["หน้าสแกนที่สอง"], dpi=50)))

    assert main([str(source)], ocr=FakeEngine(["หนึ่ง"], ["สอง"])) == 0

    shown = capsys.readouterr().err
    assert "OCR หน้า 1/2" in shown
    assert "OCR หน้า 2/2" in shown


def test_the_command_says_how_to_install_missing_ocr_models(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PDF_TO_DOC_MODELS", str(tmp_path / "no-models-here"))
    source = tmp_path / "scan.pdf"
    source.write_bytes(pdf(Scan(["หน้าสแกน"], dpi=50)))

    assert main([str(source)]) == 9
    assert "pdf-to-doc-models" in capsys.readouterr().err
    assert not (tmp_path / "scan.md").exists()


# Text over a scan: the text layer holds it exactly, OCR reads the rest

CONTRACT_BODY = ["ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้", "และส่งรายงานทุกหกเดือนจนกว่าจะสิ้นสุดโครงการ"] * 6


def test_a_scan_with_text_stamped_in_its_body_is_still_read_with_ocr() -> None:
    stamp = [Styled("สำเนาถูกต้อง", y=400), Styled("ลงชื่อ นายสมชาย ใจดี ผู้มีอำนาจลงนาม", y=425)]
    misread_stamp = [Styled("สำเนาถูกตอง", y=400), Styled("ลงชื่อ นายสมชาย ใจดี ผู้มีอำนาจลงนาม", y=425)]
    engine = FakeEngine([*CONTRACT_BODY, *misread_stamp])

    result = convert(pdf(Scan(CONTRACT_BODY, overlay=stamp, dpi=50)), ocr=engine)

    [page] = markdown_pages(result)
    assert [summary.kind for summary in result.summary.pages] == ["ocr"]
    assert page.startswith("ผู้รับทุนตกลงดำเนินงานตามแผน")
    assert "สำเนาถูกต้อง" in page
    assert "สำเนาถูกตอง" not in page


def test_scan_text_on_the_same_printed_line_as_a_stamp_is_kept() -> None:
    stamp = Styled("เอกสารปกปิด", size=14, y=48, x=420)
    engine = FakeEngine([Styled("บริษัท ตัวอย่าง จำกัด", size=14, y=48), stamp, Styled("เนื้อหาของสัญญาหน้านี้", y=200)])

    result = convert(pdf(Scan(["เนื้อหาของสัญญาหน้านี้"], overlay=[stamp], dpi=50)), ocr=engine)

    [page] = markdown_pages(result)
    assert "บริษัท ตัวอย่าง จำกัด" in page
    assert page.count("เอกสารปกปิด") == 1
