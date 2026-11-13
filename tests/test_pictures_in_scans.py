"""Pictures inside a scan: a signature, a stamp or a picture that is part of a scanned page's
image comes out as a placeholder, as a picture on a text page does, and the junk OCR read in
it goes with it."""

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import pytest
from fake_ocr import Boxed, FakeEngine, FakePictures, Sideways, UpsideDown
from generate import CLAUSES, SIGNATURE, SIGNATURE_LINE
from markdown_reader import page_texts
from pdf_builder import TOP, Drawn, Picture, Scan, Styled, pdf

from pdf_to_doc import ModelsMissing, convert
from pdf_to_doc.ocr_models import DETECTOR, THAI_RECOGNISER
from pdf_to_doc.paddle import default_picture_finder
from pdf_to_doc.pictures import NoPictures

# Lines that both the PDF builder and the fake engine lay out.
Line = str | Styled | Picture
# Enough body text around a picture for a page of its own.
BEFORE, AFTER = CLAUSES[:3], CLAUSES[3:]
# A signing page, and its Markdown once its signature is found.
SIGNING_PAGE: list[Line] = [*CLAUSES, "", SIGNATURE, SIGNATURE_LINE]
SIGNED_PAGE = "".join(CLAUSES) + "\n\n[ลายเซ็น]\n\n" + SIGNATURE_LINE


def scan_markdown(*pages: Sequence[Line | Boxed], pictures: FakePictures | None = None) -> list[str]:
    """The Markdown of scans of the pages, read by an engine that reads their text, boxes it draws
    on its own too, with a finder that finds their pictures."""
    drawn = ([line for line in page if not isinstance(line, Boxed)] for page in pages)
    source = pdf(*(Scan(lines, dpi=100, colour=True) for lines in drawn))
    finder = pictures or FakePictures(*pages)
    return page_texts(convert(source, ocr=FakeEngine(*pages), pictures=finder).output.decode("utf-8"))


def between_the_clauses(placeholder: str) -> list[str]:
    """The Markdown of a page holding the placeholder between BEFORE and AFTER."""
    return ["".join(BEFORE) + f"\n\n{placeholder}\n\n" + "".join(AFTER)]


def test_a_signature_beside_a_row_to_sign_on_becomes_a_signature_placeholder() -> None:
    assert scan_markdown(SIGNING_PAGE) == [SIGNED_PAGE]


def test_a_red_ring_becomes_a_stamp_placeholder() -> None:
    assert scan_markdown([*BEFORE, Picture("stamp", 70, 70), *AFTER]) == between_the_clauses("[ตราประทับ]")


def test_a_photo_becomes_an_image_placeholder_between_the_paragraphs_around_it() -> None:
    assert scan_markdown([*BEFORE, Picture("photo", 120, 80), *AFTER]) == between_the_clauses("[รูปภาพ]")


def test_a_round_pie_chart_is_only_an_image() -> None:
    page: list[Line] = [*BEFORE, Picture("chart", 70, 70), *AFTER]

    pages = scan_markdown(page, pictures=FakePictures(page, labels={"chart": "chart"}))

    assert pages == between_the_clauses("[รูปภาพ]")


def test_a_thin_rule_found_as_a_picture_gets_no_placeholder() -> None:
    # As on a text page: an image whose shorter side is under 8 points is a rule or an ornament.
    pages = scan_markdown([*BEFORE, Picture("photo", 400, 6), *AFTER])

    assert pages == ["".join(BEFORE) + "\n\n" + "".join(AFTER)]


# Text OCR read inside a picture

SIGNED_AT = 300.0
SIGNED = Picture("signature", 140, 45, x=130, y=SIGNED_AT, overlap=14)
JUNK = Boxed("ฟฦ๏", 160, SIGNED_AT + 10, SIGNED_AT + 30, confidence=0.4)


def test_junk_read_in_a_signature_is_dropped() -> None:
    assert scan_markdown([*CLAUSES, SIGNED, JUNK, SIGNATURE_LINE]) == [SIGNED_PAGE]


def test_the_signers_name_under_the_row_to_sign_on_reads_as_printed() -> None:
    name = "(นายสมชาย ใจดี)"

    [page] = scan_markdown([*CLAUSES, SIGNED, JUNK, SIGNATURE_LINE, name])

    # The name runs on from the row to sign on just above it, as close rows make one paragraph.
    assert page == SIGNED_PAGE + " " + name


