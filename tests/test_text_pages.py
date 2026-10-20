"""Text pages: PDF pages whose text layer is converted, through the conversion function only."""

import pytest
from markdown_reader import page_texts
from pdf_builder import Spaced, pdf

from pdf_to_doc import convert

SARA_AM = "\u0e33"
SARA_AA = "\u0e32"
NIKHAHIT = "\u0e4d"
MAI_EK = "\u0e48"
MAI_HAN_AKAT = "\u0e31"
NO_BREAK_SPACE = "\u00a0"
SOFT_HYPHEN = "\u00ad"


def markdown_pages(source: bytes) -> list[str]:
    return page_texts(convert(source, to="markdown").output.decode("utf-8"))


def test_a_thai_text_page_comes_out_as_its_text() -> None:
    assert markdown_pages(pdf(["ภาษาไทยอ่านได้ถูกต้อง"])) == ["ภาษาไทยอ่านได้ถูกต้อง"]


def test_paragraphs_stay_separate() -> None:
    source = pdf(["ย่อหน้าแรกของเอกสาร", "", "ย่อหน้าที่สองของเอกสาร"])

    assert markdown_pages(source) == ["ย่อหน้าแรกของเอกสาร\n\nย่อหน้าที่สองของเอกสาร"]


def test_a_line_of_only_spaces_adds_no_empty_paragraph() -> None:
    source = pdf(["ย่อหน้าแรกของเอกสาร", "", "     ", "", "ย่อหน้าที่สองของเอกสาร"])

    assert markdown_pages(source) == ["ย่อหน้าแรกของเอกสาร\n\nย่อหน้าที่สองของเอกสาร"]


def test_an_indented_line_does_not_become_a_markdown_code_block() -> None:
    source = pdf(["ย่อหน้าแรกของเอกสาร", "", "    ข้อความที่ย่อหน้าเข้าไปสี่ช่อง"])

    assert markdown_pages(source) == ["ย่อหน้าแรกของเอกสาร\n\nข้อความที่ย่อหน้าเข้าไปสี่ช่อง"]


def test_every_page_is_marked_and_listed_in_the_summary_as_a_text_page() -> None:
    result = convert(pdf(["หน้าแรก"], ["หน้าที่สอง"]))

    assert page_texts(result.output.decode("utf-8")) == ["หน้าแรก", "หน้าที่สอง"]
    assert [(page.number, page.kind) for page in result.summary.pages] == [
        (1, "text"),
        (2, "text"),
    ]


def test_the_markdown_opens_with_a_summary_of_the_conversion() -> None:
    markdown = convert(pdf(["หน้าแรก"], ["หน้าที่สอง"])).output.decode("utf-8")

    summary = markdown.split("<!-- page 1 -->")[0]
    assert summary.startswith(">")
    assert "2 หน้า" in summary


def test_an_output_format_that_is_not_supported_yet_is_refused() -> None:
    with pytest.raises(ValueError):
        convert(pdf(["หน้าแรก"]), to="docx")  # type: ignore[arg-type]


# Line joining


def test_thai_lines_wrapped_inside_a_phrase_rejoin_without_a_space() -> None:
    source = pdf(["สัญญาให้ทุนโครงการพัฒนา", "กาวชีวภาพจากกากถั่วเหลือง"])

    assert markdown_pages(source) == ["สัญญาให้ทุนโครงการพัฒนากาวชีวภาพจากกากถั่วเหลือง"]


def test_a_line_that_wraps_at_a_space_keeps_one_space() -> None:
    source = pdf(["งานวิจัยนี้มีเป้าหมาย ", "เพื่อพัฒนาวัสดุชีวภาพ"])

    assert markdown_pages(source) == ["งานวิจัยนี้มีเป้าหมาย เพื่อพัฒนาวัสดุชีวภาพ"]


def test_a_line_that_starts_with_a_space_joins_with_one_space() -> None:
    source = pdf(["พัฒนาระบบเศรษฐกิจชีวภาพ", " Bio-Circular-Green Economy"])

    assert markdown_pages(source) == ["พัฒนาระบบเศรษฐกิจชีวภาพ Bio-Circular-Green Economy"]


