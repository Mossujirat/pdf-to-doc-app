"""The document model: one structured representation that every output is rendered from (ADR 0003)."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import ClassVar, Literal, assert_never

# How a page was read: from its text layer, with OCR, or not at all, as a scan kept as an image.
PageKind = Literal["text", "ocr", "kept"]
# Markdown and Word both have six heading levels.
DEEPEST_HEADING = 6
# Word takes no page larger than this either way, in points (22 inches), so it shows no image larger.
LARGEST_PAGE = 22 * 72
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
    text: str  # a line break where the cell keeps one
    rowspan: int = 1
    colspan: int = 1
    uncertain: tuple[Span, ...] = ()  # uncertain text, in order


@dataclass(frozen=True)
class Table:
    # Each row holds the cells that start in it; a merged cell covers the
    # positions its spans reach in the rows and columns after it.
    rows: tuple[tuple[TableCell, ...], ...]

    @property
    def has_merged_cells(self) -> bool:
        return any(cell.rowspan > 1 or cell.colspan > 1 for row in self.rows for cell in row)


@dataclass(frozen=True)
class IncompleteTable:
    """A table on an OCR page whose text could not be placed in its cells with certainty: its
    printed rows, each a line of its own, after a label saying the table may be incomplete. Its
    text is transcribed, so it is no placeholder."""

    rows: tuple[Paragraph, ...]
    name: ClassVar[str] = "ตารางอาจไม่สมบูรณ์"

    @property
    def label(self) -> str:
        return f"[{self.name}]"


PlaceholderKind = Literal["image", "signature", "stamp", "handwriting", "scan"]


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
            case "scan":
                return "หน้าสแกน"
            case _:
                assert_never(self.kind)

    @property
    def text(self) -> str:
        return f"[{self.name}]"


Block = Paragraph | Heading | ListItem | Table | IncompleteTable | Placeholder


def uncertain_text(part: Block | TableCell) -> tuple[Span, ...]:
    """The uncertain text of a block, or of a table's cell. Only paragraphs, list items and cells
    hold any: OCR pages give no headings, a table's text is in its cells, and an incomplete
    table's in its rows, which are paragraphs."""
    return part.uncertain if isinstance(part, (Paragraph, ListItem, TableCell)) else ()


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
    # The resolution kept images were lowered to, in dots per inch, so that the outputs stay within their limit.
    images_lowered_to: int | None = None

    def kept_images(self) -> set[KeptImage]:
        """Every image a placeholder carries, each once."""
        blocks = (block for page in self.pages for block in page.blocks)
        return {block.image for block in blocks if isinstance(block, Placeholder) and block.image}

    def with_kept_images(self, images: Mapping[KeptImage, KeptImage], lowered_to: int) -> "Document":
        """The document with each kept image replaced by the one `images` gives for it, lowered to `lowered_to`."""

        def changed(block: Block) -> Block:
            if isinstance(block, Placeholder) and block.image:
                return replace(block, image=images[block.image])
            return block

        pages = tuple(replace(page, blocks=tuple(changed(block) for block in page.blocks)) for page in self.pages)
        return replace(self, pages=pages, images_lowered_to=lowered_to)
