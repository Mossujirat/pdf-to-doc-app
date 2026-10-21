"""Generates the synthetic corpus: small PDFs whose reference text is known exactly.

Each page is described twice: the lines to draw, which may carry damage such as
sara am stored as two characters, and the reference text a reader sees. A scanned
page draws its lines as an image at 200 dpi, slightly askew and with mild grain.
Run `uv run python corpus/generate.py` after changing a document below, and commit the result.
"""

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import word_builder as word
from pdf_builder import NIRAMIT, SARABUN, Cell, Grid, Line, Picture, Scan, Spaced, Styled, pdf, remapped

from pdf_to_doc.quality import reference_file_name

SYNTHETIC = Path(__file__).parent / "synthetic"
# Scans damaged on purpose, for measuring how much of what OCR misreads is marked as
# uncertain text. They are kept apart because OCR is expected to get them wrong.
DEGRADED = Path(__file__).parent / "degraded"


@dataclass(frozen=True)
class SyntheticPage:
    lines: Sequence[Line] | Scan
    reference: str


@dataclass(frozen=True)
class SyntheticDocument:
    name: str
    font_file: Path
    pages: tuple[SyntheticPage, ...]
    # Characters the fonts' text layer reports as something else, as broken or legacy fonts do.
    remap: dict[str, str] | None = None


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
        name="tables",
        font_file=SARABUN,
        pages=(
            SyntheticPage(
                lines=[
                    "ผู้ให้ทุนจะจ่ายเงินเป็นงวดตามตารางนี้",
                    Grid(
                        rows=(
                            ("งวดที่", "กำหนดส่งงาน", "จำนวนเงิน"),
                            ("๑", "ส่งรายงานความก้าว\nหน้าฉบับที่หนึ่ง", "50,000"),
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
        name="multi-page",
        font_file=NIRAMIT,
        pages=(
            SyntheticPage(lines=["หน้าแรกของเอกสารทดสอบ"], reference="หน้าแรกของเอกสารทดสอบ"),
            SyntheticPage(lines=["หน้าที่สองของเอกสารทดสอบ"], reference="หน้าที่สองของเอกสารทดสอบ"),
        ),
    ),
)

STAMP = Styled("เอกสารปกปิด ห้ามเผยแพร่ก่อนได้รับอนุญาต", size=14, y=40)


def scanned(lines: list[Line], overlay: list[Line] | None = None, seed: int = 0) -> Scan:
    return Scan(lines, overlay=overlay or [], dpi=200, angle=0.4, noise=6, seed=seed)


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
    # A font whose ToUnicode map reports sara aa as sara am: "การ" reads "กำร".
    # The page looks right, so it is read with OCR.
    SyntheticDocument(
        name="wrong-unicode-map",
        font_file=SARABUN,
        pages=(SyntheticPage(lines=CLAUSES, reference="".join(CLAUSES)),),
        remap={chr(0x0E32): chr(0x0E33)},
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

ALL_DOCUMENTS = DOCUMENTS + SCANNED_DOCUMENTS + TEXT_LAYER_DOCUMENTS + PLACEHOLDER_DOCUMENTS


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
