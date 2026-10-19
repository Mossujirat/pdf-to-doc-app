"""Generates the synthetic corpus: small PDFs whose reference text is known exactly.

Each page is described twice: the lines to draw, which may carry damage such as
sara am stored as two characters, and the reference text a reader sees. A scanned
page draws its lines as an image at 200 dpi, slightly askew and with mild grain.
Run `uv run python corpus/generate.py` after changing a document below, and commit the result.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path

from pdf_builder import NIRAMIT, SARABUN, Cell, Grid, Line, Scan, Spaced, Styled, pdf

from pdf_to_doc.quality import reference_file_name

SYNTHETIC = Path(__file__).parent / "synthetic"


@dataclass(frozen=True)
class SyntheticPage:
    lines: list[Line] | Scan
    reference: str


@dataclass(frozen=True)
class SyntheticDocument:
    name: str
    font_file: Path
    pages: tuple[SyntheticPage, ...]


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


def generate(folder: Path) -> None:
    """Write every document as `<name>.pdf` plus `<name>/page-NNN.reference.md`."""
    folder.mkdir(parents=True, exist_ok=True)
    for document in DOCUMENTS + SCANNED_DOCUMENTS:
        source = pdf(*(page.lines for page in document.pages), font_file=document.font_file)
        (folder / f"{document.name}.pdf").write_bytes(source)
        references = folder / document.name
        references.mkdir(exist_ok=True)
        for number, page in enumerate(document.pages, start=1):
            (references / reference_file_name(number)).write_text(
                page.reference + "\n", encoding="utf-8", newline="\n"
            )


if __name__ == "__main__":
    shutil.rmtree(SYNTHETIC, ignore_errors=True)
    generate(SYNTHETIC)
    print(f"wrote {len(DOCUMENTS + SCANNED_DOCUMENTS)} documents to {SYNTHETIC}")
