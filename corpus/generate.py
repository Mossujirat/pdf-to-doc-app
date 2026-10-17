"""Generates the synthetic corpus: small PDFs whose reference text is known exactly.

Each page is described twice: the lines to draw, which may carry damage such as
sara am stored as two characters, and the reference text a reader sees.
Run `uv run python corpus/generate.py` after changing a document below, and commit the result.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path

from pdf_builder import NIRAMIT, SARABUN, Line, Spaced, pdf

from pdf_to_doc.quality import reference_file_name

SYNTHETIC = Path(__file__).parent / "synthetic"


@dataclass(frozen=True)
class SyntheticPage:
    lines: list[Line]
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
        name="multi-page",
        font_file=NIRAMIT,
        pages=(
            SyntheticPage(lines=["หน้าแรกของเอกสารทดสอบ"], reference="หน้าแรกของเอกสารทดสอบ"),
            SyntheticPage(lines=["หน้าที่สองของเอกสารทดสอบ"], reference="หน้าที่สองของเอกสารทดสอบ"),
        ),
    ),
)


def generate(folder: Path) -> None:
    """Write every document as `<name>.pdf` plus `<name>/page-NNN.reference.md`."""
    folder.mkdir(parents=True, exist_ok=True)
    for document in DOCUMENTS:
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
    print(f"wrote {len(DOCUMENTS)} documents to {SYNTHETIC}")
