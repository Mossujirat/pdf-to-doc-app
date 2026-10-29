"""What a conversion did, page by page. Every output opens with it."""

from dataclasses import dataclass
from typing import get_args

from pdf_to_doc.intake import MAX_OUTPUTS
from pdf_to_doc.model import (
    Block,
    Document,
    IncompleteTable,
    PageKind,
    Placeholder,
    PlaceholderKind,
    Table,
    TableCell,
    uncertain_text,
)

_MB = 1024 * 1024


@dataclass(frozen=True)
class PageSummary:
    number: int
    kind: PageKind
    engine: str | None = None
    untrusted_text_layer: bool = False
    placeholders: tuple[PlaceholderKind, ...] = ()  # the kind of each placeholder, in reading order
    uncertain: int = 0  # stretches of uncertain text
    tables: int = 0  # tables that came out as tables, on an OCR page; text pages' are not counted
    incomplete_tables: int = 0


@dataclass(frozen=True)
class Summary:
    pages: tuple[PageSummary, ...]
    # The resolution kept images were lowered to, in dots per inch, so that the outputs stay within their limit.
    images_lowered_to: int | None = None

    def count(self, kind: PageKind) -> int:
        return sum(1 for page in self.pages if page.kind == kind)

    def placeholder_count(self, kind: PlaceholderKind) -> int:
        return sum(page.placeholders.count(kind) for page in self.pages)

    @property
    def uncertain(self) -> int:
        return sum(page.uncertain for page in self.pages)

    def headline(self, uncertain_marked_as: str | None = None) -> str:
        """One Thai sentence for people: how many pages, how each was read, which were read with
        OCR, which were kept as images if any were, which of those had a text layer that could not be
        trusted, how many placeholders of each kind stand in for what was not transcribed, how many
        tables on OCR pages came out as tables and how many may be incomplete, and where, how much
        text is uncertain and where, and, if they were, what kept images were lowered to.
        `uncertain_marked_as` says how an output marks uncertain text."""
        sentence = (
            f"{len(self.pages)} หน้า: "
            f"อ่านจากข้อความในไฟล์ {self.count('text')} หน้า, "
            f"อ่านด้วย OCR {self.count('ocr')} หน้า"
        )
        ocr_pages = [page for page in self.pages if page.kind == "ocr"]
        if ocr_pages:
            engines = ", ".join(sorted({page.engine for page in ocr_pages if page.engine}))
            sentence += f" ได้แก่หน้า {_page_ranges([page.number for page in ocr_pages])} ด้วย {engines}"
        if untrusted := self._untrusted("ocr"):
            sentence += f" (หน้า {untrusted} ข้อความในไฟล์ไม่น่าเชื่อถือ จึงอ่านด้วย OCR)"
        if kept := [page.number for page in self.pages if page.kind == "kept"]:
            sentence += f", เก็บเป็นภาพ {len(kept)} หน้า ได้แก่หน้า {_page_ranges(kept)}"
            if untrusted := self._untrusted("kept"):
                sentence += f" (หน้า {untrusted} ข้อความในไฟล์ไม่น่าเชื่อถือ จึงไม่ได้นำมาใช้)"
        counts = [(Placeholder(kind).name, self.placeholder_count(kind)) for kind in get_args(PlaceholderKind)]
        if any(count for _, count in counts):
            sentence += " ส่วนที่ไม่ได้ถอดเป็นข้อความ: " + ", ".join(f"{name} {count} จุด" for name, count in counts if count)
        tables = []
        if made := sum(page.tables for page in self.pages):
            tables.append(f"เป็นตาราง {made} ตาราง")
        if incomplete := sum(page.incomplete_tables for page in self.pages):
            pages = _page_ranges([page.number for page in self.pages if page.incomplete_tables])
            tables.append(f"อาจไม่สมบูรณ์ {incomplete} ตาราง ในหน้า {pages} ควรตรวจโครงสร้างกับต้นฉบับ")
        if tables:
            sentence += " ตารางในหน้าที่อ่านด้วย OCR: " + ", ".join(tables)
        if self.uncertain:
            pages = _page_ranges([page.number for page in self.pages if page.uncertain])
            sentence += f" ข้อความที่ไม่แน่ใจ {self.uncertain} จุด ในหน้า {pages} ควรตรวจกับต้นฉบับ"
            if uncertain_marked_as:
                sentence += f" ({uncertain_marked_as})"
        if self.images_lowered_to:
            limit = MAX_OUTPUTS // _MB
            sentence += f" ภาพใน DOCX ลดความละเอียดเหลือ {self.images_lowered_to} dpi ให้ผลลัพธ์ไม่เกิน {limit} MB"
        return sentence

    def _untrusted(self, kind: PageKind) -> str:
        """The pages of the kind whose text layer could not be trusted, written short; "" if none."""
        return _page_ranges([page.number for page in self.pages if page.kind == kind and page.untrusted_text_layer])


def _page_ranges(numbers: list[int]) -> str:
    """Page numbers written short: "2–3, 5"."""
    ranges: list[list[int]] = []
    for number in numbers:
        if ranges and number == ranges[-1][-1] + 1:
            ranges[-1].append(number)
        else:
            ranges.append([number])
    return ", ".join(str(run[0]) if len(run) == 1 else f"{run[0]}–{run[-1]}" for run in ranges)


def summarize(document: Document) -> Summary:
    return Summary(
        pages=tuple(
            PageSummary(
                page.number,
                page.kind,
                page.engine,
                page.untrusted_text_layer,
                # A kept page's placeholder is counted as the page kind it stands for.
                tuple(block.kind for block in page.blocks if isinstance(block, Placeholder) and block.kind != "scan"),
                sum(len(uncertain_text(part)) for block in page.blocks for part in _parts(block)),
                sum(isinstance(block, Table) for block in page.blocks) if page.kind == "ocr" else 0,
                sum(isinstance(block, IncompleteTable) for block in page.blocks),
            )
            for page in document.pages
        ),
        images_lowered_to=document.images_lowered_to,
    )


def _parts(block: Block) -> list[Block | TableCell]:
    """What of the block can hold uncertain text: a table's cells, an incomplete table's rows, or the block itself."""
    if isinstance(block, Table):
        return [cell for row in block.rows for cell in row]
    return list(block.rows) if isinstance(block, IncompleteTable) else [block]
