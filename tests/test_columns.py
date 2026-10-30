"""The order a text page's rows are read in, where the page sets text side by side."""

from pdf_to_doc.columns import in_reading_order
from pdf_to_doc.layout import PageRows, Row

SIZE = 14.0


def row(text: str, x0: float, x1: float, baseline: float) -> Row:
    return Row(text=text, x0=x0, y0=baseline - SIZE, x1=x1, y1=baseline + 4, size=SIZE)


def test_a_page_drawn_one_column_after_the_other_keeps_its_drawing_order() -> None:
    # As on a real signing page: two signature blocks whose signing lines are long enough to
    # be read as columns, drawn one after the other, and a contract number at the foot of the
    # page drawn before them. Taken by position, the number would move to the end.
    blocks = [
        [
            "ลงชื่อ ......................................",
            "(นายสมชาย ใจดี)",
            "ผู้อำนวยการศูนย์วิจัยและพัฒนาเทคโนโลยี",
            "สำนักงานพัฒนาวิทยาศาสตร์และเทคโนโลยี",
        ],
        [
            "ลงชื่อ ......................................",
            "(นางสาวสมหญิง รักดี)",
            "หัวหน้าโครงการวิจัยและพัฒนาเทคโนโลยี",
            "สำนักงานพัฒนาวิทยาศาสตร์และเทคโนโลยี",
        ],
    ]
    drawn = [
        row("สัญญาเลขที่ 123/2567", 64, 518, 790),
        *(
            row(text, x, x + 260, 640 + 20 * number)
            for x, block in zip((20, 300), blocks)
            for number, text in enumerate(block)
        ),
    ]
    page = PageRows(rows=tuple(drawn), width=595, height=842)

    assert in_reading_order(page) == page
