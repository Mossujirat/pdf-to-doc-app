"""What a conversion did, page by page. Every output opens with it."""

from dataclasses import dataclass

from pdf_to_doc.model import Document, PageKind


@dataclass(frozen=True)
class PageSummary:
    number: int
    kind: PageKind


@dataclass(frozen=True)
class Summary:
    pages: tuple[PageSummary, ...]

    def count(self, kind: PageKind) -> int:
        return sum(1 for page in self.pages if page.kind == kind)

    def headline(self) -> str:
        """One Thai sentence for people: how many pages, and how each was read."""
        return (
            f"{len(self.pages)} หน้า: "
            f"อ่านจากข้อความในไฟล์ {self.count('text')} หน้า, "
            f"อ่านด้วย OCR {self.count('ocr')} หน้า"
        )


def summarize(document: Document) -> Summary:
    return Summary(pages=tuple(PageSummary(page.number, page.kind) for page in document.pages))
