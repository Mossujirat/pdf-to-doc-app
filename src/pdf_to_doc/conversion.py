"""The conversion function: the single entry point the CLI and the web service wrap."""

from dataclasses import dataclass
from typing import Literal

from pdf_to_doc.markdown import render_markdown
from pdf_to_doc.pdf_text import read_pdf
from pdf_to_doc.summary import Summary, summarize

OutputFormat = Literal["markdown"]


@dataclass(frozen=True)
class ConversionResult:
    output: bytes
    summary: Summary


def convert(source: bytes, *, to: OutputFormat = "markdown") -> ConversionResult:
    """Convert a source file's bytes into the requested output format."""
    if to != "markdown":
        raise ValueError(f"Unsupported output format: {to}")
    document = read_pdf(source)
    summary = summarize(document)
    output = render_markdown(document, summary).encode("utf-8")
    return ConversionResult(output=output, summary=summary)
