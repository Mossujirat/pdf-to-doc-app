"""Scoring one page of output against its reference text."""

from pdf_to_doc.quality import score_page


def test_an_output_identical_to_its_reference_scores_perfect() -> None:
    score = score_page(output="สัญญาให้ทุนโครงการ", reference="สัญญาให้ทุนโครงการ")

    assert score.cer == 0
    assert score.thai_cer == 0
    assert score.broken.total == 0


def test_cer_is_the_number_of_edits_per_reference_character() -> None:
    # 5 reference characters; the output adds 5 more: 5 edits / 5 = 1.0
    assert score_page(output="abcdeXXXXX", reference="abcde").cer == 1.0
    # 10 reference characters; one is wrong: 1 / 10
    assert score_page(output="abcdefghiX", reference="abcdefghij").cer == 0.1


def test_thai_cer_counts_only_thai_characters() -> None:
    reference = "ภาษาไทย English"  # 7 Thai characters

    assert score_page(output="ภาษาไทย Englsih", reference=reference).thai_cer == 0
    assert score_page(output="ภาษาไท English", reference=reference).thai_cer == 1 / 7


def test_line_breaks_and_repeated_spaces_do_not_count_as_errors() -> None:
    score = score_page(output="ข้อแรก\n\nข้อสอง   ข้อสาม ", reference="ข้อแรก ข้อสอง\nข้อสาม")

    assert score.cer == 0


def test_markdown_and_html_markup_do_not_count_as_errors() -> None:
    reference = "# หัวข้อ\n\n<table><tr><td>งวดที่ 1</td><td>[ลายเซ็น]</td></tr></table>"

    assert score_page(output="หัวข้อ งวดที่ 1 [ลายเซ็น]", reference=reference).cer == 0


def test_comparison_never_splits_sara_am() -> None:
    # NFKC would turn sara am into nikhahit + sara aa and hide this difference.
    score = score_page(output="ท\u0e4d\u0e32งาน", reference="ท\u0e33งาน")

    assert score.cer > 0


# Broken text, by category


def test_a_mark_left_after_a_space_is_an_orphan_mark() -> None:
    score = score_page(output="เพิ \u0e48มความร่วมมือ ท \u0e33งาน", reference="เพิ่มความร่วมมือ ทำงาน")

    assert score.broken.orphan_marks == 2
    assert score.broken.total == 2


def test_a_space_inserted_between_thai_letters_is_a_space_inside_a_word() -> None:
    score = score_page(output="หรื อความร่วม มือ", reference="หรือความร่วมมือ")

    assert score.broken.spaces_inside_words == 2


def test_spaces_that_the_reference_also_has_are_not_broken_text() -> None:
    score = score_page(output="ภาษาไทย ภาษาอังกฤษ", reference="ภาษาไทย ภาษาอังกฤษ")

    assert score.broken.total == 0


def test_private_use_area_characters_are_counted() -> None:
    # Legacy Thai fonts store a shifted tone mark as U+F70A instead of U+0E48.
    score = score_page(output="ป\uf70aาไม้", reference="ป\u0e48าไม้")

    assert score.broken.pua_characters == 1


def test_sara_am_stored_as_two_characters_is_counted() -> None:
    score = score_page(output="ท\u0e4d\u0e32งาน", reference="ท\u0e33งาน")

    assert score.broken.decomposed_sara_am == 1


def test_a_run_of_reference_text_absent_from_the_output_is_missing_text() -> None:
    reference = "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน\nผู้รับทุนต้องส่งรายงานความก้าวหน้าทุกหกเดือน\nสัญญานี้มีผลตั้งแต่วันที่ลงนาม"
    output = "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน สัญญานี้มีผลตั้งแต่วันที่ลงนาม"

    assert score_page(output=output, reference=reference).broken.missing_text == 1


def test_missing_text_does_not_depend_on_how_the_reference_is_wrapped() -> None:
    sentence = "ผู้รับทุนต้องส่งรายงานความก้าวหน้าทุกหกเดือน"
    output = "บทนำของสัญญา สัญญานี้มีผลตั้งแต่วันที่ลงนาม"
    one_line = f"บทนำของสัญญา {sentence} สัญญานี้มีผลตั้งแต่วันที่ลงนาม"
    wrapped = f"บทนำของสัญญา\n{sentence[:15]}\n{sentence[15:30]}\n{sentence[30:]}\nสัญญานี้มีผลตั้งแต่วันที่ลงนาม"

    assert score_page(output=output, reference=one_line).broken.missing_text == 1
    assert score_page(output=output, reference=wrapped).broken.missing_text == 1


def test_a_repeated_line_that_appears_only_once_in_the_output_is_missing_text() -> None:
    reference = "ลงชื่อ ผู้ให้ทุนโครงการ\nลงชื่อ ผู้ให้ทุนโครงการ"

    assert score_page(output="ลงชื่อ ผู้ให้ทุนโครงการ", reference=reference).broken.missing_text == 1


def test_a_small_typo_is_not_missing_text() -> None:
    reference = "ผู้รับทุนต้องส่งรายงานความก้าวหน้าทุกหกเดือน"
    output = "ผู้รับทุนต้องส่งรายงานความก้าวหน้าทุกหกเดีอน"

    assert score_page(output=output, reference=reference).broken.missing_text == 0


def test_spaces_inside_words_are_not_also_counted_as_missing_text() -> None:
    score = score_page(output="ผู้ รับ ทุน ต้อง ส่ง ราย งาน", reference="ผู้รับทุนต้องส่งรายงาน")

    assert score.broken.spaces_inside_words == 6
    assert score.broken.total == 6


def test_a_space_moved_into_a_word_is_a_space_inside_a_word() -> None:
    assert score_page(output="ภาษาไ ทย", reference="ภาษา ไทย").broken.spaces_inside_words == 1


