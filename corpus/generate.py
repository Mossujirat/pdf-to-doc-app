"""Generates the synthetic corpus: small PDFs whose reference text is known exactly.

Each page is described twice: the lines to draw, which may carry damage such as
sara am stored as two characters, and the reference text a reader sees. A scanned
page draws its lines as an image at 200 dpi, slightly askew and with mild grain.
Run `uv run python corpus/generate.py` after changing a document below, and commit the result.
"""

import shutil
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import word_builder as word
from pdf_builder import (
    LINE_HEIGHT,
    NIRAMIT,
    SARABUN,
    TOP,
    Cell,
    Drawn,
    Grid,
    Line,
    Picture,
    Rotated,
    Scan,
    Spaced,
    Styled,
    pdf,
    remapped,
)

from pdf_to_doc.quality import reference_file_name

SYNTHETIC = Path(__file__).parent / "synthetic"
# Scans damaged on purpose, for measuring how much of what OCR misreads is marked as
# uncertain text. They are kept apart because OCR is expected to get them wrong.
DEGRADED = Path(__file__).parent / "degraded"


@dataclass(frozen=True)
class SyntheticPage:
    lines: Sequence[Line] | Scan | Rotated | Drawn
    reference: str


@dataclass(frozen=True)
class SyntheticDocument:
    name: str
    font_file: Path
    pages: tuple[SyntheticPage, ...]
    # Characters the fonts' text layer reports as something else, as broken or legacy fonts do.
    remap: dict[str, str] | None = None


# A coarse ruled table, as some budgets are drawn: several printed lines share one cell.
# Items stacked beside their amounts are sub-rows; items beside one total keep their
# line breaks; a wrapped description is one sentence.
COARSE_TABLE = Grid(
    rows=(
        ("หมวดรายจ่าย", "รายการ", "จำนวนเงิน"),
        ("ค่าดำเนินงาน", "ค่าวัสดุสำนักงาน\nค่าถ่ายเอกสาร\nค่าไปรษณีย์", "12,000\n3,500\n1,200"),
        ("ค่าครุภัณฑ์", "เครื่องคอมพิวเตอร์\nเครื่องพิมพ์", "53,900"),
        ("ค่าเดินทาง", "ค่าเช่ารถและค่าน้ำมันเชื้อเพลิง\nสำหรับการลงพื้นที่", "15,000"),
    ),
    widths=(110, 210, 100),
)
COARSE_TABLE_REFERENCE = (
    "<table>\n"
    "<tr><td>หมวดรายจ่าย</td><td>รายการ</td><td>จำนวนเงิน</td></tr>\n"
    '<tr><td rowspan="3">ค่าดำเนินงาน</td><td>ค่าวัสดุสำนักงาน</td><td>12,000</td></tr>\n'
    "<tr><td>ค่าถ่ายเอกสาร</td><td>3,500</td></tr>\n"
    "<tr><td>ค่าไปรษณีย์</td><td>1,200</td></tr>\n"
    "<tr><td>ค่าครุภัณฑ์</td><td>เครื่องคอมพิวเตอร์<br>เครื่องพิมพ์</td><td>53,900</td></tr>\n"
    "<tr><td>ค่าเดินทาง</td><td>ค่าเช่ารถและค่าน้ำมันเชื้อเพลิงสำหรับการลงพื้นที่</td><td>15,000</td></tr>\n"
    "</table>"
)


