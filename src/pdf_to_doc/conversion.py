"""The conversion function: the single entry point the CLI and the web service wrap."""

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from typing import Literal, get_args

from pdf_to_doc.docx_output import render_docx
from pdf_to_doc.docx_reading import read_docx
from pdf_to_doc.intake import MAX_OUTPUTS, IntakeError, admit, open_pdf
from pdf_to_doc.markdown import render_markdown
from pdf_to_doc.model import Document, KeptImage
from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.paddle import default_engine
from pdf_to_doc.pdf_images import KEPT_DPI, lowered
from pdf_to_doc.progress import Opened, Progress, ProgressCallback
from pdf_to_doc.reading import read_pdf
from pdf_to_doc.summary import Summary, summarize

OutputFormat = Literal["markdown", "docx"]
# The file name extension of each output.
SUFFIXES: dict[OutputFormat, str] = {"markdown": ".md", "docx": ".docx"}
# The resolutions, in dots per inch, kept images may be lowered to when the outputs would pass
# MAX_OUTPUTS: the highest at which they fit is taken. At the lowest, the largest page Word takes
# is 440 pixels a side, and as colour noise, as hard as a scan gets to compress, a JPEG of 212 KB:
# 31 MB for 150 such pages. A picture is never sharper than the source file holds it either.
_LOWERED_DPI = (120, 100, 85, 72, 60, 50, 40, 30, 20)


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
    keep_images: bool = False,
) -> ConversionResult:
    """Convert a source file's bytes into the output format `to`, or into each format in a set of them.
    Every output is rendered from one reading of the source file, and shares one summary. A DOCX
    source never gives DOCX: asked for both formats, it gets Markdown only.

    `password` opens a PDF that needs one. `ocr` reads OCR pages; PaddleOCR does
    by default, and raises `ModelsMissing` if its models are not installed.
    `keep_images` keeps each scan of a PDF as an image of the page instead of reading it with OCR,
    and each picture as itself. Should the outputs then pass MAX_OUTPUTS, the kept images' resolution
    is lowered until they fit, and the summary says to what.
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
            document = read_pdf(pdf, (lambda: ocr) if ocr else default_engine, report, keep_images=keep_images)
    report(Progress(stage="writing"))
    outputs = _rendered(document, formats)
    if _size(outputs) > MAX_OUTPUTS and (images := document.kept_images()):
        rest = _size(outputs) - _bytes(images)
        del outputs  # as large as the limit or more, and of no more use while the images are lowered
        document, outputs = _within_the_limit(document, formats, rest)
    return ConversionResult(outputs=outputs, summary=summarize(document))


def _rendered(document: Document, formats: Set[OutputFormat]) -> dict[OutputFormat, bytes]:
    """An output for each format, in the order OutputFormat lists them, all with one summary."""
    summary = summarize(document)
    return {name: _render(document, summary, name) for name in get_args(OutputFormat) if name in formats}


def _render(document: Document, summary: Summary, to: OutputFormat) -> bytes:
    return render_docx(document, summary) if to == "docx" else render_markdown(document, summary).encode("utf-8")


def _size(outputs: Mapping[OutputFormat, bytes]) -> int:
    return sum(len(output) for output in outputs.values())


def _bytes(images: Iterable[KeptImage]) -> int:
    """What the images take in the DOCX, which holds each once."""
    return sum(len(image.data) for image in set(images))


def _within_the_limit(
    document: Document, formats: Set[OutputFormat], rest: int
) -> tuple[Document, dict[OutputFormat, bytes]]:
    """The document with its kept images lowered to the highest of `_LOWERED_DPI` at which the
    outputs fit within MAX_OUTPUTS, and those outputs; at the lowest, should none fit.

    The DOCX holds each image once, as it is, so whether a step fits is reckoned by the images
    alone, `rest` being all the outputs hold besides them. Lowering every image takes up to a
    second an image when a page is hard to compress, so the steps are not tried in turn. The
    first is guessed, as a JPEG shrinks about as its pixels do, with the square of the resolution;
    then the steps beside it are tried, up while they fit, or down until one does. The step found
    is rendered to be sure, and should the outputs still not fit, the next step down is taken.
    """
    images = document.kept_images()
    last = len(_LOWERED_DPI) - 1

    def lowered_images(step: int) -> dict[KeptImage, KeptImage]:
        """Each image, and the image lowered to the step's resolution."""
        return {image: lowered(image, _LOWERED_DPI[step]) for image in images}

    def fits(replacements: dict[KeptImage, KeptImage]) -> bool:
        return rest + _bytes(replacements.values()) <= MAX_OUTPUTS

    share = (MAX_OUTPUTS - rest) / _bytes(images)  # what the images must come down to
    step = next((step for step, dpi in enumerate(_LOWERED_DPI) if (dpi / KEPT_DPI) ** 2 <= share), last)
    replacements = lowered_images(step)
    if fits(replacements):  # up while the next step fits too
        while step > 0 and fits(sharper := lowered_images(step - 1)):
            step, replacements = step - 1, sharper
    while not fits(replacements) and step < last:  # down until one fits
        step += 1
        replacements = lowered_images(step)
    while True:
        lowered_document = document.with_kept_images(replacements, _LOWERED_DPI[step])
        outputs = _rendered(lowered_document, formats)
        if _size(outputs) <= MAX_OUTPUTS or step == last:
            return lowered_document, outputs
        step += 1
        replacements = lowered_images(step)

