"""DOCX sources: a Word file converts to Markdown with its headings, lists, tables and
images intact, its Thai repaired, and its pages as Word last laid them out."""

from markdown_reader import page_texts
from pdf_builder import Cell
from word_builder import (
    Bulleted,
    Deleted,
    Field,
    Heading,
    Hidden,
    Image,
    Inserted,
    Item,
    Link,
    Numbered,
    NumberedHeadings,
    PageBreak,
    Rich,
    Split,
    Table,
    TextBoxes,
    WithImage,
    docx,
    document,
)

from pdf_to_doc import convert

SARA_AM = chr(0x0E33)
SARA_AA = chr(0x0E32)
NIKHAHIT = chr(0x0E4D)
MAI_EK = chr(0x0E48)
MAI_HAN_AKAT = chr(0x0E31)


def markdown_pages(source: bytes) -> list[str]:
    return page_texts(convert(source).output.decode("utf-8"))


def test_a_thai_paragraph_comes_out_as_its_text() -> None:
    assert markdown_pages(docx("สัญญาให้ทุนโครงการ")) == ["สัญญาให้ทุนโครงการ"]


def test_thai_text_is_repaired_as_text_pages_are() -> None:
    assert markdown_pages(document(f"การท{NIKHAHIT}{SARA_AA}งานร่วมกัน")) == [f"การท{SARA_AM}งานร่วมกัน"]


def test_a_tone_mark_stored_before_its_vowel_is_put_in_standard_order() -> None:
    assert markdown_pages(document(f"ท{MAI_EK}{MAI_HAN_AKAT}วไป")) == [f"ท{MAI_HAN_AKAT}{MAI_EK}วไป"]


def test_hidden_text_is_left_out() -> None:
    # Found in review: Word neither shows nor prints text formatted as hidden.
    assert markdown_pages(document(Rich(("ผู้ให้ทุน", Hidden("หมายเหตุภายใน"), "จะจ่ายเงิน")))) == ["ผู้ให้ทุนจะจ่ายเงิน"]


def test_every_text_box_in_a_group_keeps_its_text() -> None:
    # Found in review: only the first box of a group was read.
    assert markdown_pages(document(TextBoxes(("กล่องแรก", "กล่องที่สอง")))) == ["กล่องแรก\n\nกล่องที่สอง"]


def test_headings_come_from_words_heading_styles_at_their_levels() -> None:
    source = document(
        Heading("สัญญาให้ทุนโครงการ", 1), Heading("ข้อกำหนดทั่วไป", 2), "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน", Heading("ภาคผนวก", 3)
    )

    assert markdown_pages(source) == ["# สัญญาให้ทุนโครงการ\n\n## ข้อกำหนดทั่วไป\n\nผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน\n\n### ภาคผนวก"]


def test_text_deleted_with_tracked_changes_on_is_left_out_and_inserted_text_kept() -> None:
    source = document(Rich(("ผู้ให้ทุนจะจ่ายเงิน", Deleted("ภายในสามสิบวัน"), Inserted("ภายในสิบห้าวัน"), "นับแต่วันส่งงาน")))

    assert markdown_pages(source) == ["ผู้ให้ทุนจะจ่ายเงินภายในสิบห้าวันนับแต่วันส่งงาน"]


def test_a_link_shows_its_text_and_a_field_what_it_shows_not_its_code() -> None:
    source = document(Rich(("ดูรายละเอียดที่", Link("เว็บไซต์โครงการ"), " หน้า ", Field("PAGE", "3"))))

    assert markdown_pages(source) == ["ดูรายละเอียดที่เว็บไซต์โครงการ หน้า 3"]


# Lists


def test_bulleted_items_become_markdown_list_items() -> None:
    source = document("รายงานที่ต้องส่ง", Bulleted(("รายงานความก้าวหน้า", "รายงานฉบับสมบูรณ์")))

    assert markdown_pages(source) == ["รายงานที่ต้องส่ง\n\n- รายงานความก้าวหน้า\n- รายงานฉบับสมบูรณ์"]


