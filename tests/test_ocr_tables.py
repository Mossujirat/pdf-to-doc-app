"""Ruled tables on OCR pages come out as tables: the rules are found in the page image,
and the text the engine reads is placed in the cells they make."""

from collections.abc import Sequence
from typing import Literal

import pytest
from docx.table import Table
from docx_reader import Cell as WordCell
from docx_reader import cells, read_docx
from fake_ocr import Askew, FakeEngine, Sideways
from fake_ocr import Line as ReadLine
from generate import (
    BUDGET,
    BUDGET_REFERENCE,
    COARSE_TABLE,
    COARSE_TABLE_REFERENCE,
    DATES,
    DATES_REFERENCE,
    KAR_AS_KAM,
    PAYMENT_SCHEDULE,
    PAYMENT_SCHEDULE_REFERENCE,
    PRICE_SCHEDULE,
    PRICE_SCHEDULE_REFERENCE,
    scanned,
)
from markdown_reader import page_texts
from pdf_builder import FONT_SIZE, LINE_HEIGHT, TOP, Cell, Drawn, Grid, Line, Picture, Scan, Styled, pdf, remapped
from test_ocr_pages import THAI_LEFT, THAI_RIGHT, two_columns

from pdf_to_doc import convert


def markdown_pages(scanned_lines: Sequence[Line], read: Sequence[ReadLine]) -> list[str]:
    """The Markdown of a scan of the lines, scanned as the corpus's scans are, which the engine reads as `read`."""
    return converted(pdf(scanned(scanned_lines, seed=1)), FakeEngine(read))


def converted(source: bytes, engine: FakeEngine) -> list[str]:
    return page_texts(convert(source, ocr=engine).output.decode("utf-8"))


def test_a_ruled_table_on_a_scan_becomes_a_table_between_the_text_around_it() -> None:
    grid = Grid(rows=(("งวดที่", "จำนวนเงิน"), ("๑", "50,000"), ("๒", "75,000")), widths=(150, 150))
    lines: list[str | Grid] = ["ผู้ให้ทุนจะจ่ายเงินเป็นงวด", grid, "ตามเงื่อนไขในสัญญา"]

    pages = markdown_pages(lines, lines)

    assert pages == [
        "ผู้ให้ทุนจะจ่ายเงินเป็นงวด\n\n"
        "| งวดที่ | จำนวนเงิน |\n"
        "| --- | --- |\n"
        "| ๑ | 50,000 |\n"
        "| ๒ | 75,000 |\n\n"
        "ตามเงื่อนไขในสัญญา"
    ]


def test_a_scanned_table_keeps_both_lines_of_a_wrapped_cell_and_its_merged_cells() -> None:
    lines: list[str | Grid] = ["ผู้ให้ทุนจะจ่ายเงินเป็นสามงวด", PAYMENT_SCHEDULE, "งบประมาณแยกตามปี", BUDGET]

    pages = markdown_pages(lines, lines)

    assert pages == [
        f"ผู้ให้ทุนจะจ่ายเงินเป็นสามงวด\n\n{PAYMENT_SCHEDULE_REFERENCE}\n\nงบประมาณแยกตามปี\n\n{BUDGET_REFERENCE}"
    ]


def test_several_printed_lines_in_a_scanned_cell_are_read_as_on_a_text_page() -> None:
    # Items stacked beside their amounts are sub-rows; items beside one total keep their breaks;
    # a wrapped description is one sentence.
    lines: list[str | Grid] = [COARSE_TABLE]

    pages = markdown_pages(lines, lines)

    assert pages == [COARSE_TABLE_REFERENCE]


def test_a_scanned_table_is_a_word_table_with_its_merged_cells_and_breaks() -> None:
    lines: list[str | Grid] = [COARSE_TABLE]

    result = convert(pdf(scanned(lines, seed=1)), to="docx", ocr=FakeEngine(lines))

    [[table]] = read_docx(result.output).pages
    assert isinstance(table, Table)
    assert cells(table) == [
        [WordCell("หมวดรายจ่าย"), WordCell("รายการ"), WordCell("จำนวนเงิน")],
        [WordCell("ค่าดำเนินงาน", rowspan=3), WordCell("ค่าวัสดุสำนักงาน"), WordCell("12,000")],
        [WordCell("ค่าถ่ายเอกสาร"), WordCell("3,500")],
        [WordCell("ค่าไปรษณีย์"), WordCell("1,200")],
        [WordCell("ค่าครุภัณฑ์"), WordCell("เครื่องคอมพิวเตอร์\nเครื่องพิมพ์"), WordCell("53,900")],
        [WordCell("ค่าเดินทาง"), WordCell("ค่าเช่ารถและค่าน้ำมันเชื้อเพลิงสำหรับการลงพื้นที่"), WordCell("15,000")],
    ]


