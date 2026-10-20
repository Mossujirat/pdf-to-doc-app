"""Placeholders: content the converter does not transcribe shows up as a short Thai label,
in Markdown and in DOCX, so the reader knows something was there and nothing is invented."""

from docx_reader import page_texts as docx_page_texts
from generate import CLAUSES, SIGNATURE, SIGNATURE_LINE
from markdown_reader import page_texts
from pdf_builder import Grid, Line, Picture, Styled, pdf

from pdf_to_doc import convert

# Enough body text for a text page; a page that is mostly picture is read with OCR.
BEFORE, AFTER = CLAUSES[:3], CLAUSES[3:]


def markdown_pages(*pages: list[Line]) -> list[str]:
    return page_texts(convert(pdf(*pages)).output.decode("utf-8"))


def docx_pages(*pages: list[Line]) -> list[str]:
    return docx_page_texts(convert(pdf(*pages), to="docx").output)


def between_the_clauses(placeholder: str) -> list[str]:
    """The Markdown of a page holding the placeholder between BEFORE and AFTER."""
    return ["".join(BEFORE) + f"\n\n{placeholder}\n\n" + "".join(AFTER)]


def test_an_image_on_a_text_page_becomes_an_image_placeholder_where_it_sits() -> None:
    assert markdown_pages([*BEFORE, Picture("photo", 120, 80), *AFTER]) == between_the_clauses("[รูปภาพ]")


# Signatures


def test_an_image_on_a_signature_line_becomes_a_signature_placeholder() -> None:
    pages = markdown_pages([*CLAUSES, "", SIGNATURE, SIGNATURE_LINE])

    assert pages == ["".join(CLAUSES) + "\n\n[ลายเซ็น]\n\n" + SIGNATURE_LINE]


def test_a_scribble_away_from_any_signature_line_is_only_an_image() -> None:
    # Unsure what it is, the converter does not guess.
    assert markdown_pages([*BEFORE, Picture("signature", 140, 45), *AFTER]) == between_the_clauses("[รูปภาพ]")


def test_a_word_that_only_contains_sign_does_not_make_a_signature_line() -> None:
    # Found in review: "designed" matched "signed".
    pages = markdown_pages([*CLAUSES, "", SIGNATURE, "Cover designed by the research office"])

    assert pages == ["".join(CLAUSES) + "\n\n[รูปภาพ]\n\nCover designed by the research office"]


def test_a_large_picture_above_a_signature_line_is_only_an_image() -> None:
    # Found in review: a signature is small.
    photo = Picture("photo", 300, 150, overlap=14)

    pages = markdown_pages([*CLAUSES, "", photo, SIGNATURE_LINE])

    assert pages == ["".join(CLAUSES) + "\n\n[รูปภาพ]\n\n" + SIGNATURE_LINE]


# Stamps


def test_a_round_coloured_mark_becomes_a_stamp_placeholder() -> None:
    assert markdown_pages([*BEFORE, Picture("stamp", 70, 70), *AFTER]) == between_the_clauses("[ตราประทับ]")


def test_a_stamp_pressed_over_a_signature_line_is_still_a_stamp() -> None:
    stamp = Picture("stamp", 70, 70, x=150, overlap=30)

    pages = markdown_pages([*CLAUSES, "", stamp, SIGNATURE_LINE])

    assert pages == ["".join(CLAUSES) + "\n\n[ตราประทับ]\n\n" + SIGNATURE_LINE]


def test_a_stamp_pressed_over_a_whole_signature_block_is_still_a_stamp() -> None:
    # Found in review: with three rows printed over it, it was taken for the page behind the text.
    stamp = Picture("stamp", 70, 70, x=90, overlap=66)

    result = convert(pdf([*CLAUSES, "", stamp, "ลงชื่อ ................", "(นายสมชาย ใจดี)", "ผู้อำนวยการ"]))

    assert result.summary.placeholder_count("stamp") == 1


def test_a_round_pie_chart_is_not_a_stamp() -> None:
    # Found in review: a stamp is a ring, not a filled round.
    assert markdown_pages([*BEFORE, Picture("chart", 70, 70), *AFTER]) == between_the_clauses("[รูปภาพ]")


