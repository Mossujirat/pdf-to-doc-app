"""The web service, used the way a browser uses it: HTTP requests in, pages, messages and
downloads out. A fake sandbox runs the real conversion function with a fake OCR engine."""

import asyncio
import re
import threading
from collections.abc import Iterator, MutableMapping
from dataclasses import replace
from typing import Any
from urllib.parse import unquote

import docx_reader
import markdown_reader
import pytest
from fake_ocr import FailingEngine, FakeEngine
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from held_sandbox import HeldSandbox
from pdf_builder import Scan, grown_to, pdf
from scripted_sandbox import ScriptedSandbox
from web_browser import (
    SETTINGS,
    as_browser,
    browser,
    browser_token,
    ended_state,
    send,
    shown_text,
    upload,
    wait_for_state,
)
from word_builder import Image, PageBreak, document, legacy_doc

from pdf_to_doc.ocr import Language, PageImage, TextBox
from pdf_to_doc.web.app import create_app
from pdf_to_doc.web.sandboxes import Ended, LocalSandbox

SCANS = [["หน้าสแกนแรก"], ["หน้าสแกนที่สอง"]]
PAGES = ["หน้าที่มีข้อความ", "หน้าสแกนแรก", "หน้าสแกนที่สอง"]


def mixed_pdf() -> bytes:
    return pdf([PAGES[0]], *(Scan(lines, dpi=50) for lines in SCANS))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with browser(FakeSandbox(lambda: FakeEngine(*SCANS))) as client:
        yield client


class HeldEngine(FakeEngine):
    """Reads each page only once the test lets it go on."""

    def __init__(self, *pages: list[str], go_on: threading.Event) -> None:
        super().__init__(*pages)
        self._go_on = go_on

    def read(self, image: PageImage, languages: tuple[Language, ...]) -> tuple[TextBox, ...]:
        assert self._go_on.wait(timeout=30)
        return super().read(image, languages)


# Converting a file


def test_a_mixed_pdf_converts_to_both_outputs(client: TestClient) -> None:
    link = upload(client, mixed_pdf())

    assert ended_state(client, link) == "finished"
    page = client.get(link).text
    assert "3 หน้า: อ่านจากข้อความในไฟล์ 1 หน้า, อ่านด้วย OCR 2 หน้า ได้แก่หน้า 2–3 ด้วย fake" in page
    markdown = client.get(f"{link}/markdown")
    assert markdown_reader.page_texts(markdown.content.decode("utf-8")) == PAGES
    assert docx_reader.page_texts(client.get(f"{link}/docx").content) == PAGES


def test_the_conversion_page_shows_the_ocr_page_being_read() -> None:
    go_on = threading.Event()
    with browser(FakeSandbox(lambda: HeldEngine(*SCANS, go_on=go_on))) as client:
        link = upload(client, mixed_pdf())

        wait_for_state(client, link, lambda state: state["text"] == "OCR หน้า 1/2")
        assert "OCR หน้า 1/2" in client.get(link).text
        go_on.set()
        assert ended_state(client, link) == "finished"


@pytest.mark.parametrize(
    ("keep_images", "headline", "markdown"),
    [
        pytest.param("no", "อ่านด้วย OCR 1 หน้า", "หน้าสแกนแรก", id="OCR"),
        pytest.param("yes", "เก็บเป็นภาพ 1 หน้า", "[หน้าสแกน]", id="kept images"),
        pytest.param(None, "อ่านด้วย OCR 1 หน้า", "หน้าสแกนแรก", id="a form from before the choice"),
    ],
)
def test_the_choice_of_kept_images_goes_with_the_file(
    client: TestClient, keep_images: str | None, headline: str, markdown: str
) -> None:
    link = upload(client, pdf(Scan(SCANS[0], dpi=50)), keep_images=keep_images)

    assert ended_state(client, link) == "finished"
    assert headline in client.get(link).text
    assert markdown_reader.page_texts(client.get(f"{link}/markdown").text) == [markdown]


def test_a_choice_the_form_does_not_offer_is_refused_as_not_an_upload(client: TestClient) -> None:
    response = send(client, pdf(Scan(SCANS[0], dpi=50)), keep_images="both")

    assert response.status_code == 400
    assert "ไม่ได้รับไฟล์" in response.text