def test_a_scanned_table_of_two_rows_keeps_each_date_under_its_heading() -> None:
    lines: list[str | Grid] = ["ระยะเวลาของโครงการ", DATES]

    pages = markdown_pages(lines, lines)

    assert pages == [f"ระยะเวลาของโครงการ\n\n{DATES_REFERENCE}"]


def test_a_double_rule_above_a_total_is_read_as_one_rule() -> None:
    # A row of empty cells 3 points tall draws the second rule.
    grid = Grid(
        rows=(("รายการ", "จำนวนเงิน"), ("ค่าวัสดุ", "45,000"), ("ค่าเดินทาง", "12,000"), ("", ""), ("รวม", "57,000")),
        widths=(170, 110),
        heights=((3, 3.0),),
    )

    pages = markdown_pages([grid], [grid])

    assert pages == [
        "| รายการ | จำนวนเงิน |\n| --- | --- |\n| ค่าวัสดุ | 45,000 |\n| ค่าเดินทาง | 12,000 |\n| รวม | 57,000 |"
    ]


@pytest.mark.parametrize("angle", [-3.0, 3.0])
def test_a_table_scanned_askew_comes_out_as_a_table(angle: float) -> None:
    # The engine straightens its boxes by the page's slant, and the rules are straightened to match.
    lines: list[str | Grid] = ["งบประมาณแยกตามปี", BUDGET]
    source = pdf(Scan(lines, dpi=200, angle=angle, noise=6, seed=1))

    pages = converted(source, FakeEngine(Askew(lines, angle)))

    assert pages == [f"งบประมาณแยกตามปี\n\n{BUDGET_REFERENCE}"]


@pytest.mark.parametrize("turn", [90, 270])
def test_a_table_printed_sideways_comes_out_as_a_table_once_the_page_is_turned(turn: Literal[90, 270]) -> None:
    pages = converted(pdf(scanned(PRICE_SCHEDULE, seed=1, sideways=turn)), FakeEngine(Sideways(PRICE_SCHEDULE, turn)))

    assert pages == [PRICE_SCHEDULE_REFERENCE]


# OCR pages that are not scans: rendered from the PDF, whose rules are in the image too

@pytest.mark.parametrize("keep_images", [False, True], ids=["images read", "images kept"])
@pytest.mark.parametrize("drawn", [False, True], ids=["text layer that cannot be trusted", "text drawn as shapes"])
def test_a_ruled_table_on_an_ocr_page_that_is_not_a_scan_becomes_a_table(drawn: bool, keep_images: bool) -> None:
    # Kept images keep scans only: these pages are still read.
    lines: list[str | Grid] = ["ผู้ให้ทุนจะจ่ายเงินเป็นสามงวด", PAYMENT_SCHEDULE, "งบประมาณแยกตามปี", BUDGET]
    source = pdf(Drawn(lines)) if drawn else remapped(pdf(lines), KAR_AS_KAM)

    result = convert(source, ocr=FakeEngine(lines), keep_images=keep_images)

    assert [page.kind for page in result.summary.pages] == ["ocr"]
    assert page_texts(result.output.decode("utf-8")) == [
        f"ผู้ให้ทุนจะจ่ายเงินเป็นสามงวด\n\n{PAYMENT_SCHEDULE_REFERENCE}\n\nงบประมาณแยกตามปี\n\n{BUDGET_REFERENCE}"
    ]


def test_a_scanned_table_kept_as_an_image_is_not_read() -> None:
    lines: list[str | Grid] = ["ผู้ให้ทุนจะจ่ายเงินเป็นสามงวด", PAYMENT_SCHEDULE]
    engine = FakeEngine(lines)

    result = convert(pdf(scanned(lines, seed=1)), ocr=engine, keep_images=True)

    assert page_texts(result.output.decode("utf-8")) == ["[หน้าสแกน]"]
    assert engine.images == []


