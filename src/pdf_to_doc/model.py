"""The document model: one structured representation that every output is rendered from (ADR 0003)."""

from dataclasses import dataclass
from typing import Literal

PageKind = Literal["text", "ocr"]


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class Heading:
    level: int  # 1 is the most prominent
    text: str


@dataclass(frozen=True)
class ListItem:
    text: str  # keeps its own number or letter, such as "1." or "(ก)"; bullets are dropped


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


Block = Paragraph | Heading | ListItem | Table


@dataclass(frozen=True)
class Page:
    number: int
    kind: PageKind
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Document:
    pages: tuple[Page, ...]
