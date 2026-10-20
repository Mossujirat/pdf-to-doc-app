"""Renders the document model as Markdown for AI chats, and reads its page markers back."""

import html
import re

from pdf_to_doc.model import Block, Document, Heading, ListItem, Table
from pdf_to_doc.summary import Summary


def render_markdown(document: Document, summary: Summary) -> str:
    parts = [f"> **สรุปการแปลง** {summary.headline()}"]
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
        return f"{'  ' * block.level}- {block.text}"
    if isinstance(block, Table):
        return _html_table(block) if block.has_merged_cells else _gfm_table(block)
    return block.text


def _gfm_table(table: Table) -> str:
    """A GitHub-flavoured Markdown table; the first row is the header."""
    lines = []
    for index, row in enumerate(table.rows):
        lines.append("| " + " | ".join(cell.text.replace("|", "\\|") for cell in row) + " |")
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
            cells.append(f"<td{spans}>{html.escape(cell.text, quote=False)}</td>")
        lines.append("<tr>" + "".join(cells) + "</tr>")
    lines.append("</table>")
    return "\n".join(lines)


_PAGE_MARKER = re.compile(r"^<!-- page (\d+) -->$", re.MULTILINE)


def _page_marker(number: int) -> str:
    return f"<!-- page {number} -->"


def split_pages(markdown: str) -> dict[int, str]:
    """The Markdown of each page, keyed by page number, without the summary."""
    parts = _PAGE_MARKER.split(markdown)
    # parts = [summary, "1", page-1 text, "2", page-2 text, ...]
    return {int(number): text.strip() for number, text in zip(parts[1::2], parts[2::2])}
