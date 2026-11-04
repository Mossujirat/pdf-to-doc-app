"""Check boxes on OCR pages: a ticked box comes out as ☒ and an empty one as ☐, before the text
it qualifies, in both outputs. OCR reads no text in a box, so they are found in the page image."""

from docx_reader import page_texts as docx_page_texts
from fake_ocr import Boxed, FakeEngine
from markdown_reader import page_texts
from pdf_builder import TOP, CheckBox, CheckMark, Drawn, Grid, Scan, Styled, laid_out_grid, pdf

from pdf_to_doc import convert

# Lines that both the PDF builder and the fake engine lay out.
Drawable = str | Styled | Grid | CheckBox


def scanned_page(*lines: Drawable) -> str:
    """The Markdown of a scan of the lines, which the engine reads all but the check boxes of."""
    [page] = page_texts(convert(pdf(Scan(list(lines), dpi=150)), ocr=FakeEngine(list(lines))).output.decode("utf-8"))
    return page


def form() -> list[Drawable]:
    """A row of a form: its label, then a ticked box before one choice and an empty one before another."""
    return [
        Styled("ประเภทโครงการ", size=12, y=TOP),
        CheckBox(180, TOP, "tick"),
        Styled("โครงการเดี่ยว", size=12, x=195, y=TOP),
        CheckBox(285, TOP, "none"),
        Styled("ชุดโครงการ", size=12, x=300, y=TOP),
    ]


def test_ticked_and_empty_boxes_on_a_form_come_out_before_the_choices_they_qualify() -> None:
    page = scanned_page(*form())

    assert page == "ประเภทโครงการ ☒ โครงการเดี่ยว ☐ ชุดโครงการ"


def test_boxes_in_a_ruled_tables_cells_come_out_in_their_cells() -> None:
    # As the sample contract shares out the rights to each result of a project; its boxes are about
    # two thirds as tall as a line of its text, here 16 points.
    grid = Grid(rows=(("ผลงาน", "ผู้ให้ทุน", "ผู้รับทุน"), ("ต้นแบบกาวชีวภาพ", "", ""), ("สูตรกาวชีวภาพ", "", "")), widths=(200, 90, 90), y=TOP)
    marks: dict[tuple[int, int], CheckMark] = {(1, 1): "none", (1, 2): "tick", (2, 1): "tick", (2, 2): "tick"}
    cells = [cell.rect for cell in laid_out_grid(grid, TOP).cells]  # row by row
    boxes = [
        CheckBox(rect.x0 + rect.width / 2 - 8, rect.y0 + rect.height / 2 + 8, mark, size=16)
        for (row, column), mark in marks.items()
        for rect in [cells[row * len(grid.widths) + column]]
    ]

    page = scanned_page(grid, *boxes)

    assert page == (
        "| ผลงาน | ผู้ให้ทุน | ผู้รับทุน |\n| --- | --- | --- |\n| ต้นแบบกาวชีวภาพ | ☐ | ☒ |\n| สูตรกาวชีวภาพ | ☒ | ☒ |"
    )


def test_a_box_with_a_speck_in_it_is_ticked_but_uncertain() -> None:
    # Something is in it, too little to call a tick: the reader checks.
    page = scanned_page(Styled("สถานะ", size=12, y=TOP), CheckBox(120, TOP, "smudge"), Styled("วิสาหกิจขนาดกลาง", size=12, x=135, y=TOP))

    assert page == "สถานะ <mark>☒</mark> วิสาหกิจขนาดกลาง"


def test_the_engines_own_reading_of_a_tick_gives_way_to_the_box() -> None:
    # PaddleOCR read some ticks as "V" or "√", boxed apart from the text.
    lines: list[Drawable] = [Styled("สถานะ", size=12, y=TOP), CheckBox(120, TOP, "tick"), Styled("วิสาหกิจขนาดกลาง", size=12, x=135, y=TOP)]
    tick = Boxed("V", x=121, top=TOP - 10, bottom=TOP - 1, confidence=0.99)

    [page] = page_texts(convert(pdf(Scan(lines, dpi=150)), ocr=FakeEngine([*lines, tick])).output.decode("utf-8"))

    assert page == "สถานะ ☒ วิสาหกิจขนาดกลาง"


def test_a_box_the_engine_took_into_the_text_around_it_comes_out_where_it_sits() -> None:
    # PaddleOCR read "ระยะเวลาโครงการ ☑ 12 เดือน" as one box, "ระยะเวลาโครงการ12 เดือน", the box dropped.
    scanned: list[Drawable] = [
        Styled("ระยะเวลาโครงการ", size=12, y=TOP),
        CheckBox(166, TOP, "tick"),
        Styled("12 เดือน", size=12, x=181, y=TOP),
    ]
    read = Styled("ระยะเวลาโครงการ12 เดือน", size=12, y=TOP)

    [page] = page_texts(convert(pdf(Scan(scanned, dpi=150)), ocr=FakeEngine([read])).output.decode("utf-8"))

    assert page == "ระยะเวลาโครงการ ☒ 12 เดือน"