def test_numbered_items_keep_the_numbers_word_draws() -> None:
    source = document(Numbered(("เงื่อนไขของสัญญา", "ขอบเขตของการดำเนินงาน", "ข้อตกลงด้านการเงิน")))

    assert markdown_pages(source) == ["- 1. เงื่อนไขของสัญญา\n- 2. ขอบเขตของการดำเนินงาน\n- 3. ข้อตกลงด้านการเงิน"]


def test_thai_digits_and_thai_letters_are_numbered_as_word_numbers_them() -> None:
    source = document(
        Numbered(("งวดแรก", "งวดที่สอง"), levels=(("thaiNumbers", "%1."),)),
        "และ",
        Numbered(("ผู้ให้ทุน", "ผู้รับทุน", "ผู้ประสานงาน"), levels=(("thaiLetters", "(%1)"),)),
    )

    assert markdown_pages(source) == [
        "- ๑. งวดแรก\n- ๒. งวดที่สอง\n\nและ\n\n- (ก) ผู้ให้ทุน\n- (ข) ผู้รับทุน\n- (ค) ผู้ประสานงาน"
    ]


def test_a_list_within_a_list_is_numbered_by_level() -> None:
    levels = (("decimal", "%1."), ("decimal", "%1.%2"))
    source = document(
        Numbered((Item("ขอบเขต"), Item("งานวิจัย", 1), Item("งานพัฒนา", 1), Item("ระยะเวลา"), Item("ปีแรก", 1)), levels)
    )

    assert markdown_pages(source) == ["- 1. ขอบเขต\n  - 1.1 งานวิจัย\n  - 1.2 งานพัฒนา\n- 2. ระยะเวลา\n  - 2.1 ปีแรก"]


def test_a_list_carries_on_after_a_paragraph_and_starts_again_when_word_restarts_it() -> None:
    source = document(
        Numbered(("ข้อแรก", "ข้อที่สอง")),
        "หมายเหตุระหว่างรายการ",
        Numbered(("ข้อที่สาม",), begins="carrying on"),
        "รายการชุดใหม่",
        Numbered(("ข้อแรกของชุดใหม่",), begins="starting again"),
        "อีกรายการหนึ่ง",
        Numbered(("ข้อแรกของอีกรายการ",)),
    )

    assert markdown_pages(source) == [
        "- 1. ข้อแรก\n- 2. ข้อที่สอง\n\nหมายเหตุระหว่างรายการ\n\n- 3. ข้อที่สาม\n\n"
        "รายการชุดใหม่\n\n- 1. ข้อแรกของชุดใหม่\n\nอีกรายการหนึ่ง\n\n- 1. ข้อแรกของอีกรายการ"
    ]


def test_a_deeper_level_starts_again_under_each_new_item_above_it() -> None:
    # Found in review: the third level counted on under a new first-level item.
    levels = (("decimal", "%1."), ("decimal", "%1.%2."), ("decimal", "%1.%2.%3."))
    items = (Item("ก", 0), Item("ข", 1), Item("ค", 2), Item("ง", 0), Item("จ", 2))

    assert markdown_pages(document(Numbered(items, levels))) == [
        "- 1. ก\n  - 1.1. ข\n    - 1.1.1. ค\n- 2. ง\n    - 2.1.1. จ"
    ]


def test_a_list_that_starts_again_can_redraw_its_numbers() -> None:
    # Found in review: a level redefined in the list's override was ignored.
    source = document(
        Numbered(("ข้อแรก", "ข้อที่สอง")),
        "รายการชุดใหม่",
        Numbered(("ข้อแรกของชุดใหม่",), begins="starting again", redrawn=("upperRoman", "%1)")),
    )

    assert markdown_pages(source) == ["- 1. ข้อแรก\n- 2. ข้อที่สอง\n\nรายการชุดใหม่\n\n- I) ข้อแรกของชุดใหม่"]