def test_a_note_typed_over_a_scanned_table_lands_in_the_cell_it_sits_in() -> None:
    grid = Grid(rows=(("งวดที่", "จำนวนเงิน", "หมายเหตุ"), ("๑", "50,000", ""), ("๒", "75,000", "")), widths=(80, 120, 200))
    # In the first row's empty note cell; the engine reads the note too, with a letter lost.
    note, misread_note = Styled("แก้ไขตามบันทึกแล้ว", x=276, y=TOP + 53), Styled("แกไขตามบันทึกแล้ว", x=276, y=TOP + 53)
    lines: list[str | Grid] = ["ผู้ให้ทุนจะจ่ายเงินเป็นงวด", grid]

    pages = converted(pdf(Scan(lines, overlay=[note], dpi=200, angle=0.4, noise=6, seed=1)), FakeEngine([*lines, misread_note]))

    assert pages == [
        "ผู้ให้ทุนจะจ่ายเงินเป็นงวด\n\n"
        "| งวดที่ | จำนวนเงิน | หมายเหตุ |\n"
        "| --- | --- | --- |\n"
        "| ๑ | 50,000 | แก้ไขตามบันทึกแล้ว |\n"
        "| ๒ | 75,000 |  |"
    ]


def test_a_table_right_under_two_columns_does_not_stop_them_being_read_one_after_the_other() -> None:
    # The table starts a line under the columns and reaches across their gutter: taken for text,
    # its cells would close the gutter, and the page would be read across.
    table = Grid(
        rows=(("หมวด", "รายละเอียดค่าใช้จ่ายของโครงการ"), ("ค่าตอบแทน", "ค่าตอบแทนผู้วิจัยและผู้ช่วยวิจัย")),
        widths=(150, 306),
        y=TOP + 5 * LINE_HEIGHT,
    )
    lines: list[str | Styled | Grid] = [*two_columns(THAI_LEFT, THAI_RIGHT, y=TOP), table]

    [page] = markdown_pages(lines, lines)

    assert page == "\n\n".join(
        [
            "".join(THAI_LEFT),
            "".join(THAI_RIGHT),
            "| หมวด | รายละเอียดค่าใช้จ่ายของโครงการ |\n| --- | --- |\n| ค่าตอบแทน | ค่าตอบแทนผู้วิจัยและผู้ช่วยวิจัย |",
        ]
    )


def test_a_table_in_a_column_stays_whole_and_the_columns_are_read_one_after_the_other() -> None:
    # The left column holds a table; the right column runs on beside it. The table's own short
    # cells, taken for text, would part the left column in three, and the page would be read across.
    above, below = THAI_LEFT[:2], THAI_LEFT[2:]
    right = [*THAI_RIGHT, *THAI_LEFT[:4]]
    table = Grid(rows=(("ปี", "งบประมาณ"), ("2568", "50,000")), widths=(90, 110), y=TOP + 3 * LINE_HEIGHT)
    lines: list[str | Styled | Grid] = [
        *(Styled(text, size=12, y=TOP + number * LINE_HEIGHT) for number, text in enumerate(above)),
        table,
        *(Styled(text, size=12, y=TOP + (6 + number) * LINE_HEIGHT) for number, text in enumerate(below)),
        *(Styled(text, size=12, x=300, y=TOP + number * LINE_HEIGHT) for number, text in enumerate(right)),
    ]

    [page] = markdown_pages(lines, lines)

    assert page == "\n\n".join(["".join(above), "| ปี | งบประมาณ |\n| --- | --- |\n| 2568 | 50,000 |", "".join(below), "".join(right)])


def test_a_table_in_the_right_column_is_read_in_that_column_where_it_sits() -> None:
    # The left column's second paragraph starts below the table's top, but beside it.
    table = Grid(rows=(("ปี", "งบประมาณ"), ("2568", "50,000")), widths=(90, 110), x=300, y=TOP + 3 * LINE_HEIGHT)
    left = [THAI_LEFT[:2], THAI_LEFT[2:]]
    above, below = THAI_RIGHT[:2], [*THAI_RIGHT[2:], *THAI_LEFT[:3]]
    lines: list[str | Styled | Grid] = [
        *(Styled(text, size=12, y=TOP + number * LINE_HEIGHT) for number, text in enumerate(left[0])),
        *(Styled(text, size=12, y=TOP + (3 + number) * LINE_HEIGHT) for number, text in enumerate(left[1])),
        *(Styled(text, size=12, x=300, y=TOP + number * LINE_HEIGHT) for number, text in enumerate(above)),
        table,
        *(Styled(text, size=12, x=300, y=TOP + (6 + number) * LINE_HEIGHT) for number, text in enumerate(below)),
    ]

    [page] = markdown_pages(lines, lines)

    assert page == "\n\n".join(
        ["".join(left[0]), "".join(left[1]), "".join(above), "| ปี | งบประมาณ |\n| --- | --- |\n| 2568 | 50,000 |", "".join(below)]
    )


# Rules that do not make a table


