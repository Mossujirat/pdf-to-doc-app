"""The conversion function: the single entry point the CLI and the web service wrap."""

from dataclasses import dataclass
from typing import Literal

from pdf_to_doc.intake import UnsupportedFormat, admit, open_pdf
from pdf_to_doc.markdown import render_markdown
from pdf_to_doc.pdf_text import read_pdf
from pdf_to_doc.summary import Summary, summarize

OutputFormat = Literal["markdown"]


@dataclass(frozen=True)
class ConversionResult:
    output: bytes
    summary: Summary


def convert(source: bytes, *, to: OutputFormat = "markdown", password: str | None = None) -> ConversionResult:
    """Convert a source file's bytes into the requested output format.

    `password` opens a PDF that needs one. A source file that cannot or will not
    be converted raises an `IntakeError`, whose type says why.
    """
    if to != "markdown":
        raise ValueError(f"Unsupported output format: {to}")
    if admit(source) == "docx":
        raise UnsupportedFormat("docx")  # DOCX sources are accepted, but reading them is not built yet.
    with open_pdf(source, password) as pdf:
        document = read_pdf(pdf)
    summary = summarize(document)
    output = render_markdown(document, summary).encode("utf-8")
    return ConversionResult(output=output, summary=summary)