def test_bulleted_items_keep_their_nesting() -> None:
    source = document(Bulleted((Item("งานวิจัย"), Item("ทดลองในห้องปฏิบัติการ", 1), Item("งานพัฒนา"))))

    assert markdown_pages(source) == ["- งานวิจัย\n  - ทดลองในห้องปฏิบัติการ\n- งานพัฒนา"]


HEADINGS = (Heading("บทนำ", 1), Heading("ขอบเขต", 2), Heading("ระยะเวลา", 2), Heading("งบประมาณ", 1))


def test_headings_numbered_through_their_styles_keep_their_numbers() -> None:
    assert markdown_pages(document(NumberedHeadings(HEADINGS))) == [
        "# 1 บทนำ\n\n## 1.1 ขอบเขต\n\n## 1.2 ระยะเวลา\n\n# 2 งบประมาณ"
    ]


def test_a_heading_style_that_names_the_list_but_not_its_level_is_not_numbered() -> None:
    # Checked in real Word: the first level names the style Heading 1, so a Heading 2
    # counted at that level shows no number, and does not count.
    assert markdown_pages(document(NumberedHeadings(HEADINGS, levels_in_styles=False))) == [
        "# 1 บทนำ\n\n## ขอบเขต\n\n## ระยะเวลา\n\n# 2 งบประมาณ"
    ]


# Tables


def test_rows_and_cells_held_in_content_controls_keep_their_text() -> None:
    # Found in review: Word's repeating sections hold rows and cells in content controls.
    table = Table((("ก", "ข"), ("ค", "ง"), ("จ", "ฉ")), controlled_rows=(1,), controlled_cells=((2, 1),))

    assert markdown_pages(document(table)) == ["| ก | ข |\n| --- | --- |\n| ค | ง |\n| จ | ฉ |"]


def test_a_table_becomes_a_markdown_table_between_the_text_around_it() -> None:
    source = document(
        "ผู้ให้ทุนจะจ่ายเงินเป็นงวด", Table((("งวดที่", "จำนวนเงิน"), ("๑", "50,000"))), "ตามเงื่อนไขในสัญญา"
    )

    assert markdown_pages(source) == [
        "ผู้ให้ทุนจะจ่ายเงินเป็นงวด\n\n| งวดที่ | จำนวนเงิน |\n| --- | --- |\n| ๑ | 50,000 |\n\nตามเงื่อนไขในสัญญา"
    ]


def test_merged_cells_make_an_html_table_with_spans() -> None:
    source = document(
        Table(
            (
                (Cell("รายการ", rowspan=2), Cell("งบประมาณ", colspan=2)),
                ("ปีที่ ๑", "ปีที่ ๒"),
                ("ค่าตอบแทน", "100,000", "120,000"),
            )
        )
    )

    assert markdown_pages(source) == [
        "<table>\n"
        '<tr><td rowspan="2">รายการ</td><td colspan="2">งบประมาณ</td></tr>\n'
        "<tr><td>ปีที่ ๑</td><td>ปีที่ ๒</td></tr>\n"
        "<tr><td>ค่าตอบแทน</td><td>100,000</td><td>120,000</td></tr>\n"
        "</table>"
    ]


# Pages


def test_a_typed_page_break_starts_a_new_page() -> None:
    result = convert(document("หน้าแรก", PageBreak(), "หน้าที่สอง"))

    assert page_texts(result.output.decode("utf-8")) == ["หน้าแรก", "หน้าที่สอง"]
    assert result.summary.headline().startswith("2 หน้า: อ่านจากข้อความในไฟล์ 2 หน้า")


def test_a_paragraph_set_to_break_the_page_before_it_starts_a_new_page() -> None:
    assert markdown_pages(document("หน้าแรก", PageBreak("before"), Heading("บทที่สอง"))) == ["หน้าแรก", "# บทที่สอง"]