DOCUMENTS = (
    SyntheticDocument(
        name="thai-justified",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    # Justified text: character clusters set apart with extra room.
                    Spaced(("ผู้", "รั", "บ", "ทุ", "น", "ต", "ก", "ล", "ง", "ดำ", "เ", "นิ", "น"), gap=4),
                    Spaced(("ง", "า", "น", "ต", "า", "ม", "แ", "ผ", "น"), gap=6),
                    "",
                    "สัญญาให้ทุนโครงการพัฒนา",
                    "กาวชีวภาพจากกากถั่วเหลือง ",
                    "และลิกนินสำหรับอุตสาหกรรมไม้",
                ],
                reference=(
                    "ผู้รับทุนตกลงดำเนินงานตามแผน\n\n"
                    "สัญญาให้ทุนโครงการพัฒนากาวชีวภาพจากกากถั่วเหลือง และลิกนินสำหรับอุตสาหกรรมไม้"
                ),
            ),
        ),
    ),
    SyntheticDocument(
        name="thai-english-wrap",
        font_file=NIRAMIT,
        pages=(
            SyntheticPage(
                lines=[
                    "พัฒนาระบบเศรษฐกิจชีวภาพ",
                    "Bio-Circular-Green Economy",
                    "ในด้านพลังงานสะอาด",
                    "",
                    "แผนระยะ long-",
                    "term สำหรับปี 2567-",
                    "2568",
                    "",
                    # Words set apart without space characters.
                    Spaced(("โครงการ", "BCG", "ระยะที่", "2"), gap=6),
                ],
                reference=(
                    "พัฒนาระบบเศรษฐกิจชีวภาพ Bio-Circular-Green Economy ในด้านพลังงานสะอาด\n\n"
                    "แผนระยะ long-term สำหรับปี 2567-2568\n\n"
                    "โครงการ BCG ระยะที่ 2"
                ),
            ),
        ),
    ),
    SyntheticDocument(
        name="thai-character-repair",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    # Sara am stored as nikhahit + sara aa, and as sara aa + nikhahit.
                    "การท\u0e4d\u0e32งานร่วมกัน ท\u0e32\u0e4dให้ดี",
                    "",
                    # Mai ek stored before mai han-akat.
                    "ท\u0e48\u0e31วไป",
                    "",
                    # Stray spaces before a tone mark and before sara am.
                    "เพิ \u0e48มความร่วมมือ ท \u0e33งาน",
                ],
                reference=(
                    "การท\u0e33งานร่วมกัน ท\u0e33ให้ดี\n\n"
                    "ท\u0e31\u0e48วไป\n\n"
                    "เพิ\u0e48มความร่วมมือ ท\u0e33งาน"
                ),
            ),
        ),
    ),
    SyntheticDocument(
        name="page-structure",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40),
                    Styled("สัญญาให้ทุนโครงการ", size=22, y=100),
                    Styled("ข้อกำหนดทั่วไป", size=18),
                    "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุน",
                    "เพื่อดำเนินโครงการตามแผน",
                    "",
                    "เอกสารแนบท้ายสัญญามีดังนี้",
                    "1. เงื่อนไขของสัญญา",
                    "2. ขอบเขตของการดำเนินงาน",
                    "๓. ข้อตกลงด้านการเงิน",
                    Styled("สัญญาเลขที่ T-001 หน้าที่ 1/2", size=14, y=800),
                ],
                reference=(
                    "# สัญญาให้ทุนโครงการ\n\n"
                    "## ข้อกำหนดทั่วไป\n\n"
                    "ผู้ให้ทุนตกลงให้ทุนแก่ผู้รับทุนเพื่อดำเนินโครงการตามแผน\n\n"
                    "เอกสารแนบท้ายสัญญามีดังนี้\n\n"
                    "- 1. เงื่อนไขของสัญญา\n"
                    "- 2. ขอบเขตของการดำเนินงาน\n"
                    "- ๓. ข้อตกลงด้านการเงิน"
                ),
            ),
            SyntheticPage(
                lines=[
                    Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40),
                    Styled("การจ่ายเงิน", size=18, y=100),
                    "ผู้ให้ทุนจะจ่ายเงินเป็นงวด",
                    Styled("ย่อหน้าใหม่เริ่มด้วยการย่อเข้า", x=108),
                    "และต่อในบรรทัดถัดไป",
                    "",
                    # Rows set out with tab stops, like a list of appendices.
                    Spaced(("ภาคผนวก 1", "เงื่อนไขของสัญญา", "จำนวน 7 หน้า"), gap=40),
                    Spaced(("ภาคผนวก 2", "ขอบเขตของงาน", "จำนวน 54 หน้า"), gap=40),
                    Styled("สัญญาเลขที่ T-001 หน้าที่ 2/2", size=14, y=800),
                ],
                reference=(
                    "## การจ่ายเงิน\n\n"
                    "ผู้ให้ทุนจะจ่ายเงินเป็นงวด\n\n"
                    "ย่อหน้าใหม่เริ่มด้วยการย่อเข้าและต่อในบรรทัดถัดไป\n\n"
                    "ภาคผนวก 1 เงื่อนไขของสัญญา จำนวน 7 หน้า\n\n"
                    "ภาคผนวก 2 ขอบเขตของงาน จำนวน 54 หน้า"
                ),
            ),
            SyntheticPage(
                lines=[
                    Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40),
                    Styled("ภาคผนวก ๑", size=22, y=100),
                    Styled("รายงานที่ต้องส่ง", bold=True),
                    "",
                    "• รายงานความก้าวหน้า",
                    "• รายงานฉบับสมบูรณ์",
                    # Page numbering restarts in the appendix.
                    Styled("หน้าที่ ๑/๒", size=14, y=800),
                ],
                reference=(
                    "# ภาคผนวก ๑\n\n"
                    "### รายงานที่ต้องส่ง\n\n"
                    "- รายงานความก้าวหน้า\n"
                    "- รายงานฉบับสมบูรณ์"
                ),
            ),
            SyntheticPage(
                lines=[
                    Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40),
                    Styled("ผู้รับทุนต้องส่งรายงานตามกำหนดเวลา", y=100),
                    Styled("หน้าที่ ๒/๒", size=14, y=800),
                ],
                reference="ผู้รับทุนต้องส่งรายงานตามกำหนดเวลา",
            ),
        ),
    ),
    SyntheticDocument(
        name="clause-references",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    "ข้อกำหนดการจ่ายเงิน",
                    # A cross-reference whose number wraps onto the next line is no clause; a
                    # clause after one that ends on a full line is.
                    "1. ผู้รับทุนต้องชำระค่าปรับเป็นรายวันในอัตราที่ได้กำหนดไว้แล้วตามข้อ",
                    "4.2 ของสัญญานี้",
                    "2. ผู้ให้ทุนตกลงจ่ายเงินสนับสนุนโครงการวิจัยนี้รวมทั้งสิ้นเป็นเงินจำนวน",
                    # "ล่วงหน้า" ends in "หน้า", page, but refers to nothing.
                    "3. ผู้รับทุนต้องแจ้งการเปลี่ยนแปลงให้ทราบล่วงหน้า",
                    "4. ผู้ให้ทุนจะตรวจรับงานภายในสามสิบวัน",
                ],
                reference=(
                    "ข้อกำหนดการจ่ายเงิน\n\n"
                    "- 1. ผู้รับทุนต้องชำระค่าปรับเป็นรายวันในอัตราที่ได้กำหนดไว้แล้วตามข้อ 4.2 ของสัญญานี้\n"
                    "- 2. ผู้ให้ทุนตกลงจ่ายเงินสนับสนุนโครงการวิจัยนี้รวมทั้งสิ้นเป็นเงินจำนวน\n"
                    "- 3. ผู้รับทุนต้องแจ้งการเปลี่ยนแปลงให้ทราบล่วงหน้า\n"
                    "- 4. ผู้ให้ทุนจะตรวจรับงานภายในสามสิบวัน"
                ),
            ),
        ),
    ),
    SyntheticDocument(
        name="tables",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    "ผู้ให้ทุนจะจ่ายเงินเป็นงวดตามตารางนี้",
                    Grid(
                        rows=(
                            ("งวดที่", "กำหนดส่งงาน", "จำนวนเงิน"),
                            # Wrapped as Word wraps it: the next word would not fit on the first line.
                            ("๑", "ส่งรายงานความก้าวหน้าฉบับ\nที่หนึ่ง", "50,000"),
                            ("๒", "ส่งรายงานฉบับสมบูรณ์", "75,000"),
                        ),
                        widths=(70, 200, 100),
                    ),
                    "งบประมาณแยกตามปีมีดังนี้",
                    Grid(
                        rows=(
                            (Cell("รายการ", rowspan=2), Cell("งบประมาณ", colspan=2)),
                            ("ปีที่ ๑", "ปีที่ ๒"),
                            ("ค่าตอบแทนผู้วิจัย", "100,000", "120,000"),
                            ("ค่าวัสดุ", "-", "30,000"),
                        ),
                        widths=(150, 100, 100),
                    ),
                    "ทั้งนี้ไม่รวมภาษีมูลค่าเพิ่ม",
                ],
                reference=(
                    "ผู้ให้ทุนจะจ่ายเงินเป็นงวดตามตารางนี้\n\n"
                    "| งวดที่ | กำหนดส่งงาน | จำนวนเงิน |\n"
                    "| --- | --- | --- |\n"
                    "| ๑ | ส่งรายงานความก้าวหน้าฉบับที่หนึ่ง | 50,000 |\n"
                    "| ๒ | ส่งรายงานฉบับสมบูรณ์ | 75,000 |\n\n"
                    "งบประมาณแยกตามปีมีดังนี้\n\n"
                    "<table>\n"
                    '<tr><td rowspan="2">รายการ</td><td colspan="2">งบประมาณ</td></tr>\n'
                    "<tr><td>ปีที่ ๑</td><td>ปีที่ ๒</td></tr>\n"
                    "<tr><td>ค่าตอบแทนผู้วิจัย</td><td>100,000</td><td>120,000</td></tr>\n"
                    "<tr><td>ค่าวัสดุ</td><td>-</td><td>30,000</td></tr>\n"
                    "</table>\n\n"
                    "ทั้งนี้ไม่รวมภาษีมูลค่าเพิ่ม"
                ),
            ),
        ),
    ),
    SyntheticDocument(
        name="coarse-table",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=["งบประมาณโครงการแยกตามหมวดรายจ่าย", COARSE_TABLE],
                reference=f"งบประมาณโครงการแยกตามหมวดรายจ่าย\n\n{COARSE_TABLE_REFERENCE}",
            ),
        ),
    ),
    SyntheticDocument(
        name="multi-page",
        font_file=NIRAMIT,
        pages=(
            SyntheticPage(lines=["หน้าแรกของเอกสารทดสอบ"], reference="หน้าแรกของเอกสารทดสอบ"),
            SyntheticPage(lines=["หน้าที่สองของเอกสารทดสอบ"], reference="หน้าที่สองของเอกสารทดสอบ"),
        ),
    ),
)

