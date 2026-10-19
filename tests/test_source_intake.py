"""Source intake: a file the converter cannot or will not convert is refused, with its own error and exit code."""

import io
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest
from markdown_reader import page_texts
from pdf_builder import OWNER_PASSWORD, grown_to, pdf, protected
from word_builder import docx, legacy_doc

from pdf_to_doc import (
    CopyRestricted,
    DamagedFile,
    PasswordRequired,
    TooLarge,
    UnsupportedFormat,
    WrongPassword,
    convert,
)
from pdf_to_doc.cli import main


def test_a_legacy_word_file_is_refused() -> None:
    with pytest.raises(UnsupportedFormat) as refusal:
        convert(legacy_doc())

    assert refusal.value.found == "doc"


def test_a_file_that_is_neither_pdf_nor_docx_is_refused() -> None:
    with pytest.raises(UnsupportedFormat) as refusal:
        convert("สัญญาให้ทุนโครงการ".encode())

    assert refusal.value.found is None


def test_a_zip_archive_that_is_not_a_word_document_is_refused() -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as files:
        files.writestr("xl/workbook.xml", "<workbook/>")

    with pytest.raises(UnsupportedFormat) as refusal:
        convert(archive.getvalue())

    assert refusal.value.found is None


def test_a_docx_is_recognised_but_not_converted_yet() -> None:
    with pytest.raises(UnsupportedFormat) as refusal:
        convert(docx("สัญญาให้ทุนโครงการ"))

    assert refusal.value.found == "docx"


def cut_short_pdf() -> bytes:
    return pdf(["หน้าแรก"])[:200]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(cut_short_pdf, id="PDF"),
        pytest.param(lambda: docx("หน้าแรก")[:-30], id="DOCX"),
    ],
)
def test_a_file_cut_short_is_refused_as_damaged(source: Callable[[], bytes]) -> None:
    with pytest.raises(DamagedFile):
        convert(source())


# Limits

MB = 1024 * 1024


def pdf_of_size(size: int) -> bytes:
    return grown_to(pdf(["หน้าแรก"]), size)


def test_a_file_over_50_mb_is_refused() -> None:
    with pytest.raises(TooLarge) as refusal:
        convert(pdf_of_size(50 * MB + 1))

    assert (refusal.value.unit, refusal.value.limit) == ("bytes", 50 * MB)


def test_a_file_of_exactly_50_mb_converts() -> None:
    result = convert(pdf_of_size(50 * MB))

    assert page_texts(result.output.decode("utf-8")) == ["หน้าแรก"]


def blank_pages(count: int) -> bytes:
    return pdf(*[[] for _ in range(count)])


def test_a_pdf_over_150_pages_is_refused() -> None:
    with pytest.raises(TooLarge) as refusal:
        convert(blank_pages(151))

    assert (refusal.value.unit, refusal.value.size, refusal.value.limit) == ("pages", 151, 150)


def test_a_pdf_of_exactly_150_pages_converts() -> None:
    assert len(convert(blank_pages(150)).summary.pages) == 150


# Protected PDFs


PASSWORD = "รหัสลับ๑๒๓"  # Thai, as Thai users set them


def locked_pdf() -> bytes:
    return protected(pdf(["เอกสารลับ"]), open_password=PASSWORD)


def test_a_pdf_that_needs_a_password_is_refused_without_one() -> None:
    with pytest.raises(PasswordRequired):
        convert(locked_pdf())


def test_a_pdf_that_needs_a_password_converts_with_the_right_one() -> None:
    result = convert(locked_pdf(), password=PASSWORD)

    assert page_texts(result.output.decode("utf-8")) == ["เอกสารลับ"]


def test_a_wrong_password_is_refused() -> None:
    with pytest.raises(WrongPassword):
        convert(locked_pdf(), password="guess")


def no_copy_pdf() -> bytes:
    return protected(pdf(["เอกสารลับ"]), allow_copy=False)


def test_a_pdf_whose_permissions_forbid_copying_text_is_refused() -> None:
    with pytest.raises(CopyRestricted):
        convert(no_copy_pdf())


@pytest.mark.parametrize("open_password", ["", PASSWORD], ids=["opens freely", "needs a password"])
def test_the_owner_password_does_not_lift_a_copy_restriction(open_password: str) -> None:
    source = protected(pdf(["เอกสารลับ"]), open_password=open_password, allow_copy=False)

    with pytest.raises(CopyRestricted):
        convert(source, password=OWNER_PASSWORD)


# The command line


def test_the_command_reads_the_type_from_the_content_not_the_name(tmp_path: Path) -> None:
    source = tmp_path / "contract.docx"
    source.write_bytes(pdf(["สัญญาให้ทุนโครงการ"]))

    assert main([str(source)]) == 0
    assert page_texts((tmp_path / "contract.md").read_text(encoding="utf-8")) == ["สัญญาให้ทุนโครงการ"]


@pytest.mark.parametrize("name", ["missing.pdf", "folder"])
def test_the_command_reports_a_source_path_it_cannot_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    (tmp_path / "folder").mkdir()

    with pytest.raises(SystemExit) as stop:
        main([str(tmp_path / name)])

    assert stop.value.code == 2
    assert "อ่านไฟล์" in capsys.readouterr().err


def test_the_command_opens_a_locked_pdf_with_its_password(tmp_path: Path) -> None:
    source = tmp_path / "secret.pdf"
    source.write_bytes(locked_pdf())

    assert main([str(source), "--password", PASSWORD]) == 0
    assert page_texts((tmp_path / "secret.md").read_text(encoding="utf-8")) == ["เอกสารลับ"]


@pytest.mark.parametrize(
    ("source", "options", "exit_code", "message"),
    [
        pytest.param(legacy_doc, [], 3, "บันทึกเป็น .docx", id="legacy Word file"),
        pytest.param(lambda: "ข้อความธรรมดา".encode(), [], 3, "ไม่ใช่ PDF หรือ DOCX", id="neither PDF nor DOCX"),
        pytest.param(lambda: docx("สัญญา"), [], 3, "ยังแปลงไฟล์ DOCX ไม่ได้", id="DOCX"),
        pytest.param(lambda: pdf_of_size(50 * MB + 1), [], 4, "50 MB", id="over 50 MB"),
        pytest.param(lambda: blank_pages(151), [], 4, "150 หน้า", id="over 150 pages"),
        pytest.param(locked_pdf, [], 5, "--password", id="password required"),
        pytest.param(locked_pdf, ["--password", "guess"], 6, "รหัสผ่านไม่ถูกต้อง", id="wrong password"),
        pytest.param(no_copy_pdf, [], 7, "ห้ามคัดลอกข้อความ", id="copy restricted"),
        pytest.param(cut_short_pdf, [], 8, "ไฟล์เสีย", id="damaged file"),
    ],
)
def test_the_command_explains_a_refusal_and_writes_no_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    source: Callable[[], bytes],
    options: list[str],
    exit_code: int,
    message: str,
) -> None:
    path = tmp_path / "source"
    path.write_bytes(source())

    assert main([str(path), *options]) == exit_code
    assert message in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == [path]