def test_a_frame_around_a_paragraph_on_a_scan_is_boxed_text_not_a_table() -> None:
    notice = Grid(rows=((Cell("ผู้รับทุนต้องส่งรายงานความก้าวหน้า\nทุกหกเดือนนับแต่วันลงนาม\nในสัญญาฉบับนี้"),),), widths=(400,))

    pages = markdown_pages([notice], [notice])

    assert pages == ["ผู้รับทุนต้องส่งรายงานความก้าวหน้าทุกหกเดือนนับแต่วันลงนามในสัญญาฉบับนี้"]


def test_a_ruled_row_with_no_ruled_rows_under_it_is_read_as_lines() -> None:
    # Only the header is boxed; whether such a table is incomplete is told elsewhere (ticket 08).
    header = Grid(rows=(("ชื่อโครงการ", "งบประมาณ", "ระยะเวลา"),), widths=(180, 120, 120))
    rows = [
        Styled(text, x=x, y=y)
        for y, row in ((170, ("ระบบติดตามงาน", "1,200,000", "12 เดือน")), (192, ("ระบบจัดเก็บเอกสาร", "800,000", "6 เดือน")))
        for x, text in zip((76, 256, 376), row)
    ]
    lines: list[str | Styled | Grid] = [header, *rows]

    pages = markdown_pages(lines, lines)

    assert pages == ["ชื่อโครงการ งบประมาณ ระยะเวลา\n\nระบบติดตามงาน 1,200,000 12 เดือน\n\nระบบจัดเก็บเอกสาร 800,000 6 เดือน"]


AFTER_THE_PICTURE = TOP + LINE_HEIGHT - FONT_SIZE + 200 + LINE_HEIGHT  # the baseline below a picture 200 pt tall


@pytest.mark.parametrize(
    "marking",
    [
        Picture("dark photo", 300, 200),
        Picture("stamp", 200, 200),
        Styled("ลงชื่อ ____________________________________ ผู้ให้ทุน"),
    ],
    ids=["a dark photo", "a stamp", "an underline"],
)
def test_a_marking_on_a_scan_that_is_not_a_table_makes_none(marking: Picture | Styled) -> None:
    after = Styled("ผู้รับทุนต้องส่งรายงานทุกหกเดือน", y=AFTER_THE_PICTURE)
    read = [Styled("หน้าที่มีภาพ"), *([] if isinstance(marking, Picture) else [marking]), after]

    [page] = markdown_pages([read[0], marking, after], read)

    assert "|" not in page and "<table>" not in page
    assert [line.text for line in read if line.text not in page] == []


def test_a_table_drawn_inside_a_cell_of_another_is_part_of_that_cell() -> None:
    # As on text pages, the inner grid is dropped and its text goes to the cell around it.
    outer = Grid(rows=(("หัวข้อ", "รายละเอียด"), ("แผนงาน", "\n\n\n")), widths=(120, 300))
    inner = Grid(rows=(("ปี", "งบ"), ("1", "100")), widths=(80, 80), x=220, y=TOP + 34)
    lines: list[str | Grid] = [outer, inner]

    pages = markdown_pages(lines, lines)

    assert pages == ["| หัวข้อ | รายละเอียด |\n| --- | --- |\n| แผนงาน | ปี งบ<br>1 100 |"]


def test_rules_that_leave_a_space_no_cell_could_be_make_no_table() -> None:
    # Three cells are left unruled, so the rules around them close off an L: it cannot be told
    # which of them the text in it belongs to, so the rows are read as lines.
    def cell(row: int, column: int) -> Cell:
        return Cell(f"{row}{column}", boxed=(row, column) not in {(2, 2), (2, 3), (3, 2)})

    grid = Grid(rows=tuple(tuple(cell(row, column) for column in range(1, 5)) for row in range(1, 5)), widths=(90,) * 4)

    pages = markdown_pages([grid], [grid])

    assert pages == ["11 12 13 14\n\n21 22 23 24\n\n31 32 33 34\n\n41 42 43 44"]


def test_a_ruled_header_box_repeated_at_the_top_of_scans_is_page_furniture() -> None:
    header = Grid(rows=(("สัญญาเลขที่ T-001", "ฉบับลงนาม"), ("โครงการพัฒนาระบบ", "เอกสารลับ")), widths=(200, 150), y=36)
    pages: list[list[str | Styled | Grid]] = [
        [header, Styled("เนื้อหาหน้าแรกของสัญญา", y=140)],
        [header, Styled("เนื้อหาหน้าที่สองของสัญญา", y=140)],
    ]

    result = converted(pdf(*(scanned(page, seed=1) for page in pages)), FakeEngine(*pages))

    assert result == ["เนื้อหาหน้าแรกของสัญญา", "เนื้อหาหน้าที่สองของสัญญา"]