OPENED = b'{"event": "opened", "source_type": "pdf", "pages": 2}'
READING = b'{"event": "progress", "stage": "reading", "current": null, "total": null}'
KEEPING_PAGES = b'{"event": "progress", "stage": "images", "current": 1, "total": 2}'


def steps_of(state: dict[str, Any]) -> list[tuple[str, str]]:
    """Each step the conversion's page lists, with where the conversion is at it."""
    return re.findall(r'data-step="(\w+)" data-at="(\w+)"', state["steps"])


def test_the_conversion_page_shows_pages_being_kept_as_images() -> None:
    held = HeldSandbox(reports=(OPENED, READING, KEEPING_PAGES))
    with browser(held) as client:
        link = upload(client, pdf(["หน้าแรก"]), keep_images="yes")

        state = wait_for_state(client, link, lambda state: state["text"] == "เก็บภาพหน้า 1/2")
        assert steps_of(state) == [
            ("queue", "done"),
            ("open", "done"),
            ("read", "done"),
            ("images", "now"),
            ("ocr", "later"),
            ("write", "later"),
        ]
        assert "เก็บหน้าสแกนเป็นภาพ" in state["steps"] and "หน้า 1/2" in state["steps"]
        assert '<progress class="step-meter" max="2" value="1">' in state["steps"]
        held.started[0].end()


def test_a_file_with_no_page_to_keep_shows_keeping_pages_as_images_as_not_needed() -> None:
    held = HeldSandbox()  # it goes straight to its first OCR page
    with browser(held) as client:
        link = upload(client, pdf(["หน้าแรก"]), keep_images="yes")

        state = wait_for_state(client, link, lambda state: state["text"] == "OCR หน้า 1/2")
        assert ("images", "skipped") in steps_of(state)
        assert "ไม่ต้องใช้" in state["steps"]
        held.started[0].end()


@pytest.mark.parametrize(
    ("keep_images", "steps"),
    [
        pytest.param(None, ["queue", "open", "read", "ocr", "write"], id="OCR"),
        pytest.param("yes", ["queue", "open", "read", "images", "ocr", "write"], id="kept images"),
    ],
)
def test_keeping_pages_as_images_is_listed_only_when_images_are_kept(keep_images: str | None, steps: list[str]) -> None:
    held = HeldSandbox()
    with browser(held, replace(SETTINGS, max_running=1)) as client:
        upload(as_browser(client, browser_token()), pdf(["หน้าแรก"]))
        waiting = upload(as_browser(client, browser_token()), pdf(["หน้าแรก"]), keep_images=keep_images)

        state = wait_for_state(client, waiting, lambda state: state["state"] == "waiting")
        assert steps_of(state) == [(step, "now" if step == "queue" else "later") for step in steps]
        held.started[0].end()


def page_rows(page: str) -> list[list[str]]:
    """The finished conversion's table, a row for each page, each cell as a visitor reads it."""
    rows = page.split("<tbody>")[1].split("</tbody>")[0].split("</tr>")[:-1]
    return [[shown_text(cell).strip() for cell in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row)] for row in rows]


def test_the_finished_table_says_which_pages_were_kept_and_why_a_kept_pages_text_was_left_out() -> None:
    summary = (
        b'{"event": "summary", "pages": ['
        b'{"number": 1, "kind": "text", "engine": null, "untrusted_text_layer": false, "placeholders": [], "uncertain": 0, "tables": 0, "incomplete_tables": 0}, '
        b'{"number": 2, "kind": "ocr", "engine": "fake", "untrusted_text_layer": true, "placeholders": [], "uncertain": 0, "tables": 0, "incomplete_tables": 0}, '
        b'{"number": 3, "kind": "kept", "engine": null, "untrusted_text_layer": false, "placeholders": [], "uncertain": 0, "tables": 0, "incomplete_tables": 0}, '
        b'{"number": 4, "kind": "kept", "engine": null, "untrusted_text_layer": true, "placeholders": [], "uncertain": 0, "tables": 0, "incomplete_tables": 0}]}'
    )
    with browser(ScriptedSandbox([summary], Ended(0, b"markdown 0\n"))) as client:
        link = upload(client, pdf(["หน้าแรก"]), keep_images="yes")

        assert ended_state(client, link) == "finished"
        page = client.get(link).text
    assert "เก็บเป็นภาพ 2 หน้า ได้แก่หน้า 3–4 (หน้า 4 ข้อความในไฟล์ไม่น่าเชื่อถือ จึงไม่ได้นำมาใช้)" in page
    assert page_rows(page) == [
        ["หน้า 1", "ข้อความในไฟล์", "–"],
        ["หน้า 2", "อ่านด้วย OCR", "ข้อความในไฟล์ผิด จึงอ่านด้วย OCR"],
        ["หน้า 3", "เก็บเป็นภาพ", "–"],
        ["หน้า 4", "เก็บเป็นภาพ", "ข้อความในไฟล์ผิด จึงไม่ได้นำมาใช้"],
    ]


