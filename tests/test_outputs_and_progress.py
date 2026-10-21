"""Both outputs from one conversion, and the progress it reports from the moment the source file is open."""

from collections.abc import Callable

import docx_reader
import markdown_reader
import pytest
from fake_ocr import FakeEngine
from pdf_builder import Scan, pdf, protected
from word_builder import Block, PageBreak, docx, document

from pdf_to_doc import DocxToDocx, IntakeError, Opened, Progress, convert
from pdf_to_doc.conversion import OutputFormat


def mixed_pdf() -> bytes:
    return pdf(["หน้าที่มีข้อความ"], Scan(["หน้าสแกนแรก"], dpi=50), Scan(["หน้าสแกนที่สอง"], dpi=50))


def engine_for_scans() -> FakeEngine:
    return FakeEngine(["หน้าสแกนแรก"], ["หน้าสแกนที่สอง"])


# Outputs


def test_both_outputs_from_one_conversion_read_the_same_as_each_on_its_own() -> None:
    markdown = convert(mixed_pdf(), to="markdown", ocr=engine_for_scans()).output
    word = convert(mixed_pdf(), to="docx", ocr=engine_for_scans()).output
    engine = engine_for_scans()

    both = convert(mixed_pdf(), to={"markdown", "docx"}, ocr=engine)

    assert both.outputs["markdown"] == markdown
    assert docx_reader.page_texts(both.outputs["docx"]) == docx_reader.page_texts(word)
    assert docx_reader.read_docx(both.outputs["docx"]).summary.text == docx_reader.read_docx(word).summary.text
    assert markdown_reader.page_texts(markdown.decode("utf-8")) == ["หน้าที่มีข้อความ", "หน้าสแกนแรก", "หน้าสแกนที่สอง"]
    assert len(engine.images) == 2  # each scan read once, for both outputs


def test_a_docx_asked_for_both_outputs_gets_markdown_only() -> None:
    source = document("หน้าแรก", PageBreak(), "หน้าที่สอง")

    result = convert(source, to={"markdown", "docx"})

    assert list(result.outputs) == ["markdown"]
    assert result.output == convert(source).output
    assert markdown_reader.page_texts(result.output.decode("utf-8")) == ["หน้าแรก", "หน้าที่สอง"]


def test_a_docx_asked_for_docx_alone_is_still_refused() -> None:
    with pytest.raises(DocxToDocx):
        convert(docx("สัญญาให้ทุนโครงการ"), to={"docx"})


def test_asking_for_no_output_is_refused() -> None:
    # Found in review: the whole file was read, OCR and all, for no output.
    with pytest.raises(ValueError):
        convert(pdf(["หน้าแรก"]), to=set())


# Progress


def test_a_text_only_pdf_reports_its_page_count_then_reading_then_writing() -> None:
    reports: list[Opened | Progress] = []

    convert(pdf(["หน้าแรก"], ["หน้าที่สอง"]), progress=reports.append)

    assert reports == [Opened(source_type="pdf", pages=2), Progress(stage="reading"), Progress(stage="writing")]


def test_a_mixed_pdf_reports_each_ocr_page_as_current_of_total_between_reading_and_writing() -> None:
    reports: list[Opened | Progress] = []

    convert(mixed_pdf(), ocr=engine_for_scans(), progress=reports.append)

    assert reports == [
        Opened(source_type="pdf", pages=3),
        Progress(stage="reading"),
        Progress(stage="ocr", current=1, total=2),
        Progress(stage="ocr", current=2, total=2),
        Progress(stage="writing"),
    ]


def test_a_docx_reports_its_page_count_once_counted_then_writing() -> None:
    # A DOCX's pages are counted by reading it, so there is no reading left to report.
    reports: list[Opened | Progress] = []

    convert(document("หน้าแรก", PageBreak(), "หน้าที่สอง"), progress=reports.append)

    assert reports == [Opened(source_type="docx", pages=2), Progress(stage="writing")]


def docx_of_pages(count: int) -> bytes:
    pages: list[Block] = []
    for number in range(count):
        pages += [f"หน้าที่ {number + 1}", PageBreak()]
    return document(*pages[:-1])


@pytest.mark.parametrize(
    ("source", "to"),
    [
        pytest.param(lambda: pdf(*[[] for _ in range(151)]), "markdown", id="PDF over 150 pages"),
        pytest.param(lambda: protected(pdf(["เอกสารลับ"]), open_password="รหัสลับ"), "markdown", id="PDF needing a password"),
        pytest.param(lambda: docx_of_pages(151), "markdown", id="DOCX over 150 pages"),
        pytest.param(lambda: docx("สัญญาให้ทุนโครงการ"), "docx", id="DOCX to DOCX"),
    ],
)
def test_a_refusal_at_intake_comes_before_any_report(source: Callable[[], bytes], to: OutputFormat) -> None:
    reports: list[Opened | Progress] = []

    with pytest.raises(IntakeError):
        convert(source(), to=to, progress=reports.append)

    assert reports == []