# What is no check box: read as it was.


def test_square_letters_and_digits_and_a_qr_codes_corners_are_no_check_boxes() -> None:
    # A bold "0" or "D" among the letters of a word, and a QR code's corner: a square with a block in it.
    lines: list[Drawable] = [
        Styled("ภ.พ.20 NSTDA DOCKET", size=28, y=TOP + 20),
        Styled("สแกนเพื่ออ่านประกาศ", size=12, y=TOP + 60),
    ]
    corner = CheckBox(300, TOP + 60, "block", size=20)

    page = scanned_page(*lines, corner)

    assert "☐" not in page and "☒" not in page


def test_a_row_of_digit_boxes_is_no_row_of_check_boxes() -> None:
    # A tax number written a digit to a box, the boxes side by side.
    digits = Grid(rows=(tuple("0105556012345"),), widths=(28,) * 13, y=TOP)

    page = scanned_page(Styled("เลขประจำตัวผู้เสียภาษี", size=12, y=TOP - 30), digits)

    assert "☐" not in page and "☒" not in page


def test_the_docx_shows_the_boxes_too() -> None:
    lines = form()

    [page] = docx_page_texts(convert(pdf(Scan(lines, dpi=150)), to="docx", ocr=FakeEngine(lines)).output)

    assert page == "ประเภทโครงการ ☒ โครงการเดี่ยว ☐ ชุดโครงการ"


def test_digits_written_a_digit_to_a_box_are_kept_and_their_boxes_are_no_check_boxes() -> None:
    # A postcode in boxes set apart, the engine reading each digit: a box it reads a character in
    # writes that character, and a row of boxes side by side is a row of such boxes.
    digits = "10400"
    lines: list[Drawable] = [Styled("รหัสไปรษณีย์", size=12, y=TOP)]
    for number, digit in enumerate(digits):
        x = 140 + number * 20
        lines += [CheckBox(x, TOP + 2, "none", size=13), Styled(digit, size=12, x=x + 3.5, y=TOP)]

    page = scanned_page(*lines)

    assert "☐" not in page and "☒" not in page
    assert [character for character in page if character.isdigit()] == list(digits)


def test_a_box_with_its_choice_set_close_beside_it_is_still_found() -> None:
    # 2.5 points from it, a fifth of its side: the sample contract's boxes stood that far from their text, or further.
    page = scanned_page(Styled("สถานะ", size=12, y=TOP), CheckBox(120, TOP, "tick"), Styled("วิสาหกิจขนาดกลาง", size=12, x=134.5, y=TOP))

    assert page == "สถานะ ☒ วิสาหกิจขนาดกลาง"


def test_boxes_on_a_page_a_pdf_printer_drew_as_shapes_are_found_too() -> None:
    lines = form()

    [page] = page_texts(convert(pdf(Drawn(lines)), ocr=FakeEngine(lines)).output.decode("utf-8"))

    assert page == "ประเภทโครงการ ☒ โครงการเดี่ยว ☐ ชุดโครงการ"


def test_a_tick_the_engine_read_into_the_text_beside_its_box_is_left_out() -> None:
    # PaddleOCR read the tick as "√" at the start of the choice's box.
    scanned: list[Drawable] = [Styled("สถานะ", size=12, y=TOP), CheckBox(120, TOP, "tick"), Styled("วิสาหกิจขนาดกลาง", size=12, x=135, y=TOP)]
    read = [Styled("สถานะ", size=12, y=TOP), Styled("√วิสาหกิจขนาดกลาง", size=12, x=120, y=TOP)]

    [page] = page_texts(convert(pdf(Scan(scanned, dpi=150)), ocr=FakeEngine(read)).output.decode("utf-8"))

    assert page == "สถานะ ☒ วิสาหกิจขนาดกลาง"


def test_a_box_whose_place_in_the_text_around_it_is_unclear_is_uncertain() -> None:
    # The engine took the box into a run of letters with no word starting near it.
    scanned: list[Drawable] = [Styled("ABCDEFGHIJK", size=12, y=TOP), CheckBox(140, TOP, "tick"), Styled("LMNOPQRSTUV", size=12, x=155, y=TOP)]
    read = Styled("ABCDEFGHIJKLMNOPQRSTUV", size=12, y=TOP)

    [page] = page_texts(convert(pdf(Scan(scanned, dpi=150)), ocr=FakeEngine([read])).output.decode("utf-8"))

    assert "<mark>☒</mark>" in page