def test_the_finished_table_notes_tables_and_incomplete_tables_apart_from_placeholders_and_tags_those_to_check() -> None:
    summary = (
        b'{"event": "summary", "pages": ['
        b'{"number": 1, "kind": "ocr", "engine": "fake", "untrusted_text_layer": false, "placeholders": [], "uncertain": 0, "tables": 2, "incomplete_tables": 0}, '
        b'{"number": 2, "kind": "ocr", "engine": "fake", "untrusted_text_layer": false, "placeholders": [], "uncertain": 0, "tables": 1, "incomplete_tables": 1}, '
        b'{"number": 3, "kind": "text", "engine": null, "untrusted_text_layer": false, "placeholders": ["image"], "uncertain": 0, "tables": 0, "incomplete_tables": 0}]}'
    )
    with browser(ScriptedSandbox([summary], Ended(0, b"markdown 0\n"))) as client:
        link = upload(client, pdf(["หน้าแรก"]))

        assert ended_state(client, link) == "finished"
        page = client.get(link).text
    assert "ตารางในหน้าที่อ่านด้วย OCR: เป็นตาราง 3 ตาราง, อาจไม่สมบูรณ์ 1 ตาราง ในหน้า 2 ควรตรวจโครงสร้างกับต้นฉบับ" in page
    assert page_rows(page) == [
        ["หน้า 1", "อ่านด้วย OCR", "ตาราง 2"],
        ["หน้า 2", "อ่านด้วย OCR", "ตรวจ ตาราง 1 · ตารางอาจไม่สมบูรณ์ 1"],
        ["หน้า 3", "ข้อความในไฟล์", "รูปภาพ 1"],
    ]
    assert "ควรตรวจ 1 หน้า" in page


def test_a_docx_gives_markdown_only(client: TestClient) -> None:
    link = upload(client, document("หน้าแรก", Image(), PageBreak(), "หน้าที่สอง"), name="สัญญา.docx")

    assert ended_state(client, link) == "finished"
    page = client.get(link).text
    assert "ส่วนที่ไม่ได้ถอดเป็นข้อความ: รูปภาพ 1 จุด" in page
    assert "ดาวน์โหลด DOCX" not in page
    assert markdown_reader.page_texts(client.get(f"{link}/markdown").text) == ["หน้าแรก\n\n[รูปภาพ]", "หน้าที่สอง"]
    assert client.get(f"{link}/docx").status_code == 404


def test_the_downloads_are_named_after_the_source_file_in_thai(client: TestClient) -> None:
    link = upload(client, mixed_pdf(), name="สัญญาจ้าง ฉบับที่ 2.pdf")
    ended_state(client, link)

    names = [client.get(f"{link}/{output}").headers["content-disposition"] for output in ("markdown", "docx")]

    assert [unquote(name.split("filename*=UTF-8''")[1]) for name in names] == [
        "สัญญาจ้าง ฉบับที่ 2.md",
        "สัญญาจ้าง ฉบับที่ 2.docx",
    ]


def test_the_local_sandbox_converts_in_a_process_of_its_own() -> None:
    # A text-only PDF, so the subprocess loads no OCR models.
    with browser(LocalSandbox()) as client:
        link = upload(client, pdf(["หน้าแรก"], ["หน้าที่สอง"]))

        assert ended_state(client, link) == "finished"
        assert markdown_reader.page_texts(client.get(f"{link}/markdown").text) == ["หน้าแรก", "หน้าที่สอง"]
        assert docx_reader.page_texts(client.get(f"{link}/docx").content) == ["หน้าแรก", "หน้าที่สอง"]