def test_text_read_surely_in_a_signature_stays() -> None:
    name = Boxed("สมชาย", 160, SIGNED_AT + 10, SIGNED_AT + 30, confidence=0.99)

    [page] = scan_markdown([*CLAUSES, SIGNED, name, SIGNATURE_LINE])

    # The name runs on into the row to sign on just under it, as close rows make one paragraph.
    assert page == "".join(CLAUSES) + "\n\n[ลายเซ็น]\n\nสมชาย" + SIGNATURE_LINE


def test_text_unsure_in_a_picture_found_behind_the_text_stays() -> None:
    # The layout model found a whole damaged scan of the corpus as one image: the page behind its
    # text, which gets no placeholder (see `layout._placeholder`). Junk is dropped only for one.
    behind = Picture("photo", 450, 80, y=TOP - 20)
    unsure = Boxed("ฟฦ๏", 300, TOP + 50, TOP + 58, confidence=0.4)

    [page] = scan_markdown([*BEFORE, unsure, behind, *AFTER])

    assert "[รูปภาพ]" not in page
    assert "ฟฦ๏" in page


def test_text_unsure_in_a_picture_with_text_layer_rows_typed_over_it_stays() -> None:
    # Found in review: page layout counts the text layer's rows over a picture too, so a picture under
    # three typed rows gets no placeholder, and the junk dropped from it was lost with nothing in its place.
    behind = Picture("photo", 450, 90, y=SIGNED_AT)
    typed = [Styled(f"บันทึกแนบท้ายข้อ {number}", x=100, y=SIGNED_AT + 25 * number) for number in (1, 2, 3)]
    unsure = Boxed("ฟฦ๏", 420, SIGNED_AT + 70, SIGNED_AT + 78, confidence=0.4)
    lines: list[Line] = [*BEFORE, behind, *AFTER]
    source = pdf(Scan(lines, overlay=typed, dpi=100, colour=True))

    result = convert(source, ocr=FakeEngine([*lines, unsure]), pictures=FakePictures(lines))

    markdown = result.output.decode("utf-8")
    assert "[รูปภาพ]" not in markdown
    assert "ฟฦ๏" in markdown


def test_a_note_typed_over_a_picture_stays_even_where_junk_read_there_holds_fewer_unknown_words() -> None:
    # Found in review: the engine's reading of a text-layer row's place takes the row's place when
    # it holds fewer words outside the word list, but junk read in a picture is then dropped, and
    # neither was left. The note's last word is no word, as a font that reports letters wrongly leaves.
    note = Styled("หมายเหตุ ขฃฅ", x=150, y=SIGNED_AT + 25)
    junk = Boxed("การ", 150, SIGNED_AT + 12, SIGNED_AT + 30, confidence=0.4)
    lines: list[Line] = [*CLAUSES, SIGNED, SIGNATURE_LINE]
    source = pdf(Scan(lines, overlay=[note], dpi=100, colour=True))

    result = convert(source, ocr=FakeEngine([*lines, junk]), pictures=FakePictures(lines))

    assert "หมายเหตุ ขฃฅ" in result.output.decode("utf-8")


# The image as read


@pytest.mark.parametrize("turn", [90, 270])
def test_a_signature_on_a_sideways_scan_is_found_where_the_page_reads_upright(turn: Literal[90, 270]) -> None:
    source = pdf(Scan(SIGNING_PAGE, dpi=100, sideways=turn, colour=True))
    page = Sideways(SIGNING_PAGE, turn)

    result = convert(source, ocr=FakeEngine(page), pictures=FakePictures(page))

    assert page_texts(result.output.decode("utf-8")) == [SIGNED_PAGE]


def test_a_signature_on_an_upside_down_scan_is_found_where_the_page_reads_upright() -> None:
    source = pdf(Scan(SIGNING_PAGE, dpi=100, upside_down=True, colour=True))
    page = UpsideDown(SIGNING_PAGE)

    result = convert(source, ocr=FakeEngine(page), pictures=FakePictures(page))

    assert page_texts(result.output.decode("utf-8")) == [SIGNED_PAGE]


# Scans only


def test_the_finder_is_not_asked_about_a_text_page_or_a_page_drawn_as_shapes() -> None:
    finder = FakePictures()

    result = convert(
        pdf([*BEFORE, Picture("photo", 120, 80), *AFTER], Drawn(SIGNING_PAGE)), ocr=FakeEngine(SIGNING_PAGE), pictures=finder
    )

    assert finder.images == []
    assert page_texts(result.output.decode("utf-8")) == [*between_the_clauses("[รูปภาพ]"), SIGNED_PAGE]


