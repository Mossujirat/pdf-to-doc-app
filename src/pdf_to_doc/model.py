"""The document model: one structured representation that every output is rendered from (ADR 0003)."""

from dataclasses import dataclass
from typing import Literal, assert_never

PageKind = Literal["text", "ocr"]
# Markdown and Word both have six heading levels.
DEEPEST_HEADING = 6


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class Heading:
    level: int  # 1 is the most prominent, DEEPEST_HEADING the least
    text: str


@dataclass(frozen=True)
class ListItem:
    text: str  # keeps its own number or letter, such as "1." or "(ก)"; bullets are dropped
    bulleted: bool  # the item had a bullet rather than its own number or letter


@dataclass(frozen=True)
class TableCell:
    text: str
    rowspan: int = 1
    colspan: int = 1


@dataclass(frozen=True)
class Table:
    # Each row holds the cells that start in it; a merged cell covers the
    # positions its spans reach in the rows and columns after it.
    rows: tuple[tuple[TableCell, ...], ...]

    @property
    def has_merged_cells(self) -> bool:
        return any(cell.rowspan > 1 or cell.colspan > 1 for row in self.rows for cell in row)


PlaceholderKind = Literal["image", "signature", "stamp", "handwriting", "incomplete_table"]


@dataclass(frozen=True)
class Placeholder:
    """Content the converter deliberately does not transcribe, shown as a short Thai label."""

    kind: PlaceholderKind

    @property
    def name(self) -> str:
        match self.kind:
            case "image":
                return "รูปภาพ"
            case "signature":
                return "ลายเซ็น"
            case "stamp":
                return "ตราประทับ"
            case "handwriting":
                return "ลายมือ"
            case "incomplete_table":
                return "ตารางอาจไม่สมบูรณ์"
            case _:
                assert_never(self.kind)

    @property
    def text(self) -> str:
        return f"[{self.name}]"


Block = Paragraph | Heading | ListItem | Table | Placeholder


@dataclass(frozen=True)
class Page:
    number: int
    kind: PageKind
    blocks: tuple[Block, ...]
    engine: str | None = None  # the OCR engine that read an OCR page
    # Read with OCR because its text layer was there but could not be trusted.
    untrusted_text_layer: bool = False


@dataclass(frozen=True)
class Document:
    pages: tuple[Page, ...]
