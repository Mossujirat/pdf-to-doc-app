"""Uncertain text: OCR text the converter cannot confirm is marked where it appears, and counted."""

from docx.text.paragraph import Paragraph
from docx_reader import read_docx, runs
from fake_ocr import FakeEngine, Unsure
from markdown_reader import page_texts
from pdf_builder import Scan, Styled, pdf

from pdf_to_doc import ConversionResult, convert


def markdown_pages(result: ConversionResult) -> list[str]:
    return page_texts(result.output.decode("utf-8"))


def scan() -> bytes:
    return pdf(Scan(["ภาพสแกน"], dpi=50))


def test_a_word_misread_into_one_that_is_not_in_the_dictionary_is_marked() -> None:
    # The engine dropped mai ek from "ผู้อื่น".
    result = convert(scan(), ocr=FakeEngine(["ผู้รับทุนต้องไม่โอนสิทธิให้ผู้อืน"]))

    assert markdown_pages(result) == ["ผู้รับทุนต้องไม่โอนสิทธิให้ผู้<mark>อืน</mark>"]


def test_short_common_words_beside_a_misread_are_not_marked_with_it() -> None:
    result = convert(scan(), ocr=FakeEngine(["ย้ายไปที่อืนจะดีกว่า"]))

    assert markdown_pages(result) == ["ย้ายไปที่<mark>อืน</mark>จะดีกว่า"]


def test_a_transliterated_word_the_segmenter_cuts_up_is_not_marked() -> None:
    # The word list lacks "ฟอร์มัล"; joined to "ดีไฮด์", it is a Thai Wikipedia title.
    line = "กาวไม่ปล่อยสารฟอร์มัลดีไฮด์"

    result = convert(scan(), ocr=FakeEngine([line]))

    assert markdown_pages(result) == [line]


def test_a_word_cut_into_pieces_is_marked_whole() -> None:
    # Not a title, so the reader checks it: all of it, not its unknown pieces "ก", "ลลู" and "ก".
    result = convert(scan(), ocr=FakeEngine(["การพัฒนาวัสดุลิกโนเซลลูโลสิก"]))

    assert markdown_pages(result) == ["การพัฒนาวัสดุ<mark>ลิกโนเซลลูโลสิก</mark>"]


def test_a_letter_in_parentheses_that_lists_items_is_not_marked() -> None:
    line = "งบประมาณประกอบด้วย (ก) ค่าวัสดุ (ข) ค่าจ้าง"

    result = convert(scan(), ocr=FakeEngine([line]))

    assert markdown_pages(result) == [line]


def test_an_abbreviation_with_full_stops_is_not_marked() -> None:
    line = "ผลการตัดสินของ บพข. ถือเป็นที่สิ้นสุด ลงนามโดย ส. ปร.ด. รอง ผพว."

    result = convert(scan(), ocr=FakeEngine([line]))

    assert markdown_pages(result) == [line]


def test_consonants_ending_a_word_before_a_full_stop_are_not_an_abbreviation() -> None:
    result = convert(scan(), ocr=FakeEngine(["ใช้งานระบบกข."]))

    assert markdown_pages(result) == ["ใช้งานระบบ<mark>กข</mark>."]


def test_na_standing_alone_is_not_marked_but_inside_a_misread_word_is() -> None:
    # "คุณภาพ" misread as "กุณภาพ" leaves "ณ" as a piece of its own.
    result = convert(scan(), ocr=FakeEngine(["ทำขึ้น ณ วันที่ 21 ตุลาคม ระบบบริหารกุณภาพ"]))

    assert markdown_pages(result) == ["ทำขึ้น ณ วันที่ 21 ตุลาคม ระบบบริหาร<mark>กุณ</mark>ภาพ"]


def test_neighbouring_uncertain_words_are_marked_as_one() -> None:
    # "เดือน ศูนย์" misread as two words that are not words.
    result = convert(scan(), ocr=FakeEngine(["ส่งรายงานทุกหกเคือน ศนย์ตรวจรับแล้ว"]))

    assert markdown_pages(result) == ["ส่งรายงานทุกหก<mark>เคือน ศนย์</mark>ตรวจรับแล้ว"]


