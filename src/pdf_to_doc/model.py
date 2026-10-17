"""The document model: one structured representation that every output is rendered from (ADR 0003)."""

from dataclasses import dataclass
from typing import Literal

PageKind = Literal["text", "ocr"]


@dataclass(frozen=True)
class Paragraph:
    text: str


Block = Paragraph


@dataclass(frozen=True)
class Page:
    number: int
    kind: PageKind
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Document:
    pages: tuple[Page, ...]