# Images that are not placeholders, or are placed after a table


def test_a_thin_rule_or_a_tiny_ornament_drawn_as_an_image_gets_no_placeholder() -> None:
    pages = markdown_pages([*BEFORE, Picture("photo", 400, 2), Picture("photo", 6, 6), *AFTER])

    assert pages == ["".join(BEFORE) + "\n\n" + "".join(AFTER)]


def test_an_image_inside_a_table_cell_is_placed_right_after_the_table() -> None:
    grid = Grid(rows=(("ตำแหน่ง", "ลายมือ"), ("ผู้ให้ทุน", "")), widths=(200, 200), y=200)
    in_cell = Picture("photo", 60, 20, x=290, y=214)

    pages = markdown_pages([*CLAUSES, grid, in_cell, Styled("ทั้งนี้ตามที่ตกลงกัน", y=320)])

    assert pages == [
        "".join(CLAUSES) + "\n\n| ตำแหน่ง | ลายมือ |\n| --- | --- |\n| ผู้ให้ทุน |  |\n\n[รูปภาพ]\n\nทั้งนี้ตามที่ตกลงกัน"
    ]


# Page furniture

LOGO = Picture("photo", 60, 30, y=30)
BODY: list[Line] = [Styled(CLAUSES[0], y=160), *CLAUSES[1:]]


def test_an_image_repeated_at_the_edge_of_several_pages_is_page_furniture() -> None:
    # Initials signed at the foot of every page move a little from page to page.
    initials = [Picture("signature", 66, 17, x=x, y=y) for x, y in ((478, 766), (469, 759), (481, 745))]

    pages = markdown_pages([LOGO, *BODY, initials[0]], [LOGO, *BODY, initials[1]], [LOGO, *BODY, initials[2]])

    assert pages == ["".join(CLAUSES)] * 3


def test_images_of_one_size_at_different_places_near_the_edge_are_kept() -> None:
    # Found in review: two stamps at the foot of two signing pages were taken for furniture.
    pages = markdown_pages(
        [*BODY, Picture("stamp", 70, 70, x=80, y=740)], [*BODY, Picture("stamp", 70, 70, x=400, y=740)]
    )

    assert pages == ["".join(CLAUSES) + "\n\n[ตราประทับ]"] * 2


def test_an_image_near_the_edge_of_only_one_page_is_kept() -> None:
    pages = markdown_pages([LOGO, *BODY], BODY)

    assert pages == ["[รูปภาพ]\n\n" + "".join(CLAUSES), "".join(CLAUSES)]


# The summary


def test_the_summary_counts_placeholders_by_kind() -> None:
    stamp = Picture("stamp", 70, 70, x=330)

    result = convert(pdf([*BEFORE, Picture("photo", 120, 80), *AFTER], [*CLAUSES, "", SIGNATURE, SIGNATURE_LINE, "", stamp]))

    counts = {kind: result.summary.placeholder_count(kind) for kind in ("image", "signature", "stamp", "handwriting")}
    assert counts == {"image": 1, "signature": 1, "stamp": 1, "handwriting": 0}
    assert result.summary.headline().endswith(" ส่วนที่ไม่ได้ถอดเป็นข้อความ: รูปภาพ 1 จุด, ลายเซ็น 1 จุด, ตราประทับ 1 จุด")


def test_a_summary_without_placeholders_does_not_mention_them() -> None:
    result = convert(pdf(CLAUSES))

    assert result.summary.placeholder_count("image") == 0
    assert "ไม่ได้ถอด" not in result.summary.headline()


# DOCX


def test_the_docx_has_the_placeholder_as_a_paragraph_of_its_own() -> None:
    pages = docx_pages([*BEFORE, Picture("photo", 120, 80), *AFTER])

    assert pages == ["".join(BEFORE) + "\n[รูปภาพ]\n" + "".join(AFTER)]


def test_the_docx_marks_a_signature_on_its_signature_line() -> None:
    pages = docx_pages([*CLAUSES, "", SIGNATURE, SIGNATURE_LINE])

    assert pages == ["".join(CLAUSES) + "\n[ลายเซ็น]\n" + SIGNATURE_LINE]
