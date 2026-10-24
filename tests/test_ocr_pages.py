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


# Columns: a reader reads each column to its end before the column to its right

THAI_LEFT = [
    "ผู้รับทุนตกลงจะดำเนินการวิจัยตาม",
    "แผนงานที่ได้รับอนุมัติจากผู้ให้ทุน",
    "และจะรายงานผลการดำเนินงานให้",
    "ผู้ให้ทุนทราบเป็นระยะทุกหกเดือน",
    "จนกว่าจะสิ้นสุดระยะเวลาโครงการ",
]
THAI_RIGHT = [
    "ผู้ให้ทุนจะจ่ายเงินทุนเป็นงวดตาม",
    "ความก้าวหน้าของงานที่ผู้รับทุนส่ง",
    "โดยแต่ละงวดต้องผ่านการตรวจรับ",
    "จากคณะกรรมการที่ผู้ให้ทุนแต่งตั้ง",
    "ภายในสามสิบวันนับแต่วันที่ได้รับ",
]
ENGLISH_LEFT = [
    "The Grantee shall carry out the research",
    "described in the approved proposal and",
    "shall report its progress to the Grantor",
    "every six months until the project ends.",
]
ENGLISH_RIGHT = [
    "The Grantor shall pay the grant in parts",
    "as the work progresses, each part after",
    "the committee appointed by the Grantor",
    "has accepted the report for that period.",
]
TITLE = Styled("สัญญารับทุนวิจัย", x=240, y=TOP)
# The baseline of the first line under the title, a blank line below it.
BELOW_TITLE = TOP + 2 * LINE_HEIGHT
Pieces = list[tuple[float, str]]  # pieces of text on one printed line, each at its own x


def two_columns(left: list[str], right: list[str], *, size: float = 12, y: float = BELOW_TITLE) -> list[Styled]:
    """Two columns whose first lines sit on the baseline y; the right one starts at x 300."""
    return [
        Styled(left[0], size=size, y=y),
        *(Styled(line, size=size) for line in left[1:]),
        Styled(right[0], size=size, x=300, y=y),
        *(Styled(line, size=size, x=300) for line in right[1:]),
    ]


@pytest.mark.parametrize(
    ("left", "right", "size", "paragraphs"),
    [
        (THAI_LEFT, THAI_RIGHT, 12, ["".join(THAI_LEFT), "".join(THAI_RIGHT)]),
        (ENGLISH_LEFT, ENGLISH_RIGHT, 9.5, [" ".join(ENGLISH_LEFT), " ".join(ENGLISH_RIGHT)]),
    ],
)
def test_a_page_set_in_two_columns_is_read_one_column_after_the_other(
    left: list[str], right: list[str], size: float, paragraphs: list[str]
) -> None:
    engine = FakeEngine([TITLE, *two_columns(left, right, size=size)])

    result = convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine)

    assert markdown_pages(result) == ["\n\n".join([TITLE.text, *paragraphs])]


def test_columns_whose_paragraphs_end_on_the_same_line_are_still_read_one_after_the_other() -> None:
    left = [*THAI_LEFT[:2], "", *THAI_LEFT[2:]]
    right = [*THAI_RIGHT[:2], "", *THAI_RIGHT[2:]]
    engine = FakeEngine(two_columns(left, right, y=TOP))

    result = convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine)

    paragraphs = [THAI_LEFT[:2], THAI_LEFT[2:], THAI_RIGHT[:2], THAI_RIGHT[2:]]
    assert markdown_pages(result) == ["\n\n".join("".join(lines) for lines in paragraphs)]


def test_a_column_that_carries_on_below_the_end_of_the_other_is_read_to_its_end_first() -> None:
    # As on the last page of terms set in columns: the right column ends early, and the
    # left one carries on below it after a gap, with a page number under both.
    carried_on = ["ผู้รับทุนต้องส่งรายงานฉบับสมบูรณ์", "ภายในสามสิบวันหลังสิ้นสุดโครงการ"]
    engine = FakeEngine(
        [
            *two_columns(THAI_LEFT, THAI_RIGHT[:3], y=TOP),
            Styled(carried_on[0], size=12, y=TOP + 7 * LINE_HEIGHT),
            Styled(carried_on[1], size=12),
            Styled("1", size=12, x=500, y=TOP + 12 * LINE_HEIGHT),
        ]
    )

    result = convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine)

    columns = ["".join(THAI_LEFT), "".join(carried_on), "".join(THAI_RIGHT[:3])]
    assert markdown_pages(result) == ["\n\n".join([*columns, "1"])]


