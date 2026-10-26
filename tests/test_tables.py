"""Ruled tables on text pages come out as tables, with Thai text in each cell intact."""

from typing import Literal

import pytest
from markdown_reader import page_texts
from pdf_builder import Cell, Grid, Line, Spaced, Styled, pdf

from pdf_to_doc import convert


def markdown_pages(*pages: list[Line]) -> list[str]:
    return page_texts(convert(pdf(*pages)).output.decode("utf-8"))


def test_a_ruled_table_becomes_a_markdown_table_between_the_text_around_it() -> None:
    grid = Grid(rows=(("งวดที่", "จำนวนเงิน"), ("๑", "50,000"), ("๒", "75,000")), widths=(150, 150))

    pages = markdown_pages(["ผู้ให้ทุนจะจ่ายเงินเป็นงวด", grid, "ตามเงื่อนไขในสัญญา"])

    assert pages == [
        "ผู้ให้ทุนจะจ่ายเงินเป็นงวด\n\n"
        "| งวดที่ | จำนวนเงิน |\n"
        "| --- | --- |\n"
        "| ๑ | 50,000 |\n"
        "| ๒ | 75,000 |\n\n"
        "ตามเงื่อนไขในสัญญา"
    ]


def test_thai_vowels_and_tone_marks_inside_cells_are_intact() -> None:
    grid = Grid(rows=(("ผู้รับทุน", "หน้าที่"), ("นักวิจัยหลัก", "ดำเนินงานตามแผนที่กำหนด")), widths=(120, 220))

    assert markdown_pages([grid]) == [
        "| ผู้รับทุน | หน้าที่ |\n| --- | --- |\n| นักวิจัยหลัก | ดำเนินงานตามแผนที่กำหนด |"
    ]


def test_merged_cells_make_an_html_table_with_spans() -> None:
    grid = Grid(
        rows=(
            (Cell("รายการ", rowspan=2), Cell("งบประมาณ", colspan=2)),
            ("ปีที่ ๑", "ปีที่ ๒"),
            ("ค่าตอบแทน", "100,000", "120,000"),
        ),
        widths=(150, 100, 100),
    )

    assert markdown_pages([grid]) == [
        "<table>\n"
        '<tr><td rowspan="2">รายการ</td><td colspan="2">งบประมาณ</td></tr>\n'
        "<tr><td>ปีที่ ๑</td><td>ปีที่ ๒</td></tr>\n"
        "<tr><td>ค่าตอบแทน</td><td>100,000</td><td>120,000</td></tr>\n"
        "</table>"
    ]


def test_text_wrapped_inside_a_cell_is_rejoined_with_the_thai_rules() -> None:
    # As Word wraps it: the first line fills the cell, and the next word would not fit after it.
    grid = Grid(rows=(("ขั้นตอน", "รายละเอียด"), ("๑", "ส่งรายงานความก้าวหน้า\nทุกหกเดือน")), widths=(80, 170))

    assert markdown_pages([grid]) == [
        "| ขั้นตอน | รายละเอียด |\n| --- | --- |\n| ๑ | ส่งรายงานความก้าวหน้าทุกหกเดือน |"
    ]


# A cell holding several printed lines: sub-rows, stacked items, or one wrapped sentence

STACKED_ITEMS = "ค่าวัสดุสำนักงาน\nค่าถ่ายเอกสาร\nค่าไปรษณีย์"


def test_stacked_items_beside_their_amounts_become_sub_rows() -> None:
    grid = Grid(
        rows=(("หมวด", "รายการ", "จำนวนเงิน"), ("ค่าดำเนินงาน", STACKED_ITEMS, "12,000\n3,500\n1,200")),
        widths=(110, 210, 100),
    )

    assert markdown_pages([grid]) == [
        "<table>\n"
        "<tr><td>หมวด</td><td>รายการ</td><td>จำนวนเงิน</td></tr>\n"
        '<tr><td rowspan="3">ค่าดำเนินงาน</td><td>ค่าวัสดุสำนักงาน</td><td>12,000</td></tr>\n'
        "<tr><td>ค่าถ่ายเอกสาร</td><td>3,500</td></tr>\n"
        "<tr><td>ค่าไปรษณีย์</td><td>1,200</td></tr>\n"
        "</table>"
    ]


