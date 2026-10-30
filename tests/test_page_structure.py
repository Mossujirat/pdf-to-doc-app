"""Page structure on text pages: page furniture removed, headings and lists kept."""

import pymupdf
import pytest
from markdown_reader import page_texts
from pdf_builder import FONT_SIZE, LEFT, SARABUN, Line, Spaced, Styled, pdf

from pdf_to_doc import convert

TOP_EDGE = 40
BOTTOM_EDGE = 800


def markdown_pages(*pages: list[Line]) -> list[str]:
    return page_texts(convert(pdf(*pages)).output.decode("utf-8"))


# Page furniture


def test_a_line_repeated_at_the_top_of_every_page_is_removed() -> None:
    stamp = Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=TOP_EDGE)

    pages = markdown_pages([stamp, Styled("เนื้อหาหน้าแรก", y=100)], [stamp, Styled("เนื้อหาหน้าที่สอง", y=100)])

    assert pages == ["เนื้อหาหน้าแรก", "เนื้อหาหน้าที่สอง"]


def test_page_counters_at_the_bottom_are_removed_even_when_numbering_restarts() -> None:
    def footer(text: str) -> Styled:
        return Styled(text, size=14, y=BOTTOM_EDGE)

    pages = markdown_pages(
        [Styled("สัญญาหน้าแรก", y=100), footer("สัญญาเลขที่ T-001 หน้าที่ 1/2")],
        [Styled("สัญญาหน้าที่สอง", y=100), footer("สัญญาเลขที่ T-001 หน้าที่ 2/2")],
        [Styled("ภาคผนวกหน้าแรก", y=100), footer("หน้าที่ ๑/๑")],
        [Styled("ภาคผนวกที่สอง", y=100), footer("- 2 -")],
    )

    assert pages == ["สัญญาหน้าแรก", "สัญญาหน้าที่สอง", "ภาคผนวกหน้าแรก", "ภาคผนวกที่สอง"]


def test_text_near_the_edge_of_only_one_page_is_kept() -> None:
    pages = markdown_pages(
        [Styled("เนื้อหาหน้าแรก", y=100), Styled("หมายเหตุท้ายหน้า", size=14, y=BOTTOM_EDGE)],
        [Styled("เนื้อหาหน้าที่สอง", y=100)],
    )

    assert pages == ["เนื้อหาหน้าแรก\n\nหมายเหตุท้ายหน้า", "เนื้อหาหน้าที่สอง"]


# Headings


def test_larger_text_becomes_headings_whose_level_follows_the_size() -> None:
    pages = markdown_pages(
        [
            Styled("สัญญาให้ทุนโครงการ", size=24),
            Styled("ข้อกำหนดทั่วไป", size=20),
            "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน",
            Styled("การจ่ายเงิน", size=20),
            "ผู้ให้ทุนจะจ่ายเงินเป็นงวด",
        ]
    )

    assert pages == [
        "# สัญญาให้ทุนโครงการ\n\n"
        "## ข้อกำหนดทั่วไป\n\n"
        "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน\n\n"
        "## การจ่ายเงิน\n\n"
        "ผู้ให้ทุนจะจ่ายเงินเป็นงวด"
    ]


def test_a_bold_line_standing_alone_at_body_size_is_the_next_heading_level_down() -> None:
    pages = markdown_pages(
        [
            Styled("สัญญาให้ทุนโครงการ", size=20),
            "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน",
            "",
            Styled("ข้อ ๑ ขอบเขตของงาน", bold=True),
            "",
            "ผู้รับทุนจะดำเนินงานตามแผน",
        ]
    )

    assert pages == [
        "# สัญญาให้ทุนโครงการ\n\n"
        "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน\n\n"
        "## ข้อ ๑ ขอบเขตของงาน\n\n"
        "ผู้รับทุนจะดำเนินงานตามแผน"
    ]