def test_thai_and_english_meet_across_a_line_break_with_one_space() -> None:
    source = pdf(["พัฒนาระบบเศรษฐกิจชีวภาพ", "Bio-Circular-Green Economy", "ในด้านพลังงานสะอาด"])

    assert markdown_pages(source) == [
        "พัฒนาระบบเศรษฐกิจชีวภาพ Bio-Circular-Green Economy ในด้านพลังงานสะอาด"
    ]


def test_a_hyphen_at_a_line_break_is_kept_and_the_word_rejoined() -> None:
    # Word breaks lines after hyphens that are part of the word, so the hyphen stays.
    source = pdf(["a long-", "term plan for COVID-", "19 in 2567-", "2568"])

    assert markdown_pages(source) == ["a long-term plan for COVID-19 in 2567-2568"]


def test_a_soft_hyphen_at_a_line_break_is_dropped_and_the_word_rejoined() -> None:
    source = pdf([f"the conver{SOFT_HYPHEN}", "sion tool"])

    assert markdown_pages(source) == ["the conversion tool"]


# Spacing inside a line


def test_thai_letters_spread_apart_by_justification_stay_one_word() -> None:
    # Each character cluster is placed separately with extra room, as in
    # justified text. A gap between Thai letters is never a word break.
    source = pdf([Spaced(("ค", "ว", "า", "ม", "ร่", "ว", "ม", "มื", "อ"), gap=5)])

    assert markdown_pages(source) == ["ความร่วมมือ"]


def test_a_justified_thai_paragraph_over_several_lines_reads_as_running_text() -> None:
    source = pdf(
        [
            Spaced(("ผู้", "รั", "บ", "ทุ", "น", "ต", "ก", "ล", "ง"), gap=4),
            Spaced(("ดำ", "เ", "นิ", "น", "ง", "า", "น"), gap=6),
        ]
    )

    assert markdown_pages(source) == ["ผู้รับทุนตกลงดำเนินงาน"]


def test_english_words_placed_apart_without_space_characters_are_separated() -> None:
    source = pdf([Spaced(("Signed", "agreement"), gap=5)])

    assert markdown_pages(source) == ["Signed agreement"]


def test_thai_and_english_placed_apart_on_one_line_are_separated() -> None:
    source = pdf([Spaced(("ภาษาไทย", "English", "ภาษาไทย"), gap=6)])

    assert markdown_pages(source) == ["ภาษาไทย English ภาษาไทย"]


# Character repair


def test_sara_am_stored_as_two_characters_comes_out_as_one() -> None:
    source = pdf([f"การท{NIKHAHIT}{SARA_AA}งานร่วมกัน", f"การท{SARA_AA}{NIKHAHIT}งานร่วมกัน"])

    assert markdown_pages(source) == [f"การท{SARA_AM}งานร่วมกันการท{SARA_AM}งานร่วมกัน"]


def test_sara_am_is_never_split_into_two_characters() -> None:
    source = pdf([f"การท{SARA_AM}งานร่วมกัน"])

    assert markdown_pages(source) == [f"การท{SARA_AM}งานร่วมกัน"]


def test_a_tone_mark_stored_before_its_vowel_is_put_in_standard_order() -> None:
    source = pdf([f"ท{MAI_EK}{MAI_HAN_AKAT}วไป"])

    assert markdown_pages(source) == [f"ท{MAI_HAN_AKAT}{MAI_EK}วไป"]


def test_a_stray_space_before_a_thai_mark_is_removed() -> None:
    source = pdf([f"เพิ {MAI_EK}มความร่วมมือ ท {SARA_AM}งาน ก{NO_BREAK_SPACE}{MAI_EK}อน"])

    assert markdown_pages(source) == [f"เพิ{MAI_EK}มความร่วมมือ ท{SARA_AM}งาน ก{MAI_EK}อน"]


def test_a_space_before_a_following_vowel_is_kept() -> None:
    # Sara aa can follow a space when a text names the vowel itself.
    source = pdf([f"สระ {SARA_AA} ออกเสียงยาว"])

    assert markdown_pages(source) == [f"สระ {SARA_AA} ออกเสียงยาว"]
