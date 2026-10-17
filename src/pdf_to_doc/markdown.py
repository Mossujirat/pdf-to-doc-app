"""Renders the document model as Markdown for AI chats."""

from pdf_to_doc.model import Document
from pdf_to_doc.summary import Summary


def render_markdown(document: Document, summary: Summary) -> str:
    parts = [f"> **สรุปการแปลง** {summary.headline()}"]
    for page in document.pages:
        parts.append(f"<!-- page {page.number} -->")
        parts.extend(block.text for block in page.blocks)
    return "\n\n".join(parts) + "\n"