def test_bold_words_inside_a_paragraph_do_not_make_it_a_heading() -> None:
    pages = markdown_pages(
        [
            "ผู้ให้ทุนตกลงให้ทุนแก่",
            Styled("หน่วยงานผู้ให้ทุนตัวอย่าง", bold=True),
            "ตามเงื่อนไขในสัญญานี้",
        ]
    )

    assert pages == ["ผู้ให้ทุนตกลงให้ทุนแก่หน่วยงานผู้ให้ทุนตัวอย่างตามเงื่อนไขในสัญญานี้"]


# Lists


def test_numbered_lines_become_list_items_that_keep_their_own_numbers() -> None:
    pages = markdown_pages(
        [
            "เอกสารแนบท้ายสัญญามีดังนี้",
            "1. เงื่อนไขของสัญญา",
            "2. ขอบเขตของการดำเนินงาน",
            "๓. ข้อตกลงด้านการเงิน",
            "(4) แบบรายงาน",
        ]
    )

    assert pages == [
        "เอกสารแนบท้ายสัญญามีดังนี้\n\n"
        "- 1. เงื่อนไขของสัญญา\n"
        "- 2. ขอบเขตของการดำเนินงาน\n"
        "- ๓. ข้อตกลงด้านการเงิน\n"
        "- (4) แบบรายงาน"
    ]


def test_a_list_item_that_wraps_onto_the_next_line_stays_one_item() -> None:
    pages = markdown_pages(["1. ผู้รับทุนต้องส่งรายงานความก้าว", "หน้าทุกหกเดือน", "2. ผู้ให้ทุนจะตรวจรายงาน"])

    assert pages == ["- 1. ผู้รับทุนต้องส่งรายงานความก้าวหน้าทุกหกเดือน\n- 2. ผู้ให้ทุนจะตรวจรายงาน"]


def test_bulleted_lines_become_list_items() -> None:
    pages = markdown_pages(["• รายงานความก้าวหน้า", "• รายงานฉบับสมบูรณ์"])

    assert pages == ["- รายงานความก้าวหน้า\n- รายงานฉบับสมบูรณ์"]


# Paragraphs


def test_a_first_line_indent_starts_a_new_paragraph() -> None:
    pages = markdown_pages(
        ["ย่อหน้าแรกจบที่บรรทัดนี้", Styled("ย่อหน้าที่สองเริ่มด้วยการย่อเข้า", x=108), "และต่อในบรรทัดถัดไป"]
    )

    assert pages == ["ย่อหน้าแรกจบที่บรรทัดนี้\n\nย่อหน้าที่สองเริ่มด้วยการย่อเข้าและต่อในบรรทัดถัดไป"]


def test_centred_lines_of_one_title_read_as_one_paragraph() -> None:
    pages = markdown_pages(
        [
            Styled("ภายใต้แผนงานสร้างเศรษฐกิจฐานชีวภาพ (Bio-Circular-Green", centered=True),
            Styled("Economy: BCG) ด้านพลังงานสะอาด", centered=True),
        ]
    )

    assert pages == ["ภายใต้แผนงานสร้างเศรษฐกิจฐานชีวภาพ (Bio-Circular-Green Economy: BCG) ด้านพลังงานสะอาด"]


def test_rows_set_out_in_columns_stay_on_separate_lines() -> None:
    pages = markdown_pages(
        [
            Spaced(("ภาคผนวก 1", "เงื่อนไขของสัญญา", "จำนวน 7 หน้า"), gap=40),
            Spaced(("ภาคผนวก 2", "ขอบเขตของงาน", "จำนวน 54 หน้า"), gap=40),
        ]
    )

    assert pages == ["ภาคผนวก 1 เงื่อนไขของสัญญา จำนวน 7 หน้า\n\nภาคผนวก 2 ขอบเขตของงาน จำนวน 54 หน้า"]


def test_a_row_without_letters_or_numbers_near_the_edge_is_content_not_furniture() -> None:
    # A table cell of dashes that happens to sit low on two pages.
    pages = markdown_pages(
        [Styled("งบประมาณหน้าแรก", y=100), Styled("- - -", y=BOTTOM_EDGE)],
        [Styled("งบประมาณหน้าที่สอง", y=100), Styled("- - -", y=BOTTOM_EDGE)],
    )

    assert pages == ["งบประมาณหน้าแรก\n\n- - -", "งบประมาณหน้าที่สอง\n\n- - -"]