STAMP = Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40)


def scanned(
    lines: Sequence[Line],
    overlay: list[Line] | None = None,
    seed: int = 0,
    sideways: Literal[0, 90, 270] = 0,
    upside_down: bool = False,
) -> Scan:
    return Scan(
        lines, overlay=overlay or [], dpi=200, angle=0.4, noise=6, seed=seed, sideways=sideways, upside_down=upside_down
    )


SCANNED_DOCUMENTS = (
    SyntheticDocument(
        name="scanned-page",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=scanned(
                    [
                        "ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้",
                        "ในสัญญาฉบับนี้ และส่งรายงานทุกหกเดือน",
                        "",
                        "โครงการ BCG Economy ระยะที่ 2 ปี 2567",
                        "",
                        "ค่าตอบแทนผู้วิจัย 100,000 บาท",
                    ],
                    seed=1,
                ),
                reference=(
                    "ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้ และส่งรายงานทุกหกเดือน\n\n"
                    "โครงการ BCG Economy ระยะที่ 2 ปี 2567\n\n"
                    "ค่าตอบแทนผู้วิจัย 100,000 บาท"
                ),
            ),
        ),
    ),
    SyntheticDocument(
        name="stamped-scans",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=scanned(
                    ["ผู้ให้ทุนจะจ่ายเงินเป็นงวด", "ตามความก้าวหน้าของงาน"],
                    overlay=[STAMP, Styled("หน้าที่ 1/2", size=14, y=800)],
                    seed=2,
                ),
                reference="ผู้ให้ทุนจะจ่ายเงินเป็นงวดตามความก้าวหน้าของงาน",
            ),
            SyntheticPage(
                lines=scanned(
                    ["ผู้รับทุนต้องส่งรายงานฉบับสมบูรณ์", "ภายในสามสิบวันหลังสิ้นสุดโครงการ"],
                    overlay=[STAMP, Styled("หน้าที่ 2/2", size=14, y=800)],
                    seed=3,
                ),
                reference="ผู้รับทุนต้องส่งรายงานฉบับสมบูรณ์ภายในสามสิบวันหลังสิ้นสุดโครงการ",
            ),
        ),
    ),
    SyntheticDocument(
        name="mixed-text-and-scan",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=["หน้านี้มีข้อความในไฟล์", "อ่านได้โดยไม่ต้องใช้ OCR"],
                reference="หน้านี้มีข้อความในไฟล์อ่านได้โดยไม่ต้องใช้ OCR",
            ),
            SyntheticPage(
                lines=scanned(["หน้านี้เป็นภาพสแกน", "ต้องอ่านด้วย OCR"], seed=4),
                reference="หน้านี้เป็นภาพสแกนต้องอ่านด้วย OCR",
            ),
        ),
    ),
)

CLAUSES = [
    "ผู้รับทุนตกลงจะดำเนินการวิจัยตามแผนงานที่ได้รับอนุมัติ",
    "และจะรายงานผลการดำเนินงานให้ผู้ให้ทุนทราบทุกหกเดือน",
    "โดยผู้ให้ทุนจะจ่ายเงินตามงวดที่กำหนดไว้ในสัญญา",
    "หากผู้รับทุนไม่สามารถดำเนินการได้ตามกำหนดเวลา",
    "ให้แจ้งผู้ให้ทุนเป็นหนังสือก่อนครบกำหนดอย่างน้อยสามสิบวัน",
]
# The clauses and a line with marks over its first and last words. An OCR page that is
# not a scan is rendered from the PDF, crisp; read crisp, this page lost its fifth line.
CRISP_PAGE = [*CLAUSES, "ผู้รับทุนต้องส่งงานตามกำหนดเวลาในตารางนี้", *CLAUSES[:2]]
# A font whose ToUnicode map reports sara aa as sara am, so that "การ" reads "กำร": the
# page looks right, but its text layer cannot be trusted, so it is read with OCR.
KAR_AS_KAM = {chr(0x0E32): chr(0x0E33)}

