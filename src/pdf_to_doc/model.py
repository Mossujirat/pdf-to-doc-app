"""The document model: one structured representation that every output is rendered from (ADR 0003)."""

from dataclasses import dataclass
from typing import Literal, assert_never

# How a page was read: from its text layer, with OCR, or not at all, as a scan kept as an image.
PageKind = Literal["text", "ocr", "kept"]
# Markdown and Word both have six heading levels.
DEEPEST_HEADING = 6
# Where a stretch of a block's text starts and ends, as positions in its text.
Span = tuple[int, int]


@dataclass(frozen=True)
class Paragraph:
    text: str
    uncertain: tuple[Span, ...] = ()  # uncertain text, in order


@dataclass(frozen=True)
class Heading:
    level: int  # 1 is the most prominent, DEEPEST_HEADING the least
    text: str


@dataclass(frozen=True)
class ListItem:
    text: str  # keeps its own number or letter, such as "1." or "(ก)"; bullets are dropped
    bulleted: bool  # the item had a bullet rather than its own number or letter
    level: int = 0  # how deep in a list within a list, 0 the outermost; text pages tell no depth
    uncertain: tuple[Span, ...] = ()  # uncertain text, in order


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


PlaceholderKind = Literal["image", "signature", "stamp", "handwriting", "incomplete_table", "scan"]


@dataclass(frozen=True)
class KeptImage:
    """An image an output shows as it is, when images are kept: compressed, never raw pixels."""

    data: bytes  # a JPEG, or a PNG where the image lets what lies under it show through
    width: float  # the size it is shown at, in points
    height: float


@dataclass(frozen=True)
class Placeholder:
    """Content the converter deliberately does not transcribe, shown as a short Thai label.
    With images kept, it carries the image that DOCX shows in its place: a scan's whole page,
    or a picture."""

    kind: PlaceholderKind
    image: KeptImage | None = None

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
            case "scan":
                return "หน้าสแกน"
            case _:
                assert_never(self.kind)

    @property
    def text(self) -> str:
        return f"[{self.name}]"


Block = Paragraph | Heading | ListItem | Table | Placeholder


def uncertain_text(block: Block) -> tuple[Span, ...]:
    """The block's uncertain text. Only paragraphs and list items hold any: OCR pages give
    no headings, and no tables until scanned tables are read."""
    return block.uncertain if isinstance(block, (Paragraph, ListItem)) else ()


def stretches(text: str, uncertain: tuple[Span, ...]) -> list[tuple[bool, str]]:
    """The text cut into its uncertain stretches and the rest, in order, each flagged True if uncertain."""
    pieces: list[tuple[bool, str]] = []
    position = 0
    for start, end in uncertain:
        if start > position:
            pieces.append((False, text[position:start]))
        pieces.append((True, text[start:end]))
        position = end
    if position < len(text):
        pieces.append((False, text[position:]))
    return pieces


@dataclass(frozen=True)
class Page:
    number: int
    kind: PageKind
    blocks: tuple[Block, ...]
    engine: str | None = None  # the OCR engine that read an OCR page
    # Its text layer was there but could not be trusted, so none of it was used: the page was
    # read with OCR instead, or, kept as an image, gave no text.
    untrusted_text_layer: bool = False

    @property
    def kept_image(self) -> KeptImage | None:
        """A kept page's image of itself, which its scan placeholder carries; None on any other page."""
        scans = (block for block in self.blocks if isinstance(block, Placeholder) and block.kind == "scan")
        return next((block.image for block in scans), None)


@dataclass(frozen=True)
class Document:
    pages: tuple[Page, ...]