def test_a_bold_row_set_out_in_columns_is_a_table_row_not_a_heading() -> None:
    pages = markdown_pages([Spaced(("รายการ", "งบประมาณ", "หมายเหตุ"), gap=40, bold=True), "", "ค่าตอบแทนนักวิจัย"])

    assert pages == ["รายการ งบประมาณ หมายเหตุ\n\nค่าตอบแทนนักวิจัย"]


# Page furniture: false positives found in review


def test_a_sentence_containing_the_word_for_page_is_not_a_page_counter() -> None:
    pages = markdown_pages(
        [Styled("เนื้อหาหน้าแรก", y=100), Styled("ผู้รับทุนต้องแจ้งล่วงหน้า 30 วัน", y=BOTTOM_EDGE)],
        [Styled("เนื้อหาหน้าที่สอง", y=100), Styled("ผู้รับทุนต้องแจ้งล่วงหน้า 15 วัน", y=BOTTOM_EDGE)],
    )

    assert pages == [
        "เนื้อหาหน้าแรก\n\nผู้รับทุนต้องแจ้งล่วงหน้า 30 วัน",
        "เนื้อหาหน้าที่สอง\n\nผู้รับทุนต้องแจ้งล่วงหน้า 15 วัน",
    ]


def test_numbers_near_the_edge_that_do_not_follow_the_pages_are_kept() -> None:
    pages = markdown_pages(
        [Styled("ยอดรวมหน้าแรก", y=100), Styled("500", size=14, y=BOTTOM_EDGE)],
        [Styled("ยอดรวมหน้าที่สอง", y=100), Styled("1200", size=14, y=BOTTOM_EDGE)],
    )

    assert pages == ["ยอดรวมหน้าแรก\n\n500", "ยอดรวมหน้าที่สอง\n\n1200"]


def test_page_numbers_that_follow_the_pages_are_removed() -> None:
    pages = markdown_pages(
        [Styled("ปกของเอกสาร", y=100)],
        [Styled("บทที่หนึ่ง", y=100), Styled("1", size=14, y=BOTTOM_EDGE)],
        [Styled("บทที่สอง", y=100), Styled("2", size=14, y=BOTTOM_EDGE)],
    )

    assert pages == ["ปกของเอกสาร", "บทที่หนึ่ง", "บทที่สอง"]


def test_the_same_line_at_the_bottom_of_one_page_and_the_top_of_the_next_is_kept() -> None:
    sentence = "ผู้ให้ทุนสงวนสิทธิ์ในการเปลี่ยนแปลง"
    pages = markdown_pages(
        [Styled("เนื้อหาหน้าแรก", y=100), Styled(sentence, y=BOTTOM_EDGE)],
        [Styled(sentence, y=TOP_EDGE), Styled("เนื้อหาหน้าที่สอง", y=100)],
    )

    assert pages == [f"เนื้อหาหน้าแรก\n\n{sentence}", f"{sentence}\n\nเนื้อหาหน้าที่สอง"]


def test_a_header_whose_top_is_inside_the_edge_band_is_removed() -> None:
    header = Styled("รายงานความก้าวหน้า ฉบับที่ 1", size=14, y=95)

    pages = markdown_pages([header, Styled("เนื้อหาหน้าแรก", y=140)], [header, Styled("เนื้อหาหน้าที่สอง", y=140)])

    assert pages == ["เนื้อหาหน้าแรก", "เนื้อหาหน้าที่สอง"]


def test_a_row_that_is_only_a_page_counter_is_removed_even_on_a_single_page() -> None:
    pages = markdown_pages(
        [Styled("ภาคผนวกที่มีหน้าเดียว", y=100), Styled("หน้าที่ ๑/๑", size=14, y=BOTTOM_EDGE)],
    )

    assert pages == ["ภาคผนวกที่มีหน้าเดียว"]


# Lists: false positives found in review