TEXT_LAYER_DOCUMENTS = (
    # A legacy Windows Thai font: marks over tall consonants and below the line
    # are shifted glyphs, reported as Private Use Area characters.
    SyntheticDocument(
        name="legacy-font",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=["ปิ่นโตของผู้ใหญ่บ้าน", "ทั้งปีนี้ไม่ได้ใช้เลย"],
                reference="ปิ่นโตของผู้ใหญ่บ้านทั้งปีนี้ไม่ได้ใช้เลย",
            ),
        ),
        remap={
            chr(0x0E34): chr(0xF701),  # sara i, shifted left
            chr(0x0E35): chr(0xF702),  # sara ii, shifted left
            chr(0x0E48): chr(0xF713),  # mai ek, shifted left
            chr(0x0E49): chr(0xF70B),  # mai tho, shifted down
            chr(0x0E31): chr(0xF710),  # mai han-akat, shifted left
            chr(0x0E0D): chr(0xF70F),  # yo ying without its lower part
        },
    ),
    SyntheticDocument(
        name="wrong-unicode-map",
        font_file=SARABUN,
        pages=(
            SyntheticPage(lines=CLAUSES, reference="".join(CLAUSES)),
            SyntheticPage(lines=CRISP_PAGE, reference="".join(CRISP_PAGE)),
        ),
        remap=KAR_AS_KAM,
    ),
    # Text drawn as shapes, with no text layer, as some PDF printers write it: read with OCR.
    SyntheticDocument(
        name="text-drawn-as-shapes",
        font_file=SARABUN,
        pages=(SyntheticPage(lines=Drawn(CRISP_PAGE), reference="".join(CRISP_PAGE)),),
    ),
)

SIGNATURE_LINE = "ลงชื่อ ................................................ ผู้ให้ทุน"
# A signature whose foot runs over the signature line after it.
SIGNATURE = Picture("signature", 140, 45, x=130, overlap=14)

PLACEHOLDER_DOCUMENTS = (
    # A signing page: a picture, a signature on its signature line, and a stamp.
    SyntheticDocument(
        name="placeholders",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    *CLAUSES,
                    "",
                    Picture("photo", 120, 70),
                    "",
                    SIGNATURE,
                    SIGNATURE_LINE,
                    "",
                    Picture("stamp", 70, 70, x=330),
                ],
                reference="".join(CLAUSES) + f"\n\n[รูปภาพ]\n\n[ลายเซ็น]\n\n{SIGNATURE_LINE}\n\n[ตราประทับ]",
            ),
        ),
    ),
)

SIGNING_PAGE: list[Line] = [
    STAMP,
    Styled("สัญญาให้ทุนโครงการ", size=22, y=100),
    *CLAUSES,
    "",
    "1. เงื่อนไขของสัญญา",
    "2. ขอบเขตของการดำเนินงาน",
    Grid(rows=(("งวดที่", "จำนวนเงิน"), ("๑", "50,000")), widths=(150, 150)),
    SIGNATURE,
    SIGNATURE_LINE,
    Picture("stamp", 70, 70, x=330),
    Styled("หน้าที่ 1/2", size=14, y=800),
]
CLOSING_LINE = "ทั้งนี้ให้เป็นไปตามระเบียบของผู้ให้ทุน"
PAYMENT_PAGE: list[Line] = [
    STAMP,
    Styled("การจ่ายเงิน", size=18, y=100),
    *CLAUSES,
    # Below 595 pt, where a page stored landscape ends before its rotation turns it upright.
    Styled(CLOSING_LINE, y=700),
    Styled("หน้าที่ 2/2", size=14, y=800),
]
# Notes typed over a scan, each placed so that its position on the page as stored,
# taken as a position on the page as shown, lies over lines of the scan.
NOTE_BELOW = "หมายเหตุ ผู้ให้ทุนอนุมัติให้ขยายเวลาแล้ว"
NOTE_ABOVE = "แก้ไขตามบันทึกข้อตกลงฉบับที่สอง"

# Pages stored landscape and turned upright by a page rotation, as some scanners save them.
ROTATED_DOCUMENTS = (
    SyntheticDocument(
        name="rotated-text-pages",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=Rotated(SIGNING_PAGE, 90),
                reference=(
                    "# สัญญาให้ทุนโครงการ\n\n"
                    + "".join(CLAUSES)
                    + "\n\n- 1. เงื่อนไขของสัญญา\n- 2. ขอบเขตของการดำเนินงาน\n\n"
                    "| งวดที่ | จำนวนเงิน |\n| --- | --- |\n| ๑ | 50,000 |\n\n"
                    f"[ลายเซ็น]\n\n{SIGNATURE_LINE}\n\n[ตราประทับ]"
                ),
            ),
            SyntheticPage(
                lines=Rotated(PAYMENT_PAGE, 270),
                reference="## การจ่ายเงิน\n\n" + "".join(CLAUSES) + f"\n\n{CLOSING_LINE}",
            ),
        ),
    ),
    SyntheticDocument(
        name="rotated-scans",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=Rotated(scanned(CLAUSES, overlay=[Styled(NOTE_BELOW, y=540)], seed=5), 270),
                reference="".join(CLAUSES) + f"\n\n{NOTE_BELOW}",
            ),
            SyntheticPage(
                lines=Rotated(
                    scanned([Styled(CLAUSES[0], y=300), *CLAUSES[1:]], overlay=[Styled(NOTE_ABOVE, y=200)], seed=6), 90
                ),
                reference=f"{NOTE_ABOVE}\n\n" + "".join(CLAUSES),
            ),
        ),
    ),
)

PRICES = (
    ("ลำดับ", "รายการ", "จำนวน", "ราคาต่อหน่วย", "จำนวนเงิน"),
    ("1", "ค่าตอบแทนผู้วิจัย", "12 เดือน", "8,000.00", "96,000.00"),
    ("2", "ค่าวัสดุและอุปกรณ์", "1 ชุด", "30,000.00", "30,000.00"),
    ("3", "ค่าเดินทางไปประชุม", "5 ครั้ง", "2,500.00", "12,500.00"),
)
# A price schedule as wide as a landscape sheet, and what a reader sees on it.
PRICE_SCHEDULE: list[str | Grid] = [
    "ตารางราคา (Price Schedule)",
    Grid(rows=PRICES, widths=(60, 230, 100, 130, 130)),
    "รวมทั้งสิ้น 138,500.00 บาท",
]
PRICE_SCHEDULE_REFERENCE = (
    "ตารางราคา (Price Schedule)\n\n"
    "| ลำดับ | รายการ | จำนวน | ราคาต่อหน่วย | จำนวนเงิน |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| 1 | ค่าตอบแทนผู้วิจัย | 12 เดือน | 8,000.00 | 96,000.00 |\n"
    "| 2 | ค่าวัสดุและอุปกรณ์ | 1 ชุด | 30,000.00 | 30,000.00 |\n"
    "| 3 | ค่าเดินทางไปประชุม | 5 ครั้ง | 2,500.00 | 12,500.00 |\n\n"
    "รวมทั้งสิ้น 138,500.00 บาท"
)

