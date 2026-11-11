"""Page furniture on OCR pages: headers, footers and page numbers that OCR reads a little differently
on each page, or that sit a little further from the edge than the band, are removed; content that
repeats is kept."""

from collections.abc import Sequence

from fake_ocr import Boxed, FakeEngine, Line, Unsure
from markdown_reader import page_texts
from pdf_builder import FONT_SIZE, Scan, Styled, pdf

from pdf_to_doc import convert

BODY_TOP = 300  # the baseline of each page's body, well inside the edge bands
BODIES = [
    "ผู้รับทุนตกลงดำเนินงานตามแผน",
    "ผู้ให้ทุนจะจ่ายเงินเป็นงวด",
    "ผู้รับทุนต้องส่งรายงานทุกหกเดือน",
    "ผู้ให้ทุนจะตรวจรับงานภายในสามสิบวัน",
    "ผู้รับทุนต้องแจ้งการเปลี่ยนแปลงเป็นหนังสือ",
]


def body(number: int) -> Styled:
    return Styled(BODIES[number - 1], y=BODY_TOP)


def scans(*pages: Sequence[Line], overlays: Sequence[list[Styled]] = ()) -> list[str]:
    """The Markdown of scans that the engine reads as the given lines, each scan with its text layer's overlay."""
    layers = list(overlays) or [[] for _ in pages]
    source = pdf(*(Scan([BODIES[0]], overlay=overlay, dpi=50) for overlay in layers))
    return page_texts(convert(source, ocr=FakeEngine(*pages)).output.decode("utf-8"))


# Furniture OCR reads differently from page to page


def test_a_header_read_a_little_differently_on_each_page_is_removed() -> None:
    header = "สัญญาเลขที่ T-002 ฉบับแก้ไขครั้งที่หนึ่ง"
    pages = scans(
        [Styled(header, y=50), body(1)],
        # OCR drops a tone mark and reads the zeros as letters.
        [Styled("สัญญาเลขที T-OO2 ฉบับแก้ไขครั้งที่หนึ่ง", y=50), body(2)],
        [Styled(header, y=50), body(3)],
    )

    assert pages == BODIES[:3]


def test_a_header_read_differently_on_only_two_pages_is_kept() -> None:
    # Rows only alike must repeat on three pages, as body lines a word apart can be as alike.
    pages = scans(
        [Styled("สัญญาเลขที่ T-002 ฉบับแก้ไขครั้งที่หนึ่ง", y=50), body(1)],
        [Styled("สัญญาเลขที T-OO2 ฉบับแก้ไขครั้งที่หนึ่ง", y=50), body(2)],
    )

    assert pages == [
        f"สัญญาเลขที่ T-002 ฉบับแก้ไขครั้งที่หนึ่ง\n\n{BODIES[0]}",
        f"สัญญาเลขที T-<mark>OO2</mark> ฉบับแก้ไขครั้งที่หนึ่ง\n\n{BODIES[1]}",
    ]


def test_a_footer_read_on_one_line_with_junk_from_initials_beside_it_is_removed() -> None:
    footer = "ฉบับนี้จัดทำขึ้นสองฉบับมีข้อความตรงกัน"
    baseline = 800

    def initials(junk: str) -> Boxed:
        return Boxed(junk, x=430, top=baseline - 1.1 * FONT_SIZE, bottom=baseline + 0.4 * FONT_SIZE, confidence=0.4)

    pages = scans(
        [body(1), Styled(footer, y=baseline), initials("ศnสนรn")],
        [body(2), Styled(footer, y=baseline), initials("Ds ศ0ดนรทm")],
    )

    assert pages == BODIES[:2]


def test_rows_at_the_edge_that_differ_only_in_their_numbers_are_kept() -> None:
    pages = scans(
        [body(1), Styled("ยอดรวมทั้งสิ้นเป็นเงิน 1,200 บาท", y=800)],
        [body(2), Styled("ยอดรวมทั้งสิ้นเป็นเงิน 3,400 บาท", y=800)],
    )

    assert pages == [f"{BODIES[0]}\n\nยอดรวมทั้งสิ้นเป็นเงิน 1,200 บาท", f"{BODIES[1]}\n\nยอดรวมทั้งสิ้นเป็นเงิน 3,400 บาท"]


def test_body_lines_in_the_edge_band_that_differ_in_a_word_are_kept() -> None:
    # Found in testing: at 0.81 alike, these were taken for one header read two ways.
    pages = scans(
        [Styled("เนื้อหาหน้าแรกของสัญญา", y=90), body(1)],
        [Styled("เนื้อหาหน้าที่สองของสัญญา", y=90), body(2)],
    )

    assert pages == [f"เนื้อหาหน้าแรกของสัญญา\n\n{BODIES[0]}", f"เนื้อหาหน้าที่สองของสัญญา\n\n{BODIES[1]}"]


