"""Text layers that cannot be taken at their word: legacy glyphs are mapped back to Thai,
and a page whose text layer is still wrong is read with OCR instead."""

import pytest
from fake_ocr import FakeEngine
from generate import CLAUSES
from markdown_reader import page_texts
from pdf_builder import Scan, Styled, pdf, remapped

from pdf_to_doc import ConversionResult, convert

SARA_I = chr(0x0E34)
MAI_EK = chr(0x0E48)
# Legacy Windows Thai fonts shift these marks left over tall consonants, and
# report the shifted glyphs as Private Use Area characters.
SARA_I_SHIFTED_LEFT = chr(0xF701)
MAI_EK_SHIFTED_LEFT = chr(0xF713)


def markdown_pages(result: ConversionResult) -> list[str]:
    return page_texts(result.output.decode("utf-8"))


def test_a_legacy_fonts_private_use_marks_are_read_back_as_thai() -> None:
    legacy = remapped(pdf(["ปิ่นโตทองคำ"]), {SARA_I: SARA_I_SHIFTED_LEFT, MAI_EK: MAI_EK_SHIFTED_LEFT})
    engine = FakeEngine()

    result = convert(legacy, ocr=engine)

    assert markdown_pages(result) == ["ปิ่นโตทองคำ"]
    assert engine.images == []


SARA_AA = chr(0x0E32)
SARA_AM = chr(0x0E33)


def test_a_text_layer_that_misspells_its_words_is_read_with_ocr_instead() -> None:
    # The font reports sara aa as sara am, so "การ" comes out as "กำร".
    source = remapped(pdf(CLAUSES), {SARA_AA: SARA_AM})

    result = convert(source, ocr=FakeEngine(CLAUSES))

    assert markdown_pages(result) == ["".join(CLAUSES)]
    [page] = result.summary.pages
    assert (page.kind, page.untrusted_text_layer) == ("ocr", True)
    assert "ข้อความในไฟล์ไม่น่าเชื่อถือ" in result.summary.headline()


@pytest.mark.parametrize(
    "damage",
    [
        pytest.param({"ก": chr(0xFFFD)}, id="a glyph with no Unicode mapping"),
        pytest.param({"ก": chr(0xE000)}, id="a Private Use Area character that is no legacy Thai glyph"),
        pytest.param({"ง": SARA_AM}, id="sara am after a vowel"),
    ],
)
def test_a_text_layer_holding_what_correct_thai_never_holds_is_read_with_ocr(damage: dict[str, str]) -> None:
    lines = ["เงินทุนของโครงการ", "ผู้ให้ทุนจ่ายเงิน"]

    result = convert(remapped(pdf(lines), damage), ocr=FakeEngine(lines))

    assert markdown_pages(result) == ["".join(lines)]
    assert [page.untrusted_text_layer for page in result.summary.pages] == [True]


def test_a_few_words_are_too_few_to_judge_by_the_dictionary() -> None:
    # Names are often not dictionary words: "ภรณ์" and "พัฒน์" are not. These are made up.
    names = "ลงชื่อ นางสาวสมมติภรณ์ ตัวอย่างวงศ์ และนายทดสอบพัฒน์ สมมติสกุล"
    engine = FakeEngine()

    result = convert(pdf([names]), ocr=engine)

    assert markdown_pages(result) == [names]
    assert engine.images == []


def test_repetition_marks_and_abbreviation_marks_do_not_count_as_misspelt_words() -> None:
    # PyThaiNLP reads "ๆ" and "ฯ" as words of their own, and no dictionary has them.
    lines = ["ผู้รับทุนต้องส่งรายงานเร็วๆ และบ่อยๆ ทุกเดือน", "โดยเขียนให้ชัดๆ สั้นๆ และตรงๆ", "ส่งถึงกรมฯ ที่ดูแลโครงการ", "ให้ทันเวลาทุกครั้งไป"]
    engine = FakeEngine()

    result = convert(pdf(lines), ocr=engine)

    assert [page.kind for page in result.summary.pages] == ["text"]
    assert engine.images == []


# Text over a scan is checked too

STAMP = Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาตจากการไฟฟ้า", size=14, y=40)


def test_a_stamp_on_a_scan_with_unreadable_characters_is_read_with_ocr() -> None:
    source = remapped(pdf(Scan(["เนื้อหาของสัญญา"], overlay=[STAMP], dpi=50)), {"ก": chr(0xFFFD)})

    result = convert(source, ocr=FakeEngine([STAMP, "เนื้อหาของสัญญา"]))

    [page] = markdown_pages(result)
    assert chr(0xFFFD) not in page
    assert page.startswith(STAMP.text)
    assert [summary.untrusted_text_layer for summary in result.summary.pages] == [True]


def test_a_stamp_on_a_scan_whose_font_misreports_its_letters_is_read_with_ocr() -> None:
    # Too short to judge by the dictionary on its own; the engine's reading of
    # the same place spells its words right.
    source = remapped(pdf(Scan(["เนื้อหาของสัญญา"], overlay=[STAMP], dpi=50)), {SARA_AA: SARA_AM})

    result = convert(source, ocr=FakeEngine([STAMP, "เนื้อหาของสัญญา"]))

    [page] = markdown_pages(result)
    assert page.startswith(STAMP.text)


def test_bullets_from_a_symbol_font_are_bullets_not_damage() -> None:
    # Word draws bullets with the Symbol font, which reports them as U+F0B7.
    source = remapped(pdf(["รายการที่ต้องส่ง", "• รายงานความก้าวหน้า", "• รายงานฉบับสมบูรณ์"]), {"•": chr(0xF0B7)})
    engine = FakeEngine()

    result = convert(source, ocr=engine)

    assert markdown_pages(result) == ["รายการที่ต้องส่ง\n\n- รายงานความก้าวหน้า\n- รายงานฉบับสมบูรณ์"]
    assert engine.images == []


def test_a_glyph_the_font_cannot_name_sends_the_page_to_ocr() -> None:
    # The test font has no glyph for the zero-width space, so its text layer
    # cannot say which character it was. It never becomes an invisible NUL.
    result = convert(pdf(["ทดสอบ" + chr(0x200B) + "อักขระ"]), ocr=FakeEngine(["ทดสอบอักขระ"]))

    assert [page.untrusted_text_layer for page in result.summary.pages] == [True]
    assert chr(0) not in result.output.decode("utf-8")