@pytest.mark.parametrize(
    "below",
    [
        [[(72, "ชื่อโครงการ"), (300, "การพัฒนาระบบติดตามงานวิจัยแบบออนไลน์")], [(72, "หัวหน้าโครงการ"), (300, "นางสาวสมหญิง รักดี ตำแหน่งนักวิจัย")]],
        [[(72, "ลงชื่อ ................"), (300, "ลงชื่อ ................")], [(72, "(นายสมชาย ใจดี)"), (300, "(นางสาวสมหญิง รักดี)")]],
    ],
    ids=["labels and values", "signature blocks"],
)
def test_rows_under_two_columns_are_read_row_by_row_after_them(below: list[Pieces]) -> None:
    # Their gaps lie under the columns' gutter, but they are not more of the columns.
    rows = [Styled(text, size=12, x=x, y=TOP + (7 + number) * LINE_HEIGHT) for number, row in enumerate(below) for x, text in row]
    engine = FakeEngine([*two_columns(THAI_LEFT, THAI_RIGHT, y=TOP), *rows])

    [page] = markdown_pages(convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine))

    assert page.startswith("".join(THAI_LEFT) + "\n\n" + "".join(THAI_RIGHT))
    printed = [" ".join(text for _, text in row) for row in below]
    assert [line for line in printed if line not in page] == []


def test_a_note_typed_under_a_column_comes_out_once_at_the_end_of_that_column() -> None:
    under_right_column = BELOW_TITLE + len(THAI_RIGHT) * LINE_HEIGHT
    note = Styled("หมายเหตุ แก้ไขตามบันทึกข้อตกลงฉบับที่สอง", size=12, x=300, y=under_right_column)
    misread_note = Styled("หมายเหตุ แกไขตามบันทึกข้อตกลงฉบับที่สอง", size=12, x=300, y=under_right_column)
    scanned = [TITLE, *two_columns(THAI_LEFT, THAI_RIGHT)]
    engine = FakeEngine([*scanned, misread_note])

    [page] = markdown_pages(convert(pdf(Scan(scanned, overlay=[note], dpi=50)), ocr=engine))

    assert page.count(note.text) == 1
    assert misread_note.text not in page
    assert page.index(THAI_LEFT[-1]) < page.index(THAI_RIGHT[0]) < page.index(THAI_RIGHT[-1]) < page.index(note.text)


def test_a_header_stamped_over_scans_in_columns_is_removed_with_the_page_counter() -> None:
    stamp = Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40)
    counters = [Styled(f"หน้าที่ {number}/2", size=14, y=800) for number in (1, 2)]
    scanned = two_columns(THAI_LEFT, THAI_RIGHT, y=TOP)
    source = pdf(*(Scan(scanned, overlay=[stamp, counter], dpi=50) for counter in counters))
    # The engine reads the stamp and the counter in each image too.
    engine = FakeEngine(*([stamp, *scanned, counter] for counter in counters))

    pages = markdown_pages(convert(source, ocr=engine))

    assert pages == ["".join(THAI_LEFT) + "\n\n" + "".join(THAI_RIGHT)] * 2


def test_initials_in_the_margin_beside_a_column_do_not_stop_it_being_read_whole() -> None:
    initials = Styled("สช", size=12, x=30, y=BELOW_TITLE + 2 * LINE_HEIGHT)
    engine = FakeEngine([TITLE, *two_columns(THAI_LEFT, THAI_RIGHT), initials])

    [page] = markdown_pages(convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine))

    assert page.endswith("\n\n" + "".join(THAI_RIGHT))
    assert [line for line in THAI_LEFT if line not in page] == []
    assert page.index(THAI_LEFT[-1]) < page.index(THAI_RIGHT[0])


def test_a_new_column_starts_a_new_paragraph_even_inside_a_numbered_clause() -> None:
    # As a new page does: the converter does not guess whether a clause runs on.
    left = ["1. ผู้รับทุนตกลงดำเนินการวิจัย", "ตามแผนงานที่ได้รับอนุมัติแล้ว", "2. ผู้ให้ทุนจะจ่ายเงินทุนเป็นงวด"]
    right = ["ตามความก้าวหน้าของงานทุกงวด", "3. ผู้รับทุนส่งรายงานฉบับสมบูรณ์", "ภายในสามสิบวันหลังจบโครงการ"]
    engine = FakeEngine(two_columns(left, right, y=TOP))

    result = convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=engine)

    assert markdown_pages(result) == [
        f"- {left[0]}{left[1]}\n- {left[2]}\n\n{right[0]}\n\n- {right[1]}{right[2]}",
    ]