def test_pages_follow_where_words_last_layout_broke_them() -> None:
    source = document("หน้าแรก", PageBreak("rendered"), "หน้าที่สอง", Split("ย่อหน้าที่ขึ้นต้นในหน้าสอง", "และจบในหน้าสาม"))

    assert markdown_pages(source) == ["หน้าแรก", "หน้าที่สอง\n\nย่อหน้าที่ขึ้นต้นในหน้าสอง", "และจบในหน้าสาม"]


def test_a_typed_break_that_word_also_laid_out_as_a_page_break_makes_one_new_page() -> None:
    # Word saves both: the typed break, and where its layout broke the page.
    source = document("หน้าแรก", PageBreak(), PageBreak("rendered"), "หน้าที่สอง")

    assert markdown_pages(source) == ["หน้าแรก", "หน้าที่สอง"]


def test_a_table_running_over_pages_keeps_the_page_numbers_after_it() -> None:
    # The table sits on the page it starts on; the pages it runs onto come out empty.
    table = Table((("แถว๑", "ก"), ("แถว๒", "ข"), ("แถว๓", "ค")), new_pages=(1, 2))

    source = document("ก่อนตาราง", table, "หลังตาราง")

    assert markdown_pages(source) == [
        "ก่อนตาราง\n\n| แถว๑ | ก |\n| --- | --- |\n| แถว๒ | ข |\n| แถว๓ | ค |",
        "",
        "หลังตาราง",
    ]


def test_a_table_that_word_began_on_a_new_page_starts_that_page() -> None:
    source = document("หน้าแรก", Table((("แถว๑", "ก"),), new_pages=(0,)))

    assert markdown_pages(source) == ["หน้าแรก", "| แถว๑ | ก |\n| --- | --- |"]


def test_two_typed_page_breaks_in_a_row_leave_an_empty_page_between() -> None:
    # Found in review: Word counts the page between them.
    assert markdown_pages(document("หน้าแรก", PageBreak(), PageBreak(), "หน้าที่สาม")) == ["หน้าแรก", "", "หน้าที่สาม"]


def test_a_paragraph_set_to_break_the_page_before_it_right_after_a_typed_break_adds_no_page() -> None:
    assert markdown_pages(document("หน้าแรก", PageBreak(), PageBreak("before"), "หน้าที่สอง")) == ["หน้าแรก", "หน้าที่สอง"]


# Images


def test_a_picture_becomes_an_image_placeholder_where_it_sits() -> None:
    source = document("ย่อหน้าก่อนรูป", Image(), "ย่อหน้าหลังรูป")

    assert markdown_pages(source) == ["ย่อหน้าก่อนรูป\n\n[รูปภาพ]\n\nย่อหน้าหลังรูป"]


def test_a_picture_set_in_a_paragraph_splits_it_where_it_sits() -> None:
    assert markdown_pages(document(WithImage("ดูแผนผัง", "ประกอบ"))) == ["ดูแผนผัง\n\n[รูปภาพ]\n\nประกอบ"]


def test_a_picture_in_a_table_cell_is_placed_right_after_the_table() -> None:
    source = document(Table((("ผู้ให้ทุน", Image(60, 20)),)), "ทั้งนี้ตามที่ตกลงกัน")

    assert markdown_pages(source) == ["| ผู้ให้ทุน |  |\n| --- | --- |\n\n[รูปภาพ]\n\nทั้งนี้ตามที่ตกลงกัน"]


def test_a_line_break_typed_in_a_cell_becomes_a_space() -> None:
    # A typed line break sets lines apart on purpose, as a name above a title; a GFM cell holds one line.
    source = document(Table((("ผู้ลงนาม", "ตำแหน่ง"), ("นายสมชาย ใจดี\nผู้อำนวยการ", "ผู้ให้ทุน"))))

    assert markdown_pages(source) == [
        "| ผู้ลงนาม | ตำแหน่ง |\n| --- | --- |\n| นายสมชาย ใจดี ผู้อำนวยการ | ผู้ให้ทุน |"
    ]