def test_amounts_set_flush_right_beside_stacked_items_become_sub_rows_too() -> None:
    grid = Grid(
        rows=(("หมวด", "รายการ", "จำนวนเงิน"), ("ค่าดำเนินงาน", STACKED_ITEMS, Cell("12,000\n3,500\n1,200", align="right"))),
        widths=(110, 210, 100),
    )

    [page] = markdown_pages([grid])

    assert '<tr><td rowspan="3">ค่าดำเนินงาน</td><td>ค่าวัสดุสำนักงาน</td><td>12,000</td></tr>' in page
    assert "<tr><td>ค่าไปรษณีย์</td><td>1,200</td></tr>" in page


@pytest.mark.parametrize("align", ["left", "right", "centre"])
def test_short_items_keep_their_breaks_and_a_wrapped_sentence_joins_however_the_cell_is_aligned(
    align: Literal["left", "right", "centre"],
) -> None:
    grid = Grid(
        rows=(
            ("รายการ", "รายละเอียด"),
            (Cell("เครื่องคอมพิวเตอร์\nเครื่องพิมพ์", align=align), Cell("ส่งรายงานความก้าวหน้า\nทุกหกเดือน", align=align)),
        ),
        widths=(210, 170),
    )

    assert markdown_pages([grid]) == [
        "| รายการ | รายละเอียด |\n| --- | --- |\n| เครื่องคอมพิวเตอร์<br>เครื่องพิมพ์ | ส่งรายงานความก้าวหน้าทุกหกเดือน |"
    ]


def test_short_items_stacked_beside_one_total_keep_their_line_breaks() -> None:
    grid = Grid(rows=(("หมวด", "รายการ", "จำนวนเงิน"), ("ค่าครุภัณฑ์", "เครื่องคอมพิวเตอร์\nเครื่องพิมพ์", "53,900")), widths=(110, 210, 100))

    assert markdown_pages([grid]) == [
        "| หมวด | รายการ | จำนวนเงิน |\n| --- | --- | --- |\n| ค่าครุภัณฑ์ | เครื่องคอมพิวเตอร์<br>เครื่องพิมพ์ | 53,900 |"
    ]


def test_two_sentences_wrapping_over_as_many_lines_side_by_side_are_not_sub_rows() -> None:
    # Both cells' lines line up, but each first line fills its cell: they are wrapped sentences.
    grid = Grid(
        rows=(
            ("งวดที่", "งาน", "ค่าใช้จ่าย"),
            ("๑", "ส่งรายงานความก้าวหน้า\nทุกหกเดือน", "ค่าเช่ารถและค่าน้ำมันเชื้อเพลิง\nสำหรับการลงพื้นที่"),
        ),
        widths=(50, 170, 210),
    )

    assert markdown_pages([grid]) == [
        "| งวดที่ | งาน | ค่าใช้จ่าย |\n| --- | --- | --- |\n"
        "| ๑ | ส่งรายงานความก้าวหน้าทุกหกเดือน | ค่าเช่ารถและค่าน้ำมันเชื้อเพลิงสำหรับการลงพื้นที่ |"
    ]


def test_items_that_do_not_line_up_across_cells_are_not_sub_rows() -> None:
    # The second amount sits a line lower than the second item.
    grid = Grid(rows=(("รายการ", "จำนวนเงิน"), ("ค่าวัสดุ\nค่าเดินทาง", "1,000\n\n2,000")), widths=(210, 100))

    assert markdown_pages([grid]) == ["| รายการ | จำนวนเงิน |\n| --- | --- |\n| ค่าวัสดุ<br>ค่าเดินทาง | 1,000<br>2,000 |"]


def test_a_cell_merged_down_into_a_row_of_sub_rows_spans_them_all() -> None:
    grid = Grid(
        rows=((Cell("หมวด", rowspan=2), "รายการ", "จำนวนเงิน"), ("ค่าวัสดุ\nค่าเดินทาง", "1,000\n2,000")),
        widths=(110, 210, 100),
    )

    assert markdown_pages([grid]) == [
        "<table>\n"
        '<tr><td rowspan="3">หมวด</td><td>รายการ</td><td>จำนวนเงิน</td></tr>\n'
        "<tr><td>ค่าวัสดุ</td><td>1,000</td></tr>\n"
        "<tr><td>ค่าเดินทาง</td><td>2,000</td></tr>\n"
        "</table>"
    ]