# Sideways pages: the price schedule printed across a tall page, turned each way.
SIDEWAYS_DOCUMENTS = (
    SyntheticDocument(
        name="sideways-scans",
        font_file=SARABUN,
        pages=(
            SyntheticPage(lines=scanned(PRICE_SCHEDULE, seed=7, sideways=90), reference=PRICE_SCHEDULE_REFERENCE),
            SyntheticPage(lines=scanned(PRICE_SCHEDULE, seed=8, sideways=270), reference=PRICE_SCHEDULE_REFERENCE),
        ),
    ),
)

# Ruled tables as contracts and their attachments hold them, for tables on OCR pages.
# Wrapped text fills its cell before it wraps, as Word wraps it.
PAYMENT_SCHEDULE = Grid(
    rows=(
        ("งวดที่", "รายละเอียดงานที่ส่งมอบ", "จำนวนเงิน (บาท)"),
        ("๑", "ส่งแผนการดำเนินงานและรายงาน\nการทบทวนวรรณกรรมที่เกี่ยวข้อง", Cell("150,000", align="right")),
        ("๒", "ส่งรายงานความก้าวหน้าพร้อมผล\nการทดลองเบื้องต้นของต้นแบบ", Cell("250,000", align="right")),
        ("๓", "ส่งรายงานฉบับสมบูรณ์พร้อมคู่มือ\nการใช้งานระบบ", Cell("100,000", align="right")),
    ),
    widths=(60, 230, 130),
)
PAYMENT_SCHEDULE_REFERENCE = (
    "| งวดที่ | รายละเอียดงานที่ส่งมอบ | จำนวนเงิน (บาท) |\n"
    "| --- | --- | --- |\n"
    "| ๑ | ส่งแผนการดำเนินงานและรายงานการทบทวนวรรณกรรมที่เกี่ยวข้อง | 150,000 |\n"
    "| ๒ | ส่งรายงานความก้าวหน้าพร้อมผลการทดลองเบื้องต้นของต้นแบบ | 250,000 |\n"
    "| ๓ | ส่งรายงานฉบับสมบูรณ์พร้อมคู่มือการใช้งานระบบ | 100,000 |"
)
BUDGET = Grid(
    rows=(
        (Cell("รายการ", rowspan=2), Cell("งบประมาณ (บาท)", colspan=2)),
        ("ปีที่ 1", "ปีที่ 2"),
        ("ค่าตอบแทนผู้วิจัย", Cell("240,000", align="right"), Cell("240,000", align="right")),
        ("ค่าวัสดุและอุปกรณ์", Cell("45,000", align="right"), Cell("30,000", align="right")),
        ("ค่าเดินทาง", Cell("12,000", align="right"), Cell("-", align="right")),
    ),
    widths=(170, 110, 110),
)
BUDGET_REFERENCE = (
    "<table>\n"
    '<tr><td rowspan="2">รายการ</td><td colspan="2">งบประมาณ (บาท)</td></tr>\n'
    "<tr><td>ปีที่ 1</td><td>ปีที่ 2</td></tr>\n"
    "<tr><td>ค่าตอบแทนผู้วิจัย</td><td>240,000</td><td>240,000</td></tr>\n"
    "<tr><td>ค่าวัสดุและอุปกรณ์</td><td>45,000</td><td>30,000</td></tr>\n"
    "<tr><td>ค่าเดินทาง</td><td>12,000</td><td>-</td></tr>\n"
    "</table>"
)
DATES = Grid(
    rows=(("วันลงนามในสัญญา", "วันเริ่มดำเนินงาน", "วันสิ้นสุดโครงการ"), ("1 มีนาคม 2568", "15 มีนาคม 2568", "14 มีนาคม 2569")),
    widths=(140, 140, 140),
)
DATES_REFERENCE = (
    "| วันลงนามในสัญญา | วันเริ่มดำเนินงาน | วันสิ้นสุดโครงการ |\n"
    "| --- | --- | --- |\n"
    "| 1 มีนาคม 2568 | 15 มีนาคม 2568 | 14 มีนาคม 2569 |"
)
# A page for each of them, with text around it, and what a reader sees on it.
RULED_TABLE_PAGES: list[tuple[list[str | Grid], str]] = [
    (
        ["ผู้ให้ทุนจะจ่ายเงินทุนเป็นสามงวดตามตารางนี้", PAYMENT_SCHEDULE, "ทั้งนี้ไม่รวมภาษีมูลค่าเพิ่ม"],
        f"ผู้ให้ทุนจะจ่ายเงินทุนเป็นสามงวดตามตารางนี้\n\n{PAYMENT_SCHEDULE_REFERENCE}\n\nทั้งนี้ไม่รวมภาษีมูลค่าเพิ่ม",
    ),
    (
        ["งบประมาณโครงการแยกตามปีงบประมาณ", BUDGET, "ผู้รับทุนต้องใช้เงินตามหมวดที่ได้รับอนุมัติเท่านั้น"],
        f"งบประมาณโครงการแยกตามปีงบประมาณ\n\n{BUDGET_REFERENCE}\n\nผู้รับทุนต้องใช้เงินตามหมวดที่ได้รับอนุมัติเท่านั้น",
    ),
    (
        ["ระยะเวลาดำเนินโครงการเป็นไปตามตารางนี้", DATES],
        f"ระยะเวลาดำเนินโครงการเป็นไปตามตารางนี้\n\n{DATES_REFERENCE}",
    ),
    (
        ["งบประมาณโครงการแยกตามหมวดรายจ่าย", COARSE_TABLE],
        f"งบประมาณโครงการแยกตามหมวดรายจ่าย\n\n{COARSE_TABLE_REFERENCE}",
    ),
]
RULED_TABLE_DOCUMENTS = (
    SyntheticDocument(
        name="ruled-table-scans",
        font_file=SARABUN,
        pages=tuple(
            SyntheticPage(lines=scanned(lines, seed=21 + number), reference=reference)
            for number, (lines, reference) in enumerate(RULED_TABLE_PAGES)
        ),
    ),
    # The same pages on OCR pages that are not scans: rendered from the PDF, rules and all.
    SyntheticDocument(
        name="ruled-tables-wrong-unicode-map",
        font_file=SARABUN,
        pages=tuple(SyntheticPage(lines=lines, reference=reference) for lines, reference in RULED_TABLE_PAGES),
        remap=KAR_AS_KAM,
    ),
    SyntheticDocument(
        name="ruled-tables-drawn-as-shapes",
        font_file=SARABUN,
        pages=tuple(SyntheticPage(lines=Drawn(lines), reference=reference) for lines, reference in RULED_TABLE_PAGES),
    ),
)