FULL_LINE = "ผู้ให้ทุนตกลงจ่ายเงินสนับสนุนโครงการวิจัยนี้รวมทั้งสิ้นเป็นเงินจำนวน"


def test_a_wrapped_line_that_starts_with_a_number_carries_on_the_sentence() -> None:
    # The line before runs the full width, so the sentence wraps rather than ends.
    assert markdown_pages([FULL_LINE, "2.5 ล้านบาท ภายในปีนี้"]) == [f"{FULL_LINE} 2.5 ล้านบาท ภายในปีนี้"]
    assert markdown_pages([FULL_LINE, "09.00 น. ของวันทำการ"]) == [f"{FULL_LINE} 09.00 น. ของวันทำการ"]


def test_a_list_item_whose_last_line_runs_full_is_followed_by_the_next_item() -> None:
    # Justified clauses of a real contract often end on a full line.
    pages = markdown_pages([f"1. {FULL_LINE}", "2. ผู้ให้ทุนจะตรวจรายงาน"])

    assert pages == [f"- 1. {FULL_LINE}\n- 2. ผู้ให้ทุนจะตรวจรายงาน"]


@pytest.mark.parametrize(
    ("reference", "number"), [("ตามข้อ", "4.2 ของสัญญานี้"), (" Clause", "4.2 of this agreement")], ids=["ตามข้อ", "Clause"]
)
def test_a_clause_number_wrapped_after_its_reference_stays_in_the_list_item(reference: str, number: str) -> None:
    # As found in a contract exported from Word: the clause's line runs the full width.
    pages = markdown_pages([f"1. {FULL_LINE}{reference}", number, "2. ผู้ให้ทุนจะตรวจรายงาน"])

    assert pages == [f"- 1. {FULL_LINE}{reference} {number}\n- 2. ผู้ให้ทุนจะตรวจรายงาน"]


def test_a_reference_whose_line_stops_short_of_the_next_word_carries_on_the_sentence() -> None:
    # The line ends two font sizes short of the margin, and the next line's first word, with no
    # space in it, is far wider: Word wrapped it.
    reference = "ค่าปรับให้เป็นไปตามข้อ"
    width = pymupdf.Font(fontfile=str(SARABUN)).text_length(reference, fontsize=FONT_SIZE)
    right_margin = pymupdf.paper_size("a4")[0] - LEFT
    lines: list[Line] = [
        Styled(reference, x=right_margin - 2 * FONT_SIZE - width),
        Styled("4.2ของสัญญานี้ฉบับนี้"),
        "2. ผู้ให้ทุนจะตรวจรายงาน",
    ]

    assert markdown_pages(lines) == [f"{reference} 4.2ของสัญญานี้ฉบับนี้\n\n- 2. ผู้ให้ทุนจะตรวจรายงาน"]


def test_a_short_heading_that_ends_in_a_reference_word_is_followed_by_its_list() -> None:
    # Its line did not wrap: the number after it would have fit.
    pages = markdown_pages(["ภาคผนวก", "1. แบบฟอร์มรายงาน"])

    assert pages == ["ภาคผนวก\n\n- 1. แบบฟอร์มรายงาน"]


@pytest.mark.parametrize(
    "ending",
    [
        "ทุกข้อ",  # every clause, which points at none
        "ล่วงหน้า",  # ends in "หน้า", page, but refers to nothing
    ],
)
def test_a_list_item_ending_in_a_word_that_refers_to_no_number_is_followed_by_the_next_item(ending: str) -> None:
    pages = markdown_pages([f"1. {FULL_LINE}{ending}", "2. ผู้ให้ทุนจะตรวจรายงาน"])

    assert pages == [f"- 1. {FULL_LINE}{ending}\n- 2. ผู้ให้ทุนจะตรวจรายงาน"]


def test_thai_abbreviations_with_a_full_stop_are_not_list_items() -> None:
    pages = markdown_pages(["ที่อยู่ เลขที่ 99 หมู่ 1", "ต. บางพลี อ. บางพลี จ. สมุทรปราการ"])

    assert pages == ["ที่อยู่ เลขที่ 99 หมู่ 1 ต. บางพลี อ. บางพลี จ. สมุทรปราการ"]


