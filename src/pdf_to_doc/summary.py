"""What a conversion did, page by page. Every output opens with it."""

from dataclasses import dataclass
from typing import get_args

from pdf_to_doc.model import Document, PageKind, Placeholder, PlaceholderKind, uncertain_text


@dataclass(frozen=True)
class PageSummary:
    number: int
    kind: PageKind
    engine: str | None = None
    untrusted_text_layer: bool = False
    placeholders: tuple[PlaceholderKind, ...] = ()  # the kind of each placeholder, in reading order
    uncertain: int = 0  # stretches of uncertain text


@dataclass(frozen=True)
class Summary:
    pages: tuple[PageSummary, ...]

    def count(self, kind: PageKind) -> int:
        return sum(1 for page in self.pages if page.kind == kind)

    def placeholder_count(self, kind: PlaceholderKind) -> int:
        return sum(page.placeholders.count(kind) for page in self.pages)

    @property
    def uncertain(self) -> int:
        return sum(page.uncertain for page in self.pages)

    def headline(self, uncertain_marked_as: str | None = None) -> str:
        """One Thai sentence for people: how many pages, how each was read, which were read with
        OCR, which were kept as images if any were, how many placeholders of each kind stand in for
        what was not transcribed, and how much text is uncertain and where. `uncertain_marked_as`
        says how an output marks it."""
        sentence = (
            f"{len(self.pages)} หน้า: "
            f"อ่านจากข้อความในไฟล์ {self.count('text')} หน้า, "
            f"อ่านด้วย OCR {self.count('ocr')} หน้า"
        )
        ocr_pages = [page for page in self.pages if page.kind == "ocr"]
        if ocr_pages:
            engines = ", ".join(sorted({page.engine for page in ocr_pages if page.engine}))
            sentence += f" ได้แก่หน้า {_page_ranges([page.number for page in ocr_pages])} ด้วย {engines}"
        untrusted = [page.number for page in self.pages if page.untrusted_text_layer]
        if untrusted:
            sentence += f" (หน้า {_page_ranges(untrusted)} ข้อความในไฟล์ไม่น่าเชื่อถือ จึงอ่านด้วย OCR)"
        if kept := [page.number for page in self.pages if page.kind == "kept"]:
            sentence += f", เก็บเป็นภาพ {len(kept)} หน้า ได้แก่หน้า {_page_ranges(kept)}"
        counts = [(Placeholder(kind).name, self.placeholder_count(kind)) for kind in get_args(PlaceholderKind)]
        if any(count for _, count in counts):
            sentence += " ส่วนที่ไม่ได้ถอดเป็นข้อความ: " + ", ".join(f"{name} {count} จุด" for name, count in counts if count)
        if self.uncertain:
            pages = _page_ranges([page.number for page in self.pages if page.uncertain])
            sentence += f" ข้อความที่ไม่แน่ใจ {self.uncertain} จุด ในหน้า {pages} ควรตรวจกับต้นฉบับ"
            if uncertain_marked_as:
                sentence += f" ({uncertain_marked_as})"
        return sentence


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
                sum(len(uncertain_text(block)) for block in page.blocks),
            )
            for page in document.pages
        )
    )