def test_a_line_the_engine_reads_with_low_confidence_is_marked_whole() -> None:
    engine = FakeEngine(["ผู้รับทุนตกลงดำเนินงาน", Unsure("ตามแผนที่กำหนดไว้")])

    result = convert(scan(), ocr=engine)

    assert markdown_pages(result) == ["ผู้รับทุนตกลงดำเนินงาน<mark>ตามแผนที่กำหนดไว้</mark>"]


def test_uncertain_text_in_a_list_item_is_marked() -> None:
    engine = FakeEngine(["• ส่งรายงานทุกหกเคือน", "• จ่ายเงินตามงวดงาน"])

    result = convert(scan(), ocr=engine)

    assert markdown_pages(result) == ["- ส่งรายงานทุกหก<mark>เคือน</mark>\n- จ่ายเงินตามงวดงาน"]


def test_text_from_a_text_layer_is_never_marked() -> None:
    # A surname the word list does not hold ("มณฑน์"), on a text page and stamped as text over a scan.
    signed = "ลงชื่อ นายสมชาย ชุติมณฑน์"
    body = ["ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้"] * 12
    source = pdf([signed], Scan(body, overlay=[Styled(signed, y=500)], dpi=50))

    result = convert(source, ocr=FakeEngine([*body, Styled("ลงชื่อ นายสมชาย ชุติมณฑบ์", y=500)]))

    text_page, scanned = markdown_pages(result)
    assert text_page == signed
    assert signed in scanned
    assert "<mark>" not in scanned


def test_text_layer_text_in_the_same_paragraph_as_ocr_text_is_not_marked() -> None:
    # The note is stamped as text just below the scanned body, close enough to make one paragraph.
    body = ["ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้"] * 2 + ["ส่งรายงานทุกหกเคือน"]
    note = Styled("ลงชื่อ นายสมชาย ชุติมณฑน์", y=170)

    result = convert(pdf(Scan(body, overlay=[note], dpi=50)), ocr=FakeEngine([*body, note]))

    [page] = markdown_pages(result)
    assert page.endswith("ส่งรายงานทุกหก<mark>เคือน</mark>ลงชื่อ นายสมชาย ชุติมณฑน์")


def test_a_low_confidence_box_is_marked_where_it_was_read_and_nowhere_else() -> None:
    # The bullet the engine read is not in the list item's text, and "9" appears twice.
    lines: list[str | Unsure] = [Unsure("• ส่งรายงานทุกหกเดือนให้ผู้ให้ทุน"), "ตรวจสอบจนจบโครงการ", "", "ข้อ 9 วันที่", Unsure("9")]

    result = convert(scan(), ocr=FakeEngine(lines))

    assert markdown_pages(result) == [
        "- <mark>ส่งรายงานทุกหกเดือนให้ผู้ให้ทุน</mark>ตรวจสอบจนจบโครงการ\n\nข้อ 9 วันที่ <mark>9</mark>"
    ]


# Words and numbers shaped like a misread. The engine reads them with confidence, and English
# words and numbers are not looked up in a word list, so only their shape gives them away.


def test_a_number_with_letters_read_in_place_of_its_digits_is_marked() -> None:
    result = convert(scan(), ocr=FakeEngine(["The Buyer shall pay 12,ooo.oo baht, 1O% in advance."]))

    assert markdown_pages(result) == ["The Buyer shall pay <mark>12,ooo.oo</mark> baht, <mark>1O%</mark> in advance."]


def test_codes_that_mix_letters_and_digits_are_not_marked() -> None:
    # Neither a Roman numeral before a clause's number nor a code such as "1O1A" is a misread number.
    line = "Paper A4, room S1, the 1st B2B order under ISO 9001 after COVID-19, item No.5 at 2.5%, Annex I.2, Part II.3, desk 1O1A."

    result = convert(scan(), ocr=FakeEngine([line]))

    assert markdown_pages(result) == [line]


def test_a_small_letter_read_in_place_of_a_capital_is_marked() -> None:
    result = convert(scan(), ocr=FakeEngine(["Delivered to BKk office of THAlLAND POST."]))

    assert markdown_pages(result) == ["Delivered to <mark>BKk</mark> office of <mark>THAlLAND</mark> POST."]


