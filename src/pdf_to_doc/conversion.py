"""The conversion function: the single entry point the CLI and the web service wrap."""

from dataclasses import dataclass
from typing import Literal

from pdf_to_doc.intake import UnsupportedFormat, admit, open_pdf
from pdf_to_doc.markdown import render_markdown
from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.paddle import default_engine
from pdf_to_doc.reading import ProgressCallback, read_pdf
from pdf_to_doc.summary import Summary, summarize

OutputFormat = Literal["markdown"]


@dataclass(frozen=True)
class ConversionResult:
    output: bytes
    summary: Summary


def convert(
    source: bytes,
    *,
    to: OutputFormat = "markdown",
    password: str | None = None,
    ocr: OcrEngine | None = None,
    progress: ProgressCallback | None = None,
) -> ConversionResult:
    """Convert a source file's bytes into the requested output format.

    `password` opens a PDF that needs one. `ocr` reads OCR pages; PaddleOCR does
    by default, and raises `ModelsMissing` if its models are not installed.
    `progress` hears how far the conversion has got. A source file that cannot
    or will not be converted raises an `IntakeError`, whose type says why.
    """
    if to != "markdown":
        raise ValueError(f"Unsupported output format: {to}")
    if admit(source) == "docx":
        raise UnsupportedFormat("docx")  # DOCX sources are accepted, but reading them is not built yet.
    with open_pdf(source, password) as pdf:
        document = read_pdf(pdf, (lambda: ocr) if ocr else default_engine, progress)
    summary = summarize(document)
    output = render_markdown(document, summary).encode("utf-8")
    return ConversionResult(output=output, summary=summary)