def test_the_local_sandbox_keeps_images_when_chosen() -> None:
    # Kept, the scan loads no OCR models in the subprocess either.
    with browser(LocalSandbox()) as client:
        link = upload(client, pdf(Scan(SCANS[0], dpi=50)), keep_images="yes")

        assert ended_state(client, link) == "finished"
        assert markdown_reader.page_texts(client.get(f"{link}/markdown").text) == ["[หน้าสแกน]"]


# The size limit

MB = 1024 * 1024


def test_a_file_just_over_50_mb_is_refused(client: TestClient) -> None:
    response = client.post("/conversions", files={"file": ("ใหญ่.pdf", bytes(50 * MB + 1))}, follow_redirects=False)

    assert response.status_code == 413
    assert "ใหญ่เกินขนาดสูงสุดที่แปลงได้ 50 MB" in response.text


def test_an_upload_that_says_it_is_over_50_mb_is_refused_before_any_of_it_is_read() -> None:
    # Spoken to as the web server speaks to the app, to see whether the body is ever asked for.
    asked_for_the_body = False
    sent: list[MutableMapping[str, Any]] = []

    async def receive() -> dict[str, Any]:
        nonlocal asked_for_the_body
        asked_for_the_body = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        sent.append(message)

    headers = [
        (b"host", b"testserver"),
        (b"origin", b"https://testserver"),  # from the site's own page, as a browser says
        (b"content-type", b"multipart/form-data; boundary=edge"),
        (b"content-length", str(51 * MB).encode()),
    ]
    scope = {"type": "http", "method": "POST", "path": "/conversions", "headers": headers, "query_string": b""}
    asyncio.run(create_app(FakeSandbox())(scope, receive, send))

    assert sent[0]["status"] == 413
    assert not asked_for_the_body


def test_a_file_over_50_mb_sent_without_a_length_is_refused_while_reading(client: TestClient) -> None:
    def form() -> Iterator[bytes]:
        yield b'--edge\r\nContent-Disposition: form-data; name="file"; filename="big.pdf"\r\n\r\n'
        for _ in range(51):
            yield bytes(MB)
        yield b"\r\n--edge--\r\n"

    response = client.post(
        "/conversions",
        content=form(),
        headers={"content-type": "multipart/form-data; boundary=edge"},
        follow_redirects=False,
    )

    assert response.status_code == 413
    assert "ใหญ่เกินขนาดสูงสุดที่แปลงได้ 50 MB" in response.text


def test_a_file_of_exactly_50_mb_is_taken(client: TestClient) -> None:
    link = upload(client, grown_to(pdf(["หน้าแรก"]), 50 * MB))

    assert ended_state(client, link) == "finished"
    assert markdown_reader.page_texts(client.get(f"{link}/markdown").text) == ["หน้าแรก"]


# Only the browser that sent the file


def test_another_browser_cannot_open_a_conversion(client: TestClient) -> None:
    link = upload(client, mixed_pdf())
    ended_state(client, link)

    with TestClient(client.app, base_url="https://testserver") as other:  # the same service, another cookie jar
        for address in (link, f"{link}/state", f"{link}/markdown", f"{link}/docx"):
            response = other.get(address)
            assert response.status_code == 404
            assert "ไม่พบหน้านี้" in response.text


def test_an_unknown_link_is_not_found(client: TestClient) -> None:
    upload(client, mixed_pdf())

    response = client.get("/conversions/no-such-conversion")

    assert response.status_code == 404
    assert "ไม่พบหน้านี้" in response.text


@pytest.mark.parametrize("secure", [True, False], ids=["production", "local development"])
def test_the_browser_token_is_a_strict_http_only_cookie_for_a_day(secure: bool) -> None:
    with browser(FakeSandbox(), replace(SETTINGS, secure_cookies=secure)) as client:
        response = send(client, pdf(["หน้าแรก"]))

    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "max-age=86400" in cookie
    assert ("secure" in cookie.split("; ")) is secure


def test_a_token_the_service_did_not_make_is_replaced(client: TestClient) -> None:
    client.cookies.set("browser", "guessed")

    response = send(client, pdf(["หน้าแรก"]))

    token = response.headers["set-cookie"].split(";")[0].removeprefix("browser=")
    assert token != "guessed"
    assert len(token) >= 43


# When there is no result


def test_a_refused_file_says_it_cannot_be_converted(client: TestClient) -> None:
    link = upload(client, legacy_doc(), name="เก่า.doc")

    assert ended_state(client, link) == "refused"
    assert "แปลงไฟล์นี้ไม่ได้" in client.get(link).text


