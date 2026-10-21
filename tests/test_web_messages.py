"""The messages for a file that cannot be converted: every refusal in the command line's words,
the web's own for what only the web meets, and never the sandbox's own text."""

from collections.abc import Callable, Iterator

import pytest
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from pdf_builder import pdf, protected
from scripted_sandbox import ScriptedSandbox
from web_browser import browser, converted
from word_builder import docx_unpacking_to, legacy_doc, locked_docx

from pdf_to_doc.web.sandboxes import Ended

MB = 1024 * 1024


@pytest.fixture
def client() -> Iterator[TestClient]:
    with browser(FakeSandbox()) as client:
        yield client


@pytest.mark.parametrize(
    ("source", "message"),
    [
        pytest.param(legacy_doc, "ไฟล์นี้เป็น Word รุ่นเก่า (.doc) ซึ่งแปลงไม่ได้", id="legacy Word file"),
        pytest.param(locked_docx, "ไฟล์ Office นี้ล็อกด้วยรหัสผ่าน จึงแปลงไม่ได้", id="locked Office file"),
        pytest.param(lambda: "ข้อความธรรมดา".encode(), "ไฟล์นี้ไม่ใช่ PDF หรือ DOCX", id="neither PDF nor DOCX"),
        pytest.param(
            lambda: docx_unpacking_to(200 * MB + 1),
            "ไฟล์ DOCX นี้เมื่อแตกออกมาใหญ่ 200.1 MB เกินขนาดสูงสุดที่แปลงได้ 200 MB",
            id="DOCX unpacking over 200 MB",
        ),
        pytest.param(
            lambda: pdf(*[[] for _ in range(151)]),
            "ไฟล์นี้มี 151 หน้า เกินจำนวนสูงสุดที่แปลงได้ 150 หน้า",
            id="over 150 pages",
        ),
        pytest.param(
            lambda: protected(pdf(["เอกสารลับ"]), allow_copy=False),
            "ไฟล์ PDF นี้ตั้งสิทธิ์ห้ามคัดลอกข้อความ",
            id="copying forbidden",
        ),
        pytest.param(lambda: pdf(["หน้าแรก"])[:200], "ไฟล์เสียหรือไม่สมบูรณ์", id="damaged file"),
    ],
)
def test_a_refused_file_gets_the_command_lines_message(
    client: TestClient, source: Callable[[], bytes], message: str
) -> None:
    state, page = converted(client, source())

    assert state == "refused"
    assert message in page


def test_a_pdf_that_needs_a_password_gets_the_webs_own_message(client: TestClient) -> None:
    state, page = converted(client, protected(pdf(["เอกสารลับ"]), open_password="รหัสลับ"))

    assert state == "refused"
    assert "ยังแปลง PDF ที่ล็อกด้วยรหัสผ่านไม่ได้ กรุณาปลดรหัสผ่านออกแล้วส่งไฟล์มาใหม่" in page
    assert "--password" not in page


@pytest.mark.parametrize("kind", ["DamagedFile", "PasswordRequired", "WrongPassword", "CopyRestricted", "DocxToDocx"])
def test_every_refusal_a_sandbox_can_send_gets_a_message(kind: str) -> None:
    # Two of these never come from a web conversion, which takes no password and asks for
    # both outputs; a sandbox could still send them.
    sandbox = ScriptedSandbox([f'{{"event": "refusal", "kind": "{kind}"}}'.encode()], Ended(3, b""))
    with browser(sandbox) as client:
        state, page = converted(client, pdf(["หน้าแรก"]))

    assert state == "refused"
    assert "แปลงไฟล์นี้ไม่ได้" in page


OPENED = b'{"event": "opened", "source_type": "pdf", "pages": 3}'


def test_a_failed_conversion_says_to_try_again_and_shows_nothing_from_the_sandbox() -> None:
    sandbox = ScriptedSandbox([OPENED, b'{"event": "failure", "error": "MemoryError"}'], Ended(10, b""))
    with browser(sandbox) as client:
        state, page = converted(client, pdf(["หน้าแรก"]))

    assert state == "failed"
    assert "การแปลงล้มเหลว" in page
    assert "กรุณาลองใหม่อีกครั้ง" in page
    assert "MemoryError" not in page


def test_a_conversion_stopped_by_the_time_limit_says_so_and_to_try_again() -> None:
    sandbox = ScriptedSandbox([OPENED], Ended(137, b"", timed_out=True))
    with browser(sandbox) as client:
        state, page = converted(client, pdf(["หน้าแรก"]))

    assert state == "failed"
    assert "การแปลงใช้เวลานานเกินกำหนดจึงถูกหยุด" in page
    assert "กรุณาลองใหม่อีกครั้ง" in page
