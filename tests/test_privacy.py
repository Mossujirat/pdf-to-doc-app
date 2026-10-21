"""Privacy at runtime: a conversion never touches the network, and nothing of the
source file outlives it but the output.

Each conversion runs in a fresh process (see `fresh_process`), as a user's first one does.
Two checks look past what a user sees, on purpose: the files left in the temp area,
and the Paddle predictors still alive, which keep the last page they read.
"""

import json
from pathlib import Path

import pytest
from docx_reader import page_texts as docx_page_texts
from fresh_process import ConversionStopped, Run, SandboxRun, convert_in_fresh_process, sandbox_in_fresh_process
from markdown_reader import page_texts
from pdf_builder import Scan, pdf, protected
from sandbox_reader import events, parts
from word_builder import document

from pdf_to_doc.quality import score_page

TEXT_PAGE = ["สัญญาให้ทุนวิจัยเลขที่ ๐๔๑๗/๒๕๖๙ ระหว่างกองทุน", "ส่งเสริมการวิจัยกับบริษัทสยามอนาไลติกาจำกัด"]
SCANS = [
    ["ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้ทุกประการ", "และส่งรายงานความก้าวหน้าต่อผู้ให้ทุนทุกหกเดือน"],
    ["ผู้ให้ทุนจะจ่ายเงินเป็นงวดตามความก้าวหน้าของงาน", "ที่คณะกรรมการกำกับโครงการให้ความเห็นชอบแล้ว"],
]


def mixed() -> bytes:
    """A text page followed by two scans."""
    return pdf(TEXT_PAGE, *(Scan(lines) for lines in SCANS))


def leaked(log: str) -> list[str]:
    """Every run of 8 characters of the document's text, without a space, that the log holds."""
    lines = [*TEXT_PAGE, *SCANS[0], *SCANS[1]]
    fragments = {line[start : start + 8] for line in lines for start in range(len(line) - 7)}
    return sorted(fragment for fragment in fragments if " " not in fragment and fragment in log)


@pytest.fixture(scope="module")
def converted(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """The mixed file, converted once with real PaddleOCR."""
    return convert_in_fresh_process(tmp_path_factory.mktemp("converted"), mixed())


@pytest.mark.ocr
def test_a_first_conversion_succeeds_with_the_network_cut_off(converted: Run) -> None:
    assert converted.failure is None
    assert converted.network == []
    assert converted.output is not None
    markdown = converted.output.decode("utf-8")
    assert "ด้วย PaddleOCR" in markdown
    text_page, *scans = page_texts(markdown)
    assert text_page == "".join(TEXT_PAGE)
    for page, lines in zip(scans, SCANS, strict=True):
        assert score_page(page, "".join(lines)).cer < 0.05


@pytest.mark.ocr
def test_nothing_of_the_document_outlives_a_conversion(converted: Run) -> None:
    assert converted.failure is None
    assert converted.left_behind == []
    assert converted.paddle_objects_alive == 0


@pytest.mark.ocr
def test_the_log_of_a_conversion_holds_none_of_the_document(converted: Run) -> None:
    assert converted.failure is None
    assert leaked(converted.log) == []


@pytest.mark.ocr
def test_nothing_of_the_document_outlives_a_conversion_that_fails_partway(tmp_path: Path) -> None:
    run = convert_in_fresh_process(tmp_path, mixed(), stop_at_ocr_page=2)

    assert run.failure == ConversionStopped.__name__
    assert run.left_behind == []
    assert run.paddle_objects_alive == 0
    assert leaked(run.log) == []


def test_a_conversion_to_docx_leaves_nothing_behind_and_logs_none_of_the_document(tmp_path: Path) -> None:
    run = convert_in_fresh_process(tmp_path, pdf(TEXT_PAGE), to="docx")

    assert run.failure is None
    assert run.output is not None
    assert docx_page_texts(run.output) == ["".join(TEXT_PAGE)]
    assert run.network == []
    assert run.left_behind == []
    assert leaked(run.log) == []


def test_a_docx_source_converts_leaving_nothing_behind_and_logging_none_of_it(tmp_path: Path) -> None:
    run = convert_in_fresh_process(tmp_path, document(*TEXT_PAGE))

    assert run.failure is None
    assert run.output is not None
    assert page_texts(run.output.decode("utf-8")) == ["\n\n".join(TEXT_PAGE)]
    assert run.network == []
    assert run.left_behind == []
    assert leaked(run.log) == []


def test_nothing_of_the_document_outlives_a_refusal(tmp_path: Path) -> None:
    run = convert_in_fresh_process(tmp_path, protected(mixed(), open_password="รหัสลับ"))

    assert run.failure == "PasswordRequired"
    assert run.left_behind == []
    assert leaked(run.log) == []


# The sandbox entry point, as the launcher runs it


@pytest.fixture(scope="module")
def sandboxed(tmp_path_factory: pytest.TempPathFactory) -> SandboxRun:
    """The mixed file through the sandbox entry point once, with real PaddleOCR on 2 threads."""
    return sandbox_in_fresh_process(tmp_path_factory.mktemp("sandboxed"), mixed(), ocr_threads=2)


@pytest.mark.ocr
def test_the_sandbox_converts_with_the_network_cut_off(sandboxed: SandboxRun) -> None:
    assert sandboxed.exit_code == 0
    assert sandboxed.network == []
    outputs = parts(sandboxed.stdout)
    assert list(outputs) == ["markdown", "docx"]
    text_page, *scans = page_texts(outputs["markdown"].decode("utf-8"))
    assert text_page == "".join(TEXT_PAGE)
    for page, lines in zip(scans, SCANS, strict=True):
        assert score_page(page, "".join(lines)).cer < 0.05
    assert docx_page_texts(outputs["docx"])[0] == "".join(TEXT_PAGE)


@pytest.mark.ocr
def test_nothing_of_the_document_outlives_the_sandbox(sandboxed: SandboxRun) -> None:
    assert sandboxed.exit_code == 0
    assert sandboxed.left_behind == []
    assert sandboxed.paddle_objects_alive == 0


@pytest.mark.ocr
def test_the_sandbox_writes_nothing_to_stderr_but_events_free_of_the_document(sandboxed: SandboxRun) -> None:
    written = events(sandboxed.stderr)

    assert [event["event"] for event in written] == ["opened", "progress", "progress", "progress", "progress", "summary"]
    assert leaked(json.dumps(written, ensure_ascii=False)) == []
