"""OCR pages: scanned pages are read by the OCR engine, page by page, through the conversion function."""

from pathlib import Path
from typing import Literal

import pytest
from fake_ocr import FakeEngine, Sideways, Unsure
from markdown_reader import page_texts
from pdf_builder import LINE_HEIGHT, TOP, Rotated, Scan, Styled, pdf

from pdf_to_doc import ConversionResult, convert
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


# Clauses long enough to reach across the page, with room after the fourteenth for a note.
CLAUSES = [f"ข้อ {number} ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้" for number in range(1, 22)]
NOTE_Y = TOP + 15 * LINE_HEIGHT


@pytest.mark.parametrize("rotation", [90, 270])
def test_a_note_typed_over_a_rotated_scan_is_read_once_and_the_scan_around_it_is_kept(
    rotation: Literal[90, 270],
) -> None:
    note = Styled("หมายเหตุ แก้ไขวันส่งรายงาน", y=NOTE_Y)
    misread_note = Styled("หมายเหตุ แก้ไขวันสงรายงาน", y=NOTE_Y)
    scan = Scan([*CLAUSES[:14], "", "", "", *CLAUSES[14:]], overlay=[note], dpi=50)
    engine = FakeEngine([*CLAUSES[:14], "", misread_note, "", *CLAUSES[14:]])

    result = convert(pdf(Rotated(scan, rotation)), ocr=engine)

    [page] = markdown_pages(result)
    assert [summary.kind for summary in result.summary.pages] == ["ocr"]
    assert page.count(note.text) == 1
    assert misread_note.text not in page
    assert [clause for clause in CLAUSES if clause not in page] == []
    assert page.index(CLAUSES[13]) < page.index(note.text) < page.index(CLAUSES[14])


# Sideways pages: a reader turns the page to read them, and so does the converter

PRICE_SCHEDULE = [
    "ตารางราคางานพัฒนาระบบ Price Schedule",
    "ค่าตอบแทนผู้วิจัย 100,000 บาท",
    "ค่าวัสดุและอุปกรณ์ 30,000 บาท",
    "ค่าเดินทางไปประชุม 12,500 บาท",
    "รวมทั้งสิ้น 142,500 บาท",
]


@pytest.mark.parametrize("turn", [90, 270])
def test_a_sideways_page_reads_as_the_same_page_upright(turn: Literal[90, 270]) -> None:
    upright = convert(pdf(Scan(PRICE_SCHEDULE, dpi=50)), ocr=FakeEngine(PRICE_SCHEDULE))

    sideways = convert(pdf(Scan(PRICE_SCHEDULE, dpi=50, sideways=turn)), ocr=FakeEngine(Sideways(PRICE_SCHEDULE, turn)))

    assert markdown_pages(sideways) == markdown_pages(upright)
    assert [page.kind for page in sideways.summary.pages] == ["ocr"]


def page_turns(engine: FakeEngine) -> list[int]:
    """How far each image of a whole page that the engine read was turned; crops left out."""
    page = engine.images[0]
    return [image.turn for image in engine.images if {image.width, image.height} == {page.width, page.height}]


def test_an_upright_page_with_a_little_sideways_text_is_not_turned() -> None:
    # Two column headers set sideways, among lines that run across the page.
    engine = FakeEngine(Sideways(["เดือนที่ดำเนินการ", "ร้อยละของผลผลิต"], 90, shown=PRICE_SCHEDULE))

    result = convert(pdf(Scan(PRICE_SCHEDULE, dpi=50)), ocr=engine)

    assert page_turns(engine) == [0]
    assert markdown_pages(result)[0].startswith(PRICE_SCHEDULE[0])


def test_a_sideways_page_is_not_turned_the_wrong_way_when_its_box_reads_as_nothing_turned() -> None:
    # The box read upside down at first; turned, the engine finds nothing in it at all.
    engine = FakeEngine(Sideways(PRICE_SCHEDULE, 90, blank_crops=True))

    convert(pdf(Scan(PRICE_SCHEDULE, dpi=50, sideways=90)), ocr=engine)

    assert page_turns(engine) == [0]


def test_a_sideways_page_that_reads_no_better_turned_is_read_as_it_is() -> None:
    # Lines the engine cannot make out either way, such as faint handwriting.
    engine = FakeEngine(Sideways([Unsure(line) for line in PRICE_SCHEDULE], 90))

    convert(pdf(Scan(PRICE_SCHEDULE, dpi=50, sideways=90)), ocr=engine)

    assert page_turns(engine) == [0]


@pytest.mark.parametrize(("turn", "x"), [(90, 40), (270, 420)])
def test_a_note_typed_over_a_sideways_page_comes_out_once_where_it_sits_on_the_page(
    turn: Literal[90, 270], x: float
) -> None:
    # The note is typed upright at the foot of the page as shown, beside the turned table.
    # Turned with the page, it would lie before the table.
    note = Styled("หมายเหตุ ตรวจสอบแล้ว", x=x, y=800)
    misread_note = Styled("หมายเหตุ ตรวจสอบแลว", x=x, y=800)
    engine = FakeEngine(Sideways(PRICE_SCHEDULE, turn, shown=[misread_note]))

    result = convert(pdf(Scan(PRICE_SCHEDULE, overlay=[note], dpi=50, sideways=turn)), ocr=engine)

    [page] = markdown_pages(result)
    assert page.count(note.text) == 1
    assert misread_note.text not in page
    assert page.index(PRICE_SCHEDULE[-1]) < page.index(note.text)


@pytest.mark.parametrize("turn", [90, 270])
def test_a_header_stamped_over_scans_is_removed_from_a_sideways_page_too(turn: Literal[90, 270]) -> None:
    stamp = Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40)
    body = ["เนื้อหาหน้าแรกของสัญญา"]
    source = pdf(Scan(body, overlay=[stamp], dpi=50), Scan(PRICE_SCHEDULE, overlay=[stamp], dpi=50, sideways=turn))
    # The engine reads the stamp in each image too.
    engine = FakeEngine([stamp, *body], Sideways(PRICE_SCHEDULE, turn, shown=[stamp]))

    first, second = markdown_pages(convert(source, ocr=engine))

    assert first == body[0]
    assert second.startswith(PRICE_SCHEDULE[0])
    assert stamp.text not in second
