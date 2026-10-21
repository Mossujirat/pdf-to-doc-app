"""The conversion function: the single entry point the CLI and the web service wrap."""

from collections.abc import Mapping, Set
from dataclasses import dataclass
from typing import Literal, get_args

from pdf_to_doc.docx_output import render_docx
from pdf_to_doc.docx_reading import read_docx
from pdf_to_doc.intake import IntakeError, admit, open_pdf
from pdf_to_doc.markdown import render_markdown
from pdf_to_doc.model import Document
from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.paddle import default_engine
from pdf_to_doc.progress import Opened, Progress, ProgressCallback
from pdf_to_doc.reading import read_pdf
from pdf_to_doc.summary import Summary, summarize

OutputFormat = Literal["markdown", "docx"]


class DocxToDocx(IntakeError):
    """The source is a DOCX and DOCX output alone was asked for, which is not offered."""


@dataclass(frozen=True)
class ConversionResult:
    outputs: Mapping[OutputFormat, bytes]  # an output for each format given, in the order OutputFormat lists them
    summary: Summary

    @property
    def output(self) -> bytes:
        """The output, when there is only one."""
        [output] = self.outputs.values()
        return output


def convert(
    source: bytes,
    *,
    to: OutputFormat | Set[OutputFormat] = "markdown",
    password: str | None = None,
    ocr: OcrEngine | None = None,
    progress: ProgressCallback | None = None,
) -> ConversionResult:
    """Convert a source file's bytes into the output format `to`, or into each format in a set of them.
    Every output is rendered from one reading of the source file, and shares one summary. A DOCX
    source never gives DOCX: asked for both formats, it gets Markdown only.

    `password` opens a PDF that needs one. `ocr` reads OCR pages; PaddleOCR does
    by default, and raises `ModelsMissing` if its models are not installed.
    `progress` hears how far the conversion has got: first `Opened`, once the page
    count is known, then each stage in order. A source file that cannot or will not
    be converted raises an `IntakeError`, whose type says why, before any report.
    """
    formats = {to} if isinstance(to, str) else set(to)
    if not formats:
        raise ValueError("No output format asked for")
    if not formats <= set(get_args(OutputFormat)):
        raise ValueError(f"Unsupported output format: {to}")
    report: ProgressCallback = progress or (lambda update: None)
    if admit(source) == "docx":
        if formats == {"docx"}:
            raise DocxToDocx()
        formats.discard("docx")  # asked for both, a DOCX source gets Markdown only
        # Its pages are counted by reading it, so it is read by the time it is opened.
        document = read_docx(source)
        report(Opened(source_type="docx", pages=len(document.pages)))
    else:
        with open_pdf(source, password) as pdf:
            report(Opened(source_type="pdf", pages=pdf.page_count))
            report(Progress(stage="reading"))
            document = read_pdf(pdf, (lambda: ocr) if ocr else default_engine, report)
    report(Progress(stage="writing"))
    summary = summarize(document)
    outputs = {name: _render(document, summary, name) for name in get_args(OutputFormat) if name in formats}
    return ConversionResult(outputs=outputs, summary=summary)


def _render(document: Document, summary: Summary, to: OutputFormat) -> bytes:
    return render_docx(document, summary) if to == "docx" else render_markdown(document, summary).encode("utf-8")

