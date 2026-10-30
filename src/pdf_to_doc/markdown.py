"""Renders the document model as Markdown for AI chats, and reads its page markers back."""

import html
import re
from collections.abc import Callable

from pdf_to_doc.model import (
    Block,
    Document,
    Heading,
    IncompleteTable,
    ListItem,
    Paragraph,
    Span,
    Table,
    TableCell,
    stretches,
    uncertain_text,
)
from pdf_to_doc.summary import Summary


def render_markdown(document: Document, summary: Summary) -> str:
    # The tag is written as code, so that viewers show it instead of highlighting, and it is not counted.
    parts = [f"> **สรุปการแปลง** {summary.headline(uncertain_marked_as='ครอบไว้ด้วย `<mark>`')}"]
    for page in document.pages:
        parts.append(_page_marker(page.number))
        previous: Block | None = None
        for block in page.blocks:
            if isinstance(block, ListItem) and isinstance(previous, ListItem):
                # Items of one list sit on consecutive lines.
                parts[-1] += "\n" + _render_block(block)
            else:
                parts.append(_render_block(block))
            previous = block
    return "\n\n".join(parts) + "\n"


def _render_block(block: Block) -> str:
    if isinstance(block, Heading):
        return f"{'#' * block.level} {block.text}"
    if isinstance(block, ListItem):
        return f"{'  ' * block.level}- {_marked(block.text, uncertain_text(block))}"
    if isinstance(block, Table):
        return _html_table(block) if block.has_merged_cells else _gfm_table(block)
    if isinstance(block, IncompleteTable):
        # The label as a paragraph of its own, then each printed row as one.
        return "\n\n".join([block.label, *(_render_block(row) for row in block.rows)])
    if isinstance(block, Paragraph):
        return _marked(block.text, uncertain_text(block))
    return block.text


def _marked(text: str, uncertain: tuple[Span, ...], escaped: Callable[[str], str] = lambda text: text) -> str:
    """The text, escaped as where it goes needs, with each stretch of uncertain text wrapped in a <mark> element."""
    return "".join(
        f"<mark>{escaped(piece)}</mark>" if marked else escaped(piece) for marked, piece in stretches(text, uncertain)
    )


def _gfm_table(table: Table) -> str:
    """A GitHub-flavoured Markdown table; the first row is the header. A line break kept
    inside a cell is a <br>, as a GFM row cannot hold one."""
    lines = []
    for index, row in enumerate(table.rows):
        lines.append("| " + " | ".join(_cell(cell, lambda text: text.replace("|", "\\|")) for cell in row) + " |")
        if index == 0:
            lines.append("| " + " | ".join("---" for _ in row) + " |")
    return "\n".join(lines)


def _html_table(table: Table) -> str:
    """An HTML table, for merged cells that Markdown tables cannot express."""
    lines = ["<table>"]
    for row in table.rows:
        cells = []
        for cell in row:
            spans = ""
            if cell.rowspan > 1:
                spans += f' rowspan="{cell.rowspan}"'
            if cell.colspan > 1:
                spans += f' colspan="{cell.colspan}"'
            text = _cell(cell, lambda text: html.escape(text, quote=False))
            cells.append(f"<td{spans}>{text}</td>")
        lines.append("<tr>" + "".join(cells) + "</tr>")
    lines.append("</table>")
    return "\n".join(lines)


def _cell(cell: TableCell, escaped: Callable[[str], str]) -> str:
    """A cell's text, escaped as its table needs, with its uncertain text in <mark> elements and
    a <br> where it keeps a line break."""
    return _marked(cell.text, uncertain_text(cell), escaped).replace("\n", "<br>")


_PAGE_MARKER = re.compile(r"^<!-- page (\d+) -->$", re.MULTILINE)


def _page_marker(number: int) -> str:
    return f"<!-- page {number} -->"


def split_pages(markdown: str) -> dict[int, str]:
    """The Markdown of each page, keyed by page number, without the summary."""
    parts = _PAGE_MARKER.split(markdown)
    # parts = [summary, "1", page-1 text, "2", page-2 text, ...]
    return {int(number): text.strip() for number, text in zip(parts[1::2], parts[2::2])}