def on_rows(rows: list[Pieces]) -> list[Styled]:
    """Each row's pieces on one baseline, a line below the row before; an empty row is a blank line."""
    return [Styled(text, size=12, x=x, y=TOP + number * LINE_HEIGHT) for number, row in enumerate(rows) for x, text in row]


def assert_read_row_by_row(rows: list[Pieces]) -> None:
    [page] = markdown_pages(convert(pdf(Scan(["ภาพสแกน"], dpi=50)), ocr=FakeEngine(on_rows(rows))))
    printed = [" ".join(text for _, text in row) for row in rows if row]
    assert [line for line in printed if line not in page] == []
    assert [page.index(line) for line in printed] == sorted(page.index(line) for line in printed)


LABELS_AND_VALUES: dict[str, list[Pieces]] = {
    "values at a tab stop": [
        [(72, "ชื่อโครงการ"), (230, "การพัฒนาระบบติดตามงานวิจัย")],
        [(72, "ผู้รับทุน"), (230, "มหาวิทยาลัยตัวอย่างแห่งประเทศไทย")],
        [(230, "คณะวิศวกรรมศาสตร์")],
        [(72, "ระยะเวลา"), (230, "สิบสองเดือนนับแต่วันลงนามในสัญญา")],
        [(72, "ผู้ประสานงาน"), (230, "นางสาวตัวอย่าง ใจดี")],
    ],
    "values after a colon": [
        [(72, "ชื่อโครงการ:"), (175, "การพัฒนาระบบติดตามงานวิจัยแบบออนไลน์")],
        [(72, "หัวหน้าโครงการ:"), (175, "นางสาวสมหญิง รักดี")],
        [(72, "ระยะเวลา:"), (175, "สิบสองเดือนนับแต่วันลงนามในสัญญา")],
    ],
    "long labels and short values": [
        [(72, "สำเนาบัตรประจำตัวประชาชนของผู้รับทุน"), (430, "แนบแล้ว")],
        [(72, "หนังสือรับรองการจดทะเบียนนิติบุคคล"), (430, "แนบแล้ว")],
        [(72, "แผนการดำเนินงานและงบประมาณโครงการ"), (430, "ยังไม่แนบ")],
    ],
    "terms and their definitions": [
        [(72, "ผู้ให้ทุน"), (200, "หน่วยงานที่จ่ายเงินทุนตามสัญญานี้")],
        [(72, "ผู้รับทุน"), (200, "บุคคลหรือนิติบุคคลที่ได้รับเงินทุน")],
        [(200, "เพื่อดำเนินโครงการตามสัญญา")],
        [(72, "งวดงาน"), (200, "ช่วงเวลาที่ต้องส่งมอบผลงานแต่ละครั้ง")],
    ],
    "a block of them between paragraphs": [
        [(72, "ผู้รับทุนตกลงส่งเอกสารต่อไปนี้ให้ผู้ให้ทุนภายในกำหนดเวลา")],
        [],
        [(72, "รายงานฉบับย่อ"), (230, "ภายในวันที่ 31 มีนาคม 2568")],
        [(72, "รายงานฉบับสมบูรณ์"), (230, "ภายในวันที่ 30 กันยายน 2568")],
        [],
        [(72, "หากส่งล่าช้าผู้ให้ทุนอาจระงับการจ่ายเงินงวดถัดไปได้")],
    ],
    "a table without rules or numbers": [
        [(72, "ชื่อ"), (220, "บทบาท"), (380, "หน่วยงาน")],
        [(72, "นายสมชาย ใจดี"), (220, "หัวหน้าโครงการ"), (380, "คณะวิทยาศาสตร์")],
        [(72, "นางสาวสมหญิง รักดี"), (220, "นักวิจัยร่วม"), (380, "คณะวิศวกรรมศาสตร์")],
        [(72, "นายสมศักดิ์ มีสุข"), (220, "ผู้ช่วยวิจัย"), (380, "คณะเกษตรศาสตร์")],
    ],
    "a table of amounts by year": [
        [(72, "หมวดค่าใช้จ่าย"), (300, "ปีที่ 1 ปีที่ 2 ปีที่ 3")],
        [(72, "ค่าตอบแทนผู้วิจัยและผู้ช่วยวิจัย"), (300, "96,000.00 48,000.00 48,000.00")],
        [(72, "ค่าวัสดุอุปกรณ์และค่าใช้สอยอื่น"), (300, "30,000.00 15,000.00 12,000.00")],
        [(72, "ค่าเดินทางไปประชุมและเก็บข้อมูล"), (300, "12,500.00 10,000.00 8,500.00")],
    ],
    "a form with two fields on each line": [
        [(72, "ชื่อ นายสมชาย ใจดี"), (330, "วันที่ 1 มกราคม 2567")],
        [(72, "ตำแหน่ง หัวหน้าโครงการ"), (330, "โทรศัพท์ 02 123 4567")],
        [(72, "หน่วยงาน คณะวิทยาศาสตร์"), (330, "อีเมล somchai@example.com")],
    ],
}


