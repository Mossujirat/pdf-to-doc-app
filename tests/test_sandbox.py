"""The sandbox entry point: a source file's bytes in on stdin, both outputs out on stdout,
and events on stderr, one JSON object per line."""

import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import docx_reader
import markdown_reader
import pytest
from fake_ocr import FailingEngine, FakeEngine
from pdf_builder import Scan, pdf, protected
from sandbox_reader import events, parts
from word_builder import Image, PageBreak, document, legacy_doc

from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.sandbox import run

SCANS = [["หน้าสแกนแรก"], ["หน้าสแกนที่สอง"]]


def mixed_pdf() -> bytes:
    return pdf(["หน้าที่มีข้อความ"], *(Scan(lines, dpi=50) for lines in SCANS))


@dataclass(frozen=True)
class InProcessRun:
    exit_code: int
    parts: dict[str, bytes]  # each part on stdout, by name
    events: list[dict[str, Any]]  # each line on stderr, read as JSON


def sandbox(source: bytes, ocr: OcrEngine | None = None) -> InProcessRun:
    stdout, stderr = io.BytesIO(), io.BytesIO()
    exit_code = run(io.BytesIO(source), stdout, stderr, ocr=ocr)
    return InProcessRun(exit_code, parts(stdout.getvalue()), events(stderr.getvalue()))


# Parts


def test_a_mixed_pdf_comes_back_as_both_outputs() -> None:
    ran = sandbox(mixed_pdf(), FakeEngine(*SCANS))

    assert ran.exit_code == 0
    assert list(ran.parts) == ["markdown", "docx"]
    pages = ["หน้าที่มีข้อความ", "หน้าสแกนแรก", "หน้าสแกนที่สอง"]
    assert markdown_reader.page_texts(ran.parts["markdown"].decode("utf-8")) == pages
    assert docx_reader.page_texts(ran.parts["docx"]) == pages


def test_a_docx_comes_back_as_markdown_only() -> None:
    ran = sandbox(document("หน้าแรก", PageBreak(), "หน้าที่สอง"))

    assert ran.exit_code == 0
    assert list(ran.parts) == ["markdown"]
    assert markdown_reader.page_texts(ran.parts["markdown"].decode("utf-8")) == ["หน้าแรก", "หน้าที่สอง"]


# Events


def test_a_mixed_pdf_reports_each_stage_then_the_summary() -> None:
    ran = sandbox(mixed_pdf(), FakeEngine(*SCANS))

    assert ran.events == [
        {"event": "opened", "source_type": "pdf", "pages": 3},
        {"event": "progress", "stage": "reading", "current": None, "total": None},
        {"event": "progress", "stage": "ocr", "current": 1, "total": 2},
        {"event": "progress", "stage": "ocr", "current": 2, "total": 2},
        {"event": "progress", "stage": "writing", "current": None, "total": None},
        {
            "event": "summary",
            "pages": [
                {"number": 1, "kind": "text", "engine": None, "untrusted_text_layer": False, "placeholders": [], "uncertain": 0},
                {"number": 2, "kind": "ocr", "engine": "fake", "untrusted_text_layer": False, "placeholders": [], "uncertain": 0},
                {"number": 3, "kind": "ocr", "engine": "fake", "untrusted_text_layer": False, "placeholders": [], "uncertain": 0},
            ],
        },
    ]


def test_a_docx_reports_its_pages_and_placeholders() -> None:
    ran = sandbox(document("หน้าแรก", Image(), PageBreak(), "หน้าที่สอง"))

    assert ran.events == [
        {"event": "opened", "source_type": "docx", "pages": 2},
        {"event": "progress", "stage": "writing", "current": None, "total": None},
        {
            "event": "summary",
            "pages": [
                {"number": 1, "kind": "text", "engine": None, "untrusted_text_layer": False, "placeholders": ["image"], "uncertain": 0},
                {"number": 2, "kind": "text", "engine": None, "untrusted_text_layer": False, "placeholders": [], "uncertain": 0},
            ],
        },
    ]


# Refusals: the exit codes are the CLI's


@pytest.mark.parametrize(
    ("source", "refusal", "exit_code"),
    [
        pytest.param(legacy_doc, {"kind": "UnsupportedFormat", "found": "doc"}, 3, id="legacy Word file"),
        pytest.param(
            lambda: pdf(*[[] for _ in range(151)]),
            {"kind": "TooLarge", "unit": "pages", "size": 151, "limit": 150},
            4,
            id="over 150 pages",
        ),
        pytest.param(
            lambda: protected(pdf(["เอกสารลับ"]), open_password="รหัสลับ"),
            {"kind": "PasswordRequired"},
            5,
            id="PDF needing a password",
        ),
    ],
)
def test_a_refusal_is_one_event_with_its_exit_code_and_no_parts(
    source: Callable[[], bytes], refusal: dict[str, Any], exit_code: int
) -> None:
    ran = sandbox(source())

    assert ran.exit_code == exit_code
    assert ran.events == [{"event": "refusal", **refusal}]
    assert ran.parts == {}


# Failures


def test_an_unexpected_error_is_named_by_its_type_alone() -> None:
    ran = sandbox(mixed_pdf(), FailingEngine(f"cannot read {SCANS[0][0]}"))

    # Not Python's 1, so a failure it reported is told apart from a crash it could not.
    assert ran.exit_code == 10
    assert ran.events == [
        {"event": "opened", "source_type": "pdf", "pages": 3},
        {"event": "progress", "stage": "reading", "current": None, "total": None},
        {"event": "progress", "stage": "ocr", "current": 1, "total": 2},
        {"event": "failure", "error": "RuntimeError"},
    ]
    assert ran.parts == {}


def test_missing_ocr_models_exit_with_the_cli_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PDF_TO_DOC_MODELS", str(tmp_path / "no-models-here"))

    ran = sandbox(mixed_pdf())

    assert ran.exit_code == 9
    assert ran.events[-1] == {"event": "failure", "error": "ModelsMissing"}
    assert ran.parts == {}