def test_a_conversion_that_fails_says_so() -> None:
    with browser(FakeSandbox(FailingEngine)) as client:
        link = upload(client, mixed_pdf())

        assert ended_state(client, link) == "failed"
        assert "การแปลงล้มเหลว" in client.get(link).text


SUMMARY = b'{"event": "summary", "pages": []}'


@pytest.mark.parametrize(
    ("lines", "ended"),
    [
        pytest.param([b"Paddle says hello"], Ended(0, b"markdown 0\n"), id="a line that is not JSON"),
        pytest.param(
            [b'{"event": "opened", "source_type": "pdf", "pages": 1, "text": "x"}', SUMMARY],
            Ended(0, b"markdown 0\n"),
            id="an event with a field of its own",
        ),
        pytest.param(
            [
                '{"event": "summary", "pages": [{"number": 1, "kind": "ocr", "engine": "ผู้รับทุนตกลง",'
                ' "untrusted_text_layer": false, "placeholders": [], "uncertain": 0, "tables": 0, "incomplete_tables": 0}]}'.encode()
            ],
            Ended(0, b"markdown 0\n"),
            id="an engine name that is not a name",
        ),
        pytest.param([SUMMARY], Ended(0, b"markdown 99\nshort"), id="a part shorter than it says"),
        pytest.param([SUMMARY], Ended(0, b"docx 0\n"), id="no Markdown"),
        pytest.param([SUMMARY], Ended(1, b"markdown 0\n"), id="a crash after the summary"),
        pytest.param([SUMMARY], None, id="no ending at all"),
        pytest.param([b'{"event": "refusal", "kind": "TooLarge"}'], Ended(4, b""), id="a size refusal without its size"),
        pytest.param(
            [b'{"event": "refusal", "kind": "DamagedFile", "size": 1}'],
            Ended(8, b""),
            id="a refusal with a size it does not have",
        ),
        pytest.param(
            [b'{"event": "refusal", "kind": "TooLarge", "unit": "pages", "size": 1' + b"0" * 400 + b', "limit": 150}'],
            Ended(4, b""),
            id="a size too long to show",
        ),
        pytest.param(
            [b'{"event": "refusal", "kind": "TooLarge", "unit": "pages", "size": 151, "limit": 100}'],
            Ended(4, b""),
            id="a limit that is not the service's",
        ),
        pytest.param(
            [b'{"event": "refusal", "kind": "TooLarge", "unit": "pages", "size": 20, "limit": 150}'],
            Ended(4, b""),
            id="a size within the limit",
        ),
        pytest.param(
            [b'{"event": "summary", "pages": [], "images_lowered_to": "100"}'],
            Ended(0, b"markdown 0\n"),
            id="a resolution that is not a number",
        ),
        pytest.param(
            [b'{"event": "summary", "pages": [], "images_lowered_to": 150}'],
            Ended(0, b"markdown 0\n"),
            id="a resolution not lowered",
        ),
        pytest.param(
            [b'{"event": "summary", "pages": [], "images_lowered_to": 0}'],
            Ended(0, b"markdown 0\n"),
            id="a resolution of nothing",
        ),
        pytest.param(
            [b'{"event": "progress", "stage": "images", "current": 1, "total": 1}', SUMMARY],
            Ended(0, b"markdown 0\n"),
            id="pages kept as images when that was not asked for",
        ),
    ],
)
def test_what_a_sandbox_sends_is_checked_and_anything_off_fails(lines: list[bytes], ended: Ended | None) -> None:
    with browser(ScriptedSandbox(lines, ended)) as client:
        link = upload(client, pdf(["หน้าแรก"]))

        assert ended_state(client, link) == "failed"


def test_a_summary_of_images_made_less_sharp_finishes_and_the_page_says_how_sharp() -> None:
    summary = b'{"event": "summary", "pages": [], "images_lowered_to": 100}'

    with browser(ScriptedSandbox([summary], Ended(0, b"markdown 0\n"))) as client:
        link = upload(client, pdf(["หน้าแรก"]))

        assert ended_state(client, link) == "finished"
        assert "ภาพใน DOCX ลดความละเอียดเหลือ 100 dpi ให้ผลลัพธ์ไม่เกิน 50 MB" in client.get(link).text