def unboxed(grid: Grid, boxed_rows: int = 0) -> Grid:
    """The table with only its first `boxed_rows` rows boxed: none for a table with no rules."""
    rows = tuple(
        tuple(replace(Cell(cell) if isinstance(cell, str) else cell, boxed=number < boxed_rows) for cell in row)
        for number, row in enumerate(grid.rows)
    )
    return replace(grid, rows=rows)


# Tables on scans that are seen but not fully ruled. A table whose header alone is boxed comes out
# as an incomplete table: its label, then its printed lines one by one. A table with no rules at
# all comes out one line per row with no label, as on text pages.
PRICE_LIST = Grid(
    rows=(
        ("ลำดับ", "รายการ", "จำนวนเงิน (บาท)"),
        ("1", "ค่าตอบแทนผู้วิจัย", Cell("96,000", align="right")),
        ("2", "ค่าวัสดุและอุปกรณ์", Cell("30,000", align="right")),
        ("3", "ค่าเดินทางไปประชุม", Cell("12,500", align="right")),
    ),
    widths=(60, 220, 140),
)
PRICE_LIST_ROWS = "ลำดับ รายการ จำนวนเงิน (บาท)\n\n1 ค่าตอบแทนผู้วิจัย 96,000\n\n2 ค่าวัสดุและอุปกรณ์ 30,000\n\n3 ค่าเดินทางไปประชุม 12,500"
UNRULED_DATES = replace(unboxed(DATES), widths=(160, 160, 160))
PART_RULED_TABLE_DOCUMENTS = (
    SyntheticDocument(
        name="boxed-header-table-scans",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=scanned(
                    ["ผู้ให้ทุนจะจ่ายเงินทุนเป็นสามงวดตามตารางนี้", unboxed(PAYMENT_SCHEDULE, 1), "ทั้งนี้ไม่รวมภาษีมูลค่าเพิ่ม"],
                    seed=31,
                ),
                reference=(
                    "ผู้ให้ทุนจะจ่ายเงินทุนเป็นสามงวดตามตารางนี้\n\n[ตารางอาจไม่สมบูรณ์]\n\n"
                    "งวดที่ รายละเอียดงานที่ส่งมอบ จำนวนเงิน (บาท)\n\n"
                    "๑ ส่งแผนการดำเนินงานและรายงาน 150,000\n\nการทบทวนวรรณกรรมที่เกี่ยวข้อง\n\n"
                    "๒ ส่งรายงานความก้าวหน้าพร้อมผล 250,000\n\nการทดลองเบื้องต้นของต้นแบบ\n\n"
                    "๓ ส่งรายงานฉบับสมบูรณ์พร้อมคู่มือ 100,000\n\nการใช้งานระบบ\n\n"
                    "ทั้งนี้ไม่รวมภาษีมูลค่าเพิ่ม"
                ),
            ),
            SyntheticPage(
                lines=scanned(["งบประมาณที่ขอรับการสนับสนุนมีดังนี้", unboxed(PRICE_LIST, 1)], seed=32),
                reference=f"งบประมาณที่ขอรับการสนับสนุนมีดังนี้\n\n[ตารางอาจไม่สมบูรณ์]\n\n{PRICE_LIST_ROWS}",
            ),
        ),
    ),
    SyntheticDocument(
        name="unruled-table-scans",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=scanned(
                    [
                        "งบประมาณที่ขอรับการสนับสนุนมีดังนี้",
                        unboxed(PRICE_LIST),
                        "ระยะเวลาดำเนินโครงการเป็นไปตามตารางนี้",
                        UNRULED_DATES,
                    ],
                    seed=33,
                ),
                reference=(
                    f"งบประมาณที่ขอรับการสนับสนุนมีดังนี้\n\n{PRICE_LIST_ROWS}\n\n"
                    "ระยะเวลาดำเนินโครงการเป็นไปตามตารางนี้\n\n"
                    "วันลงนามในสัญญา วันเริ่มดำเนินงาน วันสิ้นสุดโครงการ\n\n1 มีนาคม 2568 15 มีนาคม 2568 14 มีนาคม 2569"
                ),
            ),
        ),
    ),
)

# Pages set in two columns of body text, each paragraph whole in its column, and a
# cover sheet whose labels are set apart from their values.
THAI_COLUMNS_TITLE = "ข้อกำหนดและเงื่อนไขการให้ทุนวิจัย"
THAI_COLUMNS = (
    [
        [
            "สัญญาฉบับนี้ทำขึ้นระหว่างหน่วยงานผู้",
            "ให้ทุนกับมหาวิทยาลัยผู้รับทุน เพื่อ",
            "สนับสนุนโครงการวิจัยตามข้อเสนอที่",
            "แนบท้ายสัญญา และให้ถือเป็น",
            "ส่วนหนึ่งของสัญญานี้",
        ],
        [
            "ผู้รับทุนตกลงจะเริ่มดำเนินงานภายใน",
            "สามสิบวันนับแต่วันลงนาม และ",
            "ดำเนินงานให้แล้วเสร็จภายในสิบสอง",
            "เดือน หากไม่อาจดำเนินงานได้",
            "ตามกำหนดต้องแจ้งเป็นหนังสือ",
            "ล่วงหน้า",
        ],
    ],
    [
        [
            "ผู้ให้ทุนจะจ่ายเงินทุนเป็นสามงวด งวด",
            "แรกเมื่อลงนามในสัญญา งวดที่สองเมื่อ",
            "ได้รับรายงานความก้าวหน้า และงวด",
            "สุดท้ายเมื่อได้รับรายงานฉบับสมบูรณ์",
        ],
        [
            "ผู้รับทุนต้องใช้เงินทุนตามแผน",
            "งบประมาณที่ได้รับอนุมัติเท่านั้น และ",
            "เก็บหลักฐานการจ่ายเงินไว้ให้ผู้ให้ทุน",
            "ตรวจสอบได้ตลอดระยะเวลาของ",
            "โครงการ",
        ],
    ],
)
ENGLISH_COLUMNS_TITLE = "GENERAL TERMS AND CONDITIONS OF PURCHASE"
ENGLISH_COLUMNS = (
    [
        ["1.1 Agreement means these terms and conditions", "together with the purchase order and any schedules", "attached to it."],
        ["1.2 Supplier means the person or company from", "whom the Buyer purchases the goods or services in", "the order."],
        ["1.3 Deliverables means all documents, products and", "materials that the Supplier develops as part of the", "services."],
    ],
    [
        ["2.1 The Supplier shall deliver the goods to the", "address stated in the order on the agreed date,", "during normal business hours."],
        ["2.2 Each delivery shall come with a delivery note", "stating the order number and the type and quantity", "of the goods."],
        ["2.3 The Buyer shall pay correctly rendered invoices", "within thirty days of receiving them."],
    ],
)
COVER_SHEET_INTRO = "ผู้รับทุนขอยืนยันรายละเอียดของโครงการตามรายการต่อไปนี้"
COVER_SHEET = [
    ("ชื่อโครงการ", "การพัฒนาระบบติดตามงานวิจัยแบบออนไลน์"),
    ("หัวหน้าโครงการ", "นางสาวสมหญิง รักดี"),
    ("หน่วยงาน", "คณะวิศวกรรมศาสตร์ มหาวิทยาลัยตัวอย่าง"),
    ("ระยะเวลา", "สิบสองเดือนนับแต่วันลงนามในสัญญา"),
    ("งบประมาณ", "หนึ่งล้านสองแสนบาทถ้วน"),
]