def test_sara_am_stored_as_two_characters_in_either_order_is_counted() -> None:
    score = score_page(output="ท\u0e32\u0e4dงาน ท\u0e4d\u0e32งาน", reference="ท\u0e33งาน ท\u0e33งาน")

    assert score.broken.decomposed_sara_am == 2


def test_an_empty_reference_with_output_counts_every_output_character_as_an_error() -> None:
    score = score_page(output="ขยะ", reference="")

    assert (score.edits, score.characters) == (3, 0)


# Markup in reference text and outputs


def test_inline_markup_such_as_uncertain_text_marks_does_not_split_words() -> None:
    score = score_page(output="การทำ<mark>งาน</mark>ร่วมกัน", reference="การทำงานร่วมกัน")

    assert score.cer == 0
    assert score.broken.total == 0


def test_angle_brackets_in_text_are_not_mistaken_for_markup() -> None:
    text = "ราคา <5 บาท และ >3 บาท"

    assert score_page(output=text, reference=text).characters == len(text)


def test_html_entities_are_read_as_the_characters_they_stand_for() -> None:
    assert score_page(output="ก&ข", reference="<td>ก&amp;ข</td>").cer == 0


def test_markdown_list_bullets_do_not_count_as_errors() -> None:
    output = "- 1. เงื่อนไขของสัญญา\n- 2. ขอบเขตของงาน\n- รายงานฉบับสมบูรณ์"
    reference = "1. เงื่อนไขของสัญญา\n2. ขอบเขตของงาน\nรายงานฉบับสมบูรณ์"

    assert score_page(output=output, reference=reference).cer == 0


# Tables: how many of the reference's cells the output holds in the right place

PAYMENTS = "ผู้ให้ทุนจ่ายเงินเป็นงวด\n\n| งวดที่ | จำนวนเงิน |\n| --- | --- |\n| 1 | 150,000 |\n| 2 | 250,000 |"


def test_a_table_that_is_all_right_has_every_cell_in_place() -> None:
    score = score_page(output=PAYMENTS, reference=PAYMENTS)

    assert (score.cells_right, score.cells) == (6, 6)


def test_amounts_swapped_between_rows_are_out_of_place_though_every_character_is_right() -> None:
    swapped = PAYMENTS.replace("150,000", "X").replace("250,000", "150,000").replace("X", "250,000")

    score = score_page(output=swapped, reference=PAYMENTS)

    assert (score.cells_right, score.cells) == (4, 6)


def test_a_table_flattened_into_a_paragraph_has_no_cell_in_place() -> None:
    flattened = "ผู้ให้ทุนจ่ายเงินเป็นงวด\n\nงวดที่ จำนวนเงิน 1 150,000 2 250,000"

    score = score_page(output=flattened, reference=PAYMENTS)

    assert score.cer == 0  # the characters cannot tell
    assert (score.cells_right, score.cells) == (0, 6)


BUDGET = (
    '<table>\n<tr><td rowspan="2">รายการ</td><td colspan="2">งบประมาณ</td></tr>\n'
    "<tr><td>ปีที่ ๑</td><td>ปีที่ ๒</td></tr>\n"
    "<tr><td>ค่าวัสดุ</td><td>-</td><td>30,000</td></tr>\n</table>"
)


def test_merged_cells_put_the_cells_after_them_where_a_reader_finds_them() -> None:
    # Without the merges, "ปีที่ ๑" and "ปีที่ ๒" move one column left, and the
    # third column of that row is gone: 5 of the 7 cells stay in place.
    unmerged = "| รายการ | งบประมาณ |\n| --- | --- |\n| ปีที่ ๑ | ปีที่ ๒ |\n| ค่าวัสดุ | - | 30,000 |"

    score = score_page(output=BUDGET, reference=BUDGET)

    assert (score.cells_right, score.cells) == (7, 7)
    assert score_page(output=unmerged, reference=BUDGET).cells_right == 5


def test_a_table_the_output_lacks_has_none_of_its_cells_in_place() -> None:
    score = score_page(output=PAYMENTS, reference=f"{PAYMENTS}\n\nงบประมาณ\n\n{BUDGET}")

    assert (score.cells_right, score.cells) == (6, 13)


def test_each_reference_table_is_compared_with_the_output_table_that_holds_its_text() -> None:
    # The output found a table the reference does not have, before the payments.
    score = score_page(output=f"{BUDGET}\n\n{PAYMENTS}", reference=PAYMENTS)

    assert (score.cells_right, score.cells) == (6, 6)


def test_a_page_without_tables_has_no_cells() -> None:
    score = score_page(output="สัญญาให้ทุนโครงการ", reference="สัญญาให้ทุนโครงการ")

    assert (score.cells_right, score.cells) == (0, 0)


def test_uncertain_text_marks_and_escaped_bars_inside_cells_do_not_move_them() -> None:
    reference = "| งวดที่ | รายละเอียด |\n| --- | --- |\n| 1 | ส่งแผนงาน \\| รายงาน |"
    output = "| งวดที่ | รายละเอียด |\n| --- | --- |\n| 1 | ส่ง<mark>แผน</mark>งาน \\| รายงาน |"

    assert score_page(output=output, reference=reference).cells_right == 4


def test_a_line_break_kept_in_a_cell_counts_the_same_on_both_sides() -> None:
    reference = "| รายการ | จำนวนเงิน |\n| --- | --- |\n| ค่าวัสดุสำนักงาน<br>ค่าถ่ายเอกสาร | 15,500 |"
    glued = reference.replace("<br>", "")

    assert score_page(output=reference, reference=reference).cells_right == 4
    assert score_page(output=glued, reference=reference).cells_right == 3
