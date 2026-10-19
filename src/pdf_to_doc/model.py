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


Block = Paragraph | Heading | ListItem


@dataclass(frozen=True)
class Page:
    number: int
    kind: PageKind
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Document:
    pages: tuple[Page, ...]