def test_words_written_in_mixed_case_on_purpose_are_not_marked() -> None:
    # A small o between capitals stands for "of".
    line = "Dr. Somchai, PhD, of McDonald Ltd sent two PDFs from an iPhone over a 5 GHz link, with the ToRs and the MoU."

    result = convert(scan(), ocr=FakeEngine([line]))

    assert markdown_pages(result) == [line]


def test_a_roman_numeral_with_l_read_in_place_of_i_is_marked() -> None:
    result = convert(scan(), ocr=FakeEngine(["Schedules l, Il and ll form part of this Agreement. Ill health excuses delay."]))

    assert markdown_pages(result) == [
        "Schedules <mark>l</mark>, <mark>Il</mark> and <mark>ll</mark> form part of this Agreement. Ill health excuses delay."
    ]


def test_an_english_word_read_with_a_thai_look_alike_letter_is_marked() -> None:
    # The Thai recogniser read s as ร and o as Thai zero.
    result = convert(scan(), ocr=FakeEngine(["ส่งรายงานเป็นไฟล์ PDF ผ่านระบบ Teamร และ Z๐om"]))

    assert markdown_pages(result) == ["ส่งรายงานเป็นไฟล์ PDF ผ่านระบบ <mark>Teamร</mark> และ <mark>Z๐om</mark>"]


def test_a_number_that_mixes_thai_and_arabic_digits_is_marked() -> None:
    # The engine read the Thai digit ๕ as 5; the year is written in Arabic digits on purpose.
    result = convert(scan(), ocr=FakeEngine(["ลงวันที่ ๑5 มกราคม 2567 ชำระ ๒๕,๐๐๐ บาท"]))

    assert markdown_pages(result) == ["ลงวันที่ <mark>๑5</mark> มกราคม 2567 ชำระ ๒๕,๐๐๐ บาท"]


def test_thai_text_joined_to_an_english_name_on_purpose_is_not_marked() -> None:
    line = "ลงนามโดยบริษัทABC จำกัด"

    result = convert(scan(), ocr=FakeEngine([line]))

    assert markdown_pages(result) == [line]


# The summary


def summary_of(result: ConversionResult) -> str:
    return result.output.decode("utf-8").split("<!-- page 1 -->")[0]


def test_the_summary_counts_the_uncertain_text_and_says_how_it_is_marked() -> None:
    source = pdf(Scan(["สแกน"], dpi=50), ["หน้าที่มีข้อความ"], Scan(["สแกน"], dpi=50))
    engine = FakeEngine(["ให้ผู้อืนรับรอง", "", "ส่งทุกหกเคือน"], ["ข้อความที่อ่านได้ถูกต้อง"])

    result = convert(source, ocr=engine)

    summary = summary_of(result)
    assert "ข้อความที่ไม่แน่ใจ 2 จุด ในหน้า 1 ควรตรวจกับต้นฉบับ (ครอบไว้ด้วย `<mark>`)" in summary
    # Written as code, so that a viewer shows the tag rather than highlighting, and no one counts it.
    assert summary.count("<mark>") == summary.count("`<mark>`")


def test_the_summary_says_nothing_of_uncertain_text_when_there_is_none() -> None:
    result = convert(scan(), ocr=FakeEngine(["ข้อความที่อ่านได้ถูกต้อง"]))

    assert "ไม่แน่ใจ" not in summary_of(result)


# DOCX


def test_uncertain_text_is_highlighted_yellow_in_docx_and_counted_on_the_first_page() -> None:
    result = convert(scan(), to="docx", ocr=FakeEngine(["ผู้รับทุนต้องไม่โอนสิทธิให้ผู้อืน"]))

    output = read_docx(result.output)
    [[paragraph]] = output.pages
    assert isinstance(paragraph, Paragraph)
    assert [(run.text, run.highlight) for run in runs(paragraph)] == [
        ("ผู้รับทุนต้องไม่โอนสิทธิให้ผู้", None),
        ("อืน", "yellow"),
    ]
    assert "ข้อความที่ไม่แน่ใจ 1 จุด ในหน้า 1 ควรตรวจกับต้นฉบับ (ไฮไลต์สีเหลือง)" in output.summary.text
