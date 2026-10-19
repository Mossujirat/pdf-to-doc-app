"""What a conversion did, page by page. Every output opens with it."""

from dataclasses import dataclass

from pdf_to_doc.model import Document, PageKind


@dataclass(frozen=True)
class PageSummary:
    number: int
    kind: PageKind
    engine: str | None = None


@dataclass(frozen=True)
class Summary:
    pages: tuple[PageSummary, ...]

    def count(self, kind: PageKind) -> int:
        return sum(1 for page in self.pages if page.kind == kind)

    def headline(self) -> str:
        """One Thai sentence for people: how many pages, how each was read, and which were read with OCR."""
        sentence = (
            f"{len(self.pages)} หน้า: "
            f"อ่านจากข้อความในไฟล์ {self.count('text')} หน้า, "
            f"อ่านด้วย OCR {self.count('ocr')} หน้า"
        )
        ocr_pages = [page for page in self.pages if page.kind == "ocr"]
        if ocr_pages:
            engines = ", ".join(sorted({page.engine for page in ocr_pages if page.engine}))
            sentence += f" ได้แก่หน้า {_page_ranges([page.number for page in ocr_pages])} ด้วย {engines}"
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
    return Summary(pages=tuple(PageSummary(page.number, page.kind, page.engine) for page in document.pages))