def test_long_body_lines_in_the_edge_band_a_word_apart_are_kept() -> None:
    # Found in review: these are 0.96 alike, more than many a misread letterhead.
    first = "ผู้รับทุนต้องส่งรายงานฉบับสมบูรณ์ภายในสามสิบวันนับแต่วันลงนาม"
    second = "ผู้รับทุนต้องส่งรายงานฉบับสมบูรณ์ภายในหกสิบวันนับแต่วันลงนาม"
    pages = scans([body(1), Styled(first, y=800)], [body(2), Styled(second, y=800)])

    assert pages == [f"{BODIES[0]}\n\n{first}", f"{BODIES[1]}\n\n{second}"]


def test_rows_at_the_edge_that_ocr_reads_unsurely_are_matched_whole() -> None:
    # A letterhead's words in a logo's type: OCR is sure of none of them.
    logo = "Northwind Foundation for Applied Research"
    pages = scans(
        [Unsure(Styled(logo, y=50)), body(1)],
        [Unsure(Styled("Northwlnd Foundatlon for Applied Research", y=50)), body(2)],
        [Unsure(Styled(logo, y=50)), body(3)],
    )

    assert pages == BODIES[:3]


# Furniture a little further from the edge than the band

FOOTER = "แบบรายงานผลการดำเนินงานประจำงวดของโครงการ"


def test_a_footer_above_the_bottom_band_with_its_page_number_at_the_end_is_removed_from_every_page() -> None:
    # A form's footer, as on a scan pasted into a larger page, numbered with no word for "page".
    pages = scans(
        [body(1), Styled(f"{FOOTER} 1", y=735)],
        [body(2), Styled(f"{FOOTER} 2", y=735)],
        [body(3), Styled(f"{FOOTER.replace('ดำเนินงาน', 'ดาเนินงาน')} 3", y=735)],
    )

    assert pages == BODIES[:3]


def test_page_numbers_and_a_header_line_just_outside_the_bands_are_removed() -> None:
    pages = scans(
        *(
            [Styled("สัญญาเลขที่ T-002", y=50), Styled("(ฉบับปรับปรุง มีนาคม 2567)", y=105), body(number), Styled(str(number), x=500, y=745)]
            for number in (1, 2, 3)
        )
    )

    assert pages == BODIES[:3]


def test_a_row_outside_the_bands_on_only_two_pages_is_kept() -> None:
    pages = scans([body(1), Styled(FOOTER, y=735)], [body(2), Styled(FOOTER, y=735)])

    assert pages == [f"{BODIES[0]}\n\n{FOOTER}", f"{BODIES[1]}\n\n{FOOTER}"]


def test_a_label_repeated_outside_the_bands_on_every_other_page_is_kept() -> None:
    # A form's label, such as one heading each researcher's résumé of two pages.
    label = "ประวัติและผลงานของผู้ร่วมงาน"
    pages = scans(
        *([Styled(label, y=130), body(number)] if number % 2 else [body(number)] for number in range(1, 6))
    )

    assert pages == [f"{label}\n\n{BODIES[0]}", BODIES[1], f"{label}\n\n{BODIES[2]}", BODIES[3], f"{label}\n\n{BODIES[4]}"]


def test_copies_of_one_page_keep_the_lines_they_repeat_near_the_edge() -> None:
    # Found in testing: the same form filled in for each of three people, or a page scanned twice.
    title, *lines = ["ใบรับเงินค่าตอบแทนผู้ประเมินโครงการ", "ได้รับเงินจากผู้ให้ทุนตามรายการดังนี้", "ค่าตอบแทนการประเมินข้อเสนอโครงการ"]
    names = ("นายสมชาย ใจดี", "นางสาวสมหญิง รักงาน", "นายประเสริฐ มั่นคง")

    def filled_in(name: str) -> list[Line]:
        return [Styled(title, y=150), *lines, Styled(name, y=400)]

    pages = scans(*(filled_in(name) for name in names))

    assert pages == [f"{title}{''.join(lines)}\n\n{name}" for name in names]


def test_numbers_ending_rows_outside_the_bands_that_do_not_follow_the_pages_are_kept() -> None:
    counts = ("25", "40", "13")
    pages = scans(*([body(number), Styled(f"จำนวนผู้เข้าร่วมทั้งหมด {count}", y=735)] for number, count in zip((1, 2, 3), counts)))

    assert pages == [f"{BODIES[number]}\n\nจำนวนผู้เข้าร่วมทั้งหมด {count}" for number, count in enumerate(counts)]


# Text from the text layer is matched exactly, as on a text page


def test_text_laid_over_scans_that_differs_a_little_is_kept() -> None:
    pages = scans(
        [body(1)],
        [body(2)],
        overlays=[[Styled("เอกสารแนบท้ายของฝ่ายผู้ว่าจ้าง", y=50)], [Styled("เอกสารแนบท้ายของฝ่ายผู้รับจ้าง", y=50)]],
    )

    assert pages == [f"เอกสารแนบท้ายของฝ่ายผู้ว่าจ้าง\n\n{BODIES[0]}", f"เอกสารแนบท้ายของฝ่ายผู้รับจ้าง\n\n{BODIES[1]}"]