@pytest.mark.parametrize("rows", LABELS_AND_VALUES.values(), ids=LABELS_AND_VALUES.keys())
def test_labels_set_apart_from_their_values_are_read_row_by_row(rows: list[Pieces]) -> None:
    assert_read_row_by_row(rows)


def test_holes_a_diagonal_watermark_leaves_in_lines_are_not_a_gutter() -> None:
    # The watermark wipes out each line a little further along than the line above, so
    # the text after each hole starts somewhere else, unlike a column's lines.
    assert_read_row_by_row(
        [
            [(72, "ประกอบกิจการค้าอุปกรณ์สำนักงาน"), (302, "และเครื่องมือสื่อสารทุกชนิดตามที่ได้ระบุไว้")],
            [(72, "ประกอบกิจการรับจ้างออกแบบระบบงาน"), (338, "และอุปกรณ์สื่อสารทุกชนิดตามที่ระบุไว้")],
            [(72, "ประกอบกิจการค้าเครื่องรับส่งวิทยุ"), (374, "และติดตั้งระบบคอมพิวเตอร์ทุกแบบ")],
        ]
    )


def test_a_line_with_a_wide_gap_in_it_is_one_line_not_two_columns() -> None:
    assert_read_row_by_row(
        [
            [(72, "ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้")],
            [],
            [(72, "สัญญาเลขที่ 123/2567 ของมหาวิทยาลัยตัวอย่าง"), (330, "ลงวันที่ 1 มกราคม 2567 ที่กรุงเทพมหานคร")],
            [],
            [(72, "และส่งรายงานทุกหกเดือนจนกว่าจะสิ้นสุดโครงการ")],
        ]
    )


# Their lines are as short as labels', so they cannot be told apart from labels yet (ticket 32).
SHORT_LINES_BESIDE_OTHER_TEXT: dict[str, list[Pieces]] = {
    "a letter with a panel of addresses": [
        [(72, "บริษัทขอแจ้งให้ทราบว่าได้รับเอกสารประกอบการเสนอราคา"), (440, "สำนักงานใหญ่")],
        [(72, "ของท่านครบถ้วนแล้ว และจะแจ้งผลการพิจารณาให้ทราบ"), (440, "กรุงเทพมหานคร")],
        [(72, "ภายในสามสิบวันนับแต่วันที่ได้รับหนังสือฉบับนี้"), (440, "โทร 02 123 4567")],
        [(72, "จึงเรียนมาเพื่อโปรดทราบและขอขอบคุณมาในโอกาสนี้"), (440, "ทะเบียน 0105556012345")],
    ],
    "signature blocks side by side": [
        [(72, "ลงชื่อ ................"), (240, "ลงชื่อ ................"), (410, "ลงชื่อ ................")],
        [(72, "(นายสมชาย ใจดี)"), (240, "(นางสาวสมหญิง รักดี)"), (410, "(นายสมศักดิ์ มีสุข)")],
        [(72, "ผู้ให้ทุน"), (240, "ผู้รับทุน"), (410, "พยาน")],
    ],
    "bank details beside the signatories": [
        [(72, "ธนาคาร กรุงไทย สาขาสีลม"), (330, "นายสมชาย ใจดี")],
        [(72, "ชื่อบัญชี มหาวิทยาลัยตัวอย่าง"), (330, "หัวหน้าโครงการ")],
        [(72, "เลขที่บัญชี 123-4-56789-0"), (330, "นางสาวสมหญิง รักดี")],
        [(72, "ประเภท ออมทรัพย์"), (330, "นักวิจัยร่วม")],
    ],
}


@pytest.mark.parametrize("rows", SHORT_LINES_BESIDE_OTHER_TEXT.values(), ids=SHORT_LINES_BESIDE_OTHER_TEXT.keys())
def test_short_lines_beside_other_text_are_read_row_by_row_for_now(rows: list[Pieces]) -> None:
    assert_read_row_by_row(rows)
