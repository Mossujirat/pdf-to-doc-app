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