def test_with_images_kept_the_finder_is_never_asked() -> None:
    finder = FakePictures(SIGNING_PAGE)

    convert(pdf(Scan(SIGNING_PAGE, dpi=100, colour=True)), ocr=FakeEngine(SIGNING_PAGE), pictures=finder, keep_images=True)

    assert finder.images == []


def test_a_missing_layout_model_is_reported_as_missing_ocr_models_are(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The OCR models are there, the layout model is not: `pdf-to-doc-models` fetches it.
    for model in (DETECTOR, THAI_RECOGNISER):
        (tmp_path / model.name).mkdir()
        for file in model.files:
            (tmp_path / model.name / file).touch()
    monkeypatch.setenv("PDF_TO_DOC_MODELS", str(tmp_path))

    with pytest.raises(ModelsMissing):
        default_picture_finder()


# Coloured ink beside a row to sign on, which the finder missed


def ink_markdown(*pages: Sequence[Line | Boxed]) -> list[str]:
    """The Markdown of colour scans of the pages, read by an engine that reads their text, with a
    finder that finds no picture, as the layout model misses a signature that touches its row."""
    drawn = ([line for line in page if not isinstance(line, Boxed)] for page in pages)
    source = pdf(*(Scan(lines, dpi=100, colour=True) for lines in drawn))
    return page_texts(convert(source, ocr=FakeEngine(*pages), pictures=NoPictures()).output.decode("utf-8"))


def test_a_blue_signature_beside_a_row_to_sign_on_the_finder_missed_is_a_signature() -> None:
    assert ink_markdown(SIGNING_PAGE) == [SIGNED_PAGE]


def test_a_red_stamp_beside_a_row_to_sign_on_the_finder_missed_is_a_stamp() -> None:
    page: list[Line] = [*CLAUSES, "", SIGNATURE_LINE, Picture("stamp", 70, 70, x=330)]

    assert ink_markdown(page) == ["".join(CLAUSES) + "\n\n" + SIGNATURE_LINE + "\n\n[ตราประทับ]"]


def test_a_highlighted_row_to_sign_on_gets_no_placeholder() -> None:
    # A highlighter's colour fills the row's box, and passes for ink but for the highlight test.
    page: list[Line] = [*CLAUSES, "", Styled(SIGNATURE_LINE, highlight=(1.0, 0.95, 0.3))]

    assert ink_markdown(page) == ["".join(CLAUSES) + "\n\n" + SIGNATURE_LINE]


def test_a_heading_printed_in_colour_away_from_any_row_to_sign_on_gets_no_placeholder() -> None:
    heading = "สัญญาให้ทุนโครงการ"
    page: list[Line] = [Styled(heading, size=22, colour=(0.1, 0.2, 0.7)), "", *CLAUSES, "", SIGNATURE_LINE]

    assert ink_markdown(page) == [f"{heading}\n\n" + "".join(CLAUSES) + "\n\n" + SIGNATURE_LINE]


def test_a_signature_the_finder_found_gets_one_placeholder_not_two() -> None:
    assert scan_markdown(SIGNING_PAGE) == [SIGNED_PAGE]


def test_a_signature_inside_a_region_found_behind_the_text_is_still_a_signature() -> None:
    # Seen on a sample's signing page: the layout model took the whole signature block, its rows of
    # print and all, for one image. That is the page behind the text, which gets no placeholder, so the
    # blue ink inside it is still a signature.
    block: list[Line] = [*CLAUSES, "", SIGNATURE, SIGNATURE_LINE, "(นายสมชาย ใจดี)", "ตำแหน่ง ผู้อำนวยการ"]
    behind = Picture("photo", 460, 130, y=TOP + 22 * len(CLAUSES) + 2)
    finder = FakePictures([behind])
    source = pdf(Scan(block, dpi=100, colour=True))

    [page] = page_texts(convert(source, ocr=FakeEngine(block), pictures=finder).output.decode("utf-8"))

    assert page.count("[ลายเซ็น]") == 1
    assert "[รูปภาพ]" not in page


def test_the_finder_is_asked_once_a_scan() -> None:
    finder = FakePictures(SIGNING_PAGE, SIGNING_PAGE)
    source = pdf(Scan(SIGNING_PAGE, dpi=100), ["หน้าที่มีข้อความ"], Scan(SIGNING_PAGE, dpi=100))

    convert(source, ocr=FakeEngine(SIGNING_PAGE, SIGNING_PAGE), pictures=finder)

    assert len(finder.images) == 2