def test_columns_set_out_without_ruling_are_not_a_table() -> None:
    rows: list[Line] = [
        Spaced(("ภาคผนวก 1", "เงื่อนไขของสัญญา", "จำนวน 7 หน้า"), gap=40),
        Spaced(("ภาคผนวก 2", "ขอบเขตของงาน", "จำนวน 54 หน้า"), gap=40),
    ]

    assert markdown_pages(rows) == ["ภาคผนวก 1 เงื่อนไขของสัญญา จำนวน 7 หน้า\n\nภาคผนวก 2 ขอบเขตของงาน จำนวน 54 หน้า"]


def test_a_vertical_bar_inside_a_cell_does_not_break_the_markdown_table() -> None:
    grid = Grid(rows=(("รหัส", "ชื่อ"), ("A|B", "ทดสอบ")), widths=(100, 100))

    assert markdown_pages([grid]) == ["| รหัส | ชื่อ |\n| --- | --- |\n" + r"| A\|B | ทดสอบ |"]


# Found in review: every character must come out exactly once


def test_text_in_a_table_row_but_outside_every_cell_is_kept_once() -> None:
    grid = Grid(
        rows=(
            ("รายการ", "จำนวนเงิน", Cell("หมายเหตุ", boxed=False)),
            ("ค่าเดินทาง", "5,000", Cell("เบิกได้", boxed=False)),
        ),
        widths=(120, 100, 100),
    )

    [text] = markdown_pages([grid])

    for word in ("รายการ", "จำนวนเงิน", "หมายเหตุ", "ค่าเดินทาง", "5,000", "เบิกได้"):
        assert text.count(word) == 1, word


def test_text_running_past_the_last_cell_stays_whole_in_that_cell() -> None:
    grid = Grid(rows=(("รายการ", "รวม"), ("ค่าใช้จ่าย", "ค่าใช้จ่ายรวมทั้งสิ้น")), widths=(100, 60))

    assert markdown_pages([grid]) == ["| รายการ | รวม |\n| --- | --- |\n| ค่าใช้จ่าย | ค่าใช้จ่ายรวมทั้งสิ้น |"]


def test_a_word_spilling_into_the_next_cell_is_not_split() -> None:
    grid = Grid(rows=(("รายการ", "จำนวน"), ("ค่าใช้จ่ายทั้งหมดของโครงการ", "5")), widths=(60, 160))

    [text] = markdown_pages([grid])

    assert text.count("ค่าใช้จ่ายทั้งหมดของโครงการ") == 1


def test_a_missing_box_leaves_an_empty_cell_so_columns_stay_aligned() -> None:
    grid = Grid(rows=(("ก", "ข", "ค"), ("1", Cell("", boxed=False), "3")), widths=(80, 80, 80))

    assert markdown_pages([grid]) == ["| ก | ข | ค |\n| --- | --- | --- |\n| 1 |  | 3 |"]


def test_pieces_set_apart_by_tab_stops_inside_a_cell_keep_a_space() -> None:
    grid = Grid(rows=(("ตำแหน่ง", "ผู้รับทุน"), ("ผู้วิจัย", "นาย\tสมชาย\tใจดี")), widths=(100, 250))

    assert markdown_pages([grid]) == ["| ตำแหน่ง | ผู้รับทุน |\n| --- | --- |\n| ผู้วิจัย | นาย สมชาย ใจดี |"]


def test_a_ruled_header_box_repeated_at_the_top_of_pages_is_page_furniture() -> None:
    def header(counter: str) -> Grid:
        return Grid(rows=(("สัญญาเลขที่ T-001", counter),), widths=(200, 150), y=40)

    pages = markdown_pages(
        [header("หน้าที่ 1/2"), Styled("เนื้อหาหน้าแรก", y=140)],
        [header("หน้าที่ 2/2"), Styled("เนื้อหาหน้าที่สอง", y=140)],
    )

    assert pages == ["เนื้อหาหน้าแรก", "เนื้อหาหน้าที่สอง"]