def test_a_list_item_continued_under_a_hanging_indent_stays_one_item() -> None:
    pages = markdown_pages(
        ["1. ผู้รับทุนต้องส่งรายงานความก้าว", Styled("หน้าทุกหกเดือน", x=90), "2. ผู้ให้ทุนจะตรวจรายงาน"]
    )

    assert pages == ["- 1. ผู้รับทุนต้องส่งรายงานความก้าวหน้าทุกหกเดือน\n- 2. ผู้ให้ทุนจะตรวจรายงาน"]


# Headings: cases found in review


def test_headings_whose_sizes_differ_by_a_fraction_of_a_point_share_a_level() -> None:
    pages = markdown_pages(
        [
            Styled("บทที่หนึ่ง", size=20),
            "เนื้อหาของบทที่หนึ่ง",
            Styled("บทที่สอง", size=20.5),
            "เนื้อหาของบทที่สอง",
        ]
    )

    assert pages == ["# บทที่หนึ่ง\n\nเนื้อหาของบทที่หนึ่ง\n\n# บทที่สอง\n\nเนื้อหาของบทที่สอง"]


def test_a_heading_only_slightly_larger_than_the_body_is_still_a_heading() -> None:
    pages = markdown_pages([Styled("ข้อกำหนดทั่วไป", size=17), "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน"])

    assert pages == ["# ข้อกำหนดทั่วไป\n\nผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน"]


def test_a_long_paragraph_set_in_larger_type_is_not_a_heading() -> None:
    body = [
        "เนื้อหาหลักของสัญญาฉบับนี้พิมพ์ด้วยขนาดปกติ",
        "และมีหลายบรรทัดมากกว่าส่วนที่พิมพ์ด้วยตัวใหญ่",
        "เพื่อให้ขนาดปกติเป็นขนาดของเนื้อหา",
    ]
    larger = [Styled(text, size=18) for text in ("ภาคผนวกนี้พิมพ์ด้วยตัวอักษร", "ที่ใหญ่กว่าเนื้อหาหลัก", "ตลอดทั้งย่อหน้า")]
    pages = markdown_pages([*body, "", *larger])

    assert pages == ["".join(body) + "\n\nภาคผนวกนี้พิมพ์ด้วยตัวอักษรที่ใหญ่กว่าเนื้อหาหลักตลอดทั้งย่อหน้า"]


def test_a_bold_heading_that_wraps_onto_a_second_line_is_one_heading() -> None:
    pages = markdown_pages(
        [
            Styled("ข้อ ๑ ขอบเขตของงานและ", bold=True),
            Styled("ระยะเวลาดำเนินงาน", bold=True),
            "",
            "ผู้รับทุนจะดำเนินงานตามแผน",
        ]
    )

    assert pages == ["# ข้อ ๑ ขอบเขตของงานและระยะเวลาดำเนินงาน\n\nผู้รับทุนจะดำเนินงานตามแผน"]


# Paragraphs: line spacing found in review


def test_one_and_a_half_line_spacing_does_not_split_paragraphs() -> None:
    lines = ["ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน", "เพื่อดำเนินโครงการตามแผนงาน", "ที่แนบท้ายสัญญานี้"]
    spaced = [Styled(text, y=100 + 31 * index) for index, text in enumerate(lines)]
    # The next paragraph starts after a larger gap than the lines' own spacing.
    next_paragraph = Styled("ผู้รับทุนตกลงรับทุนตามเงื่อนไข", y=100 + 31 * 3 + 14)

    assert markdown_pages([*spaced, next_paragraph]) == ["".join(lines) + "\n\nผู้รับทุนตกลงรับทุนตามเงื่อนไข"]


def test_a_row_of_figures_set_out_in_columns_is_not_a_list_item() -> None:
    pages = markdown_pages(["งบประมาณรายจ่าย", Spaced(("0.00", "6,750.00", "0.00", "6,750.00"), gap=40)])

    assert pages == ["งบประมาณรายจ่าย\n\n0.00 6,750.00 0.00 6,750.00"]
