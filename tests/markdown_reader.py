"""Reads a Markdown output back the way a person would: page by page."""

import re

PAGE_MARKER = re.compile(r"^<!-- page (\d+) -->$", re.MULTILINE)


def page_texts(markdown: str) -> list[str]:
    """The text of each page, without the summary above the first page marker."""
    parts = PAGE_MARKER.split(markdown)
    # parts = [summary, "1", page-1 text, "2", page-2 text, ...]
    return [text.strip() for text in parts[2::2]]