def column_lines(
    columns: Sequence[list[list[str]]], xs: Sequence[float], size: float, pitch: float, *, across: bool = False
) -> list[Line]:
    """Each column's paragraphs line under line from the same top, a blank line between them.
    Drawn one column after the other, as Word draws them, or with `across`, a row at a time
    across the columns, as some PDF writers do."""
    placed: list[tuple[int, int, Styled]] = []  # each line's row, its column, and the line
    for column, (x, paragraphs) in enumerate(zip(xs, columns, strict=True)):
        slot = 0
        for paragraph in paragraphs:
            for text in paragraph:
                placed.append((slot, column, Styled(text, size=size, x=x, y=150 + slot * pitch)))
                slot += 1
            slot += 1
    if across:
        placed.sort(key=lambda line: line[:2])
    return [line for _, _, line in placed]


TWO_COLUMN_DOCUMENTS = (
    SyntheticDocument(
        name="two-column-scans",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=scanned(
                    [
                        Styled(THAI_COLUMNS_TITLE, size=18, bold=True, y=95, centered=True),
                        *column_lines(THAI_COLUMNS, xs=(72, 311), size=14, pitch=21),
                    ],
                    seed=11,
                ),
                reference="\n\n".join(
                    [THAI_COLUMNS_TITLE, *("".join(paragraph) for column in THAI_COLUMNS for paragraph in column)]
                ),
            ),
            SyntheticPage(
                lines=scanned(
                    [
                        Styled(ENGLISH_COLUMNS_TITLE, size=13, bold=True, y=95, centered=True),
                        *column_lines(ENGLISH_COLUMNS, xs=(72, 306), size=9.5, pitch=12.5),
                    ],
                    seed=12,
                ),
                reference=f"{ENGLISH_COLUMNS_TITLE}\n\n"
                + "\n".join(f"- {' '.join(clause)}" for column in ENGLISH_COLUMNS for clause in column),
            ),
            SyntheticPage(
                lines=scanned(
                    [
                        COVER_SHEET_INTRO,
                        "",
                        *(
                            Styled(text, x=x, y=TOP + (2 + row) * LINE_HEIGHT)
                            for row, (label, value) in enumerate(COVER_SHEET)
                            for x, text in ((72, label), (230, value))
                        ),
                    ],
                    seed=13,
                ),
                reference=f"{COVER_SHEET_INTRO}\n\n" + "\n".join(f"{label} {value}" for label, value in COVER_SHEET),
            ),
        ),
    ),
    # The scans' first page as a text page, drawn line by line across its columns.
    SyntheticDocument(
        name="two-column-drawn-across",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    Styled(THAI_COLUMNS_TITLE, size=18, bold=True, y=95, centered=True),
                    *column_lines(THAI_COLUMNS, xs=(72, 311), size=14, pitch=21, across=True),
                ],
                reference="\n\n".join(
                    [THAI_COLUMNS_TITLE, *("".join(paragraph) for column in THAI_COLUMNS for paragraph in column)]
                ),
            ),
        ),
    ),
)

# Upside-down pages, as when a sheet is fed into a scanner the wrong way round. The table fits
# a page upright, unlike the price schedule, which needs a sheet on its side.
UPSIDE_DOWN_DOCUMENTS = (
    SyntheticDocument(
        name="upside-down-scans",
        font_file=SARABUN,
        pages=(
            SyntheticPage(lines=scanned([PAYMENT_SCHEDULE], seed=9, upside_down=True), reference=PAYMENT_SCHEDULE_REFERENCE),
            SyntheticPage(lines=scanned(CLAUSES, seed=10, upside_down=True), reference="".join(CLAUSES)),
        ),
    ),
)

ALL_DOCUMENTS = (
    DOCUMENTS
    + SCANNED_DOCUMENTS
    + TEXT_LAYER_DOCUMENTS
    + PLACEHOLDER_DOCUMENTS
    + ROTATED_DOCUMENTS
    + SIDEWAYS_DOCUMENTS
    + UPSIDE_DOWN_DOCUMENTS
    + TWO_COLUMN_DOCUMENTS
    + RULED_TABLE_DOCUMENTS
    + PART_RULED_TABLE_DOCUMENTS
)


@dataclass(frozen=True)
class SyntheticWordDocument:
    """A DOCX source, its blocks as Word holds them, and the reference text of each page Word laid out."""

    name: str
    blocks: tuple[word.Block, ...]
    references: tuple[str, ...]


WORD_DOCUMENTS = (
    SyntheticWordDocument(
        name="word-structure",
        blocks=(
            word.Heading("สัญญาให้ทุนโครงการ", 1),
            word.Heading("ข้อกำหนดทั่วไป", 2),
            # Sara am stored as nikhahit + sara aa, as some Word files hold it.
            f"ผู้รับทุนตกลงท{chr(0x0E4D)}{chr(0x0E32)}งานตามแผนงานที่ได้รับอนุมัติ",
            word.Numbered(("เงื่อนไขของสัญญา", "ขอบเขตของการดำเนินงาน", "ข้อตกลงด้านการเงิน")),
            "รายงานที่ต้องส่ง",
            word.Bulleted(("รายงานความก้าวหน้า", "รายงานฉบับสมบูรณ์")),
            word.PageBreak("rendered"),
            word.Heading("งบประมาณ", 2),
            word.Table(
                (
                    (Cell("รายการ", rowspan=2), Cell("งบประมาณ", colspan=2)),
                    ("ปีที่ ๑", "ปีที่ ๒"),
                    ("ค่าตอบแทนผู้วิจัย", "100,000", "120,000"),
                )
            ),
            word.Image(),
            "โครงการ BCG Economy ระยะที่ 2 แบ่งงานเป็นสามส่วน",
            word.Numbered(("งานวิจัย", "งานพัฒนา", "งานถ่ายทอดเทคโนโลยี"), levels=(("thaiLetters", "(%1)"),)),
        ),
        references=(
            "# สัญญาให้ทุนโครงการ\n\n"
            "## ข้อกำหนดทั่วไป\n\n"
            "ผู้รับทุนตกลงทำงานตามแผนงานที่ได้รับอนุมัติ\n\n"
            "- 1. เงื่อนไขของสัญญา\n- 2. ขอบเขตของการดำเนินงาน\n- 3. ข้อตกลงด้านการเงิน\n\n"
            "รายงานที่ต้องส่ง\n\n"
            "- รายงานความก้าวหน้า\n- รายงานฉบับสมบูรณ์",
            "## งบประมาณ\n\n"
            "<table>\n"
            '<tr><td rowspan="2">รายการ</td><td colspan="2">งบประมาณ</td></tr>\n'
            "<tr><td>ปีที่ ๑</td><td>ปีที่ ๒</td></tr>\n"
            "<tr><td>ค่าตอบแทนผู้วิจัย</td><td>100,000</td><td>120,000</td></tr>\n"
            "</table>\n\n"
            "[รูปภาพ]\n\n"
            "โครงการ BCG Economy ระยะที่ 2 แบ่งงานเป็นสามส่วน\n\n"
            "- (ก) งานวิจัย\n- (ข) งานพัฒนา\n- (ค) งานถ่ายทอดเทคโนโลยี",
        ),
    ),
)


CONTRACT_LINES = [
    "ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้",
    "และส่งรายงานความก้าวหน้าต่อผู้ให้ทุนทุกหกเดือน",
    "โครงการ BCG Economy ระยะที่ 2 ปี 2567",
    "ค่าตอบแทนผู้วิจัย 100,000 บาท ค่าวัสดุ 30,000 บาท",
    "ข้อ ๓ ผู้รับทุนต้องไม่โอนสิทธิตามสัญญานี้ให้ผู้อื่น",
    "หากผู้รับทุนผิดสัญญา ผู้ให้ทุนมีสิทธิบอกเลิกสัญญาได้ทันที",
    "การแก้ไขเพิ่มเติมสัญญาต้องทำเป็นหนังสือลงนามโดยคู่สัญญา",
    "ระยะเวลาดำเนินงาน ๑๒ เดือน นับแต่วันที่ลงนามในสัญญา",
    "The grantee shall submit the final report within 30 days.",
    "เงื่อนไขการเบิกจ่ายเป็นไปตามระเบียบของสำนักงานฯ",
    "หลักฐานการจ่ายเงินต้องมีลายมือชื่อผู้รับเงินทุกฉบับ",
    "ในกรณีมีข้อพิพาท ให้ใช้กฎหมายไทยบังคับแก่สัญญานี้",
]
# Resolution, grain and skew, from the corpus's own level of damage to a fax-like scan.
DAMAGE = [(200, 6, 0.4), (150, 18, 0.8), (110, 28, 1.2), (90, 36, 1.5), (75, 45, 1.8)]

DEGRADED_DOCUMENTS = (
    SyntheticDocument(
        name="damaged-scans",
        font_file=SARABUN,
        pages=tuple(
            SyntheticPage(
                # A blank line between lines makes each a paragraph of its own.
                lines=Scan(
                    [line for text in CONTRACT_LINES for line in (text, "")],
                    dpi=dpi,
                    angle=angle,
                    noise=noise,
                    seed=10 + level,
                ),
                reference="\n\n".join(CONTRACT_LINES),
            )
            for level, (dpi, noise, angle) in enumerate(DAMAGE)
        ),
    ),
)


def generate(folder: Path) -> None:
    """Write every document as `<name>.pdf` or `<name>.docx` plus `<name>/page-NNN.reference.md`."""
    _write_documents(folder, ALL_DOCUMENTS)
    for word_document in WORD_DOCUMENTS:
        (folder / f"{word_document.name}.docx").write_bytes(word.document(*word_document.blocks))
        _write_references(folder / word_document.name, list(word_document.references))


def generate_degraded(folder: Path) -> None:
    """Write the damaged scans the same way."""
    _write_documents(folder, DEGRADED_DOCUMENTS)


def _write_documents(folder: Path, documents: Sequence[SyntheticDocument]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for document in documents:
        source = pdf(*(page.lines for page in document.pages), font_file=document.font_file)
        if document.remap:
            source = remapped(source, document.remap)
        (folder / f"{document.name}.pdf").write_bytes(source)
        _write_references(folder / document.name, [page.reference for page in document.pages])


def _write_references(folder: Path, references: list[str]) -> None:
    folder.mkdir(exist_ok=True)
    for number, reference in enumerate(references, start=1):
        (folder / reference_file_name(number)).write_text(reference + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    shutil.rmtree(SYNTHETIC, ignore_errors=True)
    generate(SYNTHETIC)
    print(f"wrote {len(ALL_DOCUMENTS) + len(WORD_DOCUMENTS)} documents to {SYNTHETIC}")
    shutil.rmtree(DEGRADED, ignore_errors=True)
    generate_degraded(DEGRADED)
    print(f"wrote {len(DEGRADED_DOCUMENTS)} documents to {DEGRADED}")
