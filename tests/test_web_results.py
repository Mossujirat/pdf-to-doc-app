"""Results are kept for 10 minutes after their conversion ends, or until the visitor deletes
them, and then forgotten. A fake clock stands in for the time passing."""

from collections.abc import Callable, Iterator

import docx_reader
import markdown_reader
import pytest
from fake_clock import FakeClock
from fake_ocr import FailingEngine
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from held_sandbox import HeldSandbox
from pdf_builder import Scan, pdf
from web_browser import as_browser, browser, cancel, ended_state, upload, wait_until
from word_builder import legacy_doc

TEN_MINUTES = 10 * 60


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(clock: FakeClock) -> Iterator[TestClient]:
    with browser(FakeSandbox(), clock=clock) as client:
        yield client


def finished(client: TestClient) -> str:
    link = upload(client, pdf(["หน้าแรก"], ["หน้าที่สอง"]))
    assert ended_state(client, link) == "finished"
    return link


def is_gone(client: TestClient, address: str) -> bool:
    response = client.get(address)
    return response.status_code == 404 and "อาจหมดเวลาเก็บแล้ว ถูกลบ หรือหายไปเมื่อระบบเริ่มทำงานใหม่" in response.text


def forgotten_at_ten_minutes(client: TestClient, clock: FakeClock, link: str) -> None:
    clock.advance(TEN_MINUTES - 1)
    assert not is_gone(client, link)
    clock.advance(1)
    assert is_gone(client, link)


def test_outputs_download_until_10_minutes_have_passed_and_are_gone_after(client: TestClient, clock: FakeClock) -> None:
    link = finished(client)

    clock.advance(TEN_MINUTES - 1)
    assert markdown_reader.page_texts(client.get(f"{link}/markdown").text) == ["หน้าแรก", "หน้าที่สอง"]
    clock.advance(1)

    for address in (link, f"{link}/state", f"{link}/markdown", f"{link}/docx"):
        assert is_gone(client, address)


def test_the_result_page_shows_the_time_left(client: TestClient, clock: FakeClock) -> None:
    link = finished(client)

    assert "จะถูกลบภายใน 10 นาที" in client.get(link).text
    clock.advance(9 * 60 + 1)
    assert "จะถูกลบภายใน 1 นาที" in client.get(link).text


def test_a_download_can_be_repeated(client: TestClient, clock: FakeClock) -> None:
    link = finished(client)

    first = client.get(f"{link}/docx").content
    clock.advance(5 * 60)

    assert client.get(f"{link}/docx").content == first
    assert docx_reader.page_texts(first) == ["หน้าแรก", "หน้าที่สอง"]


def test_delete_now_drops_the_outputs_at_once(client: TestClient) -> None:
    link = finished(client)
    assert f'action="{link}/delete"' in client.get(link).text  # the result page's button

    response = client.post(f"{link}/delete")

    assert "ลบไฟล์ผลลัพธ์แล้ว" in response.text
    for address in (link, f"{link}/markdown", f"{link}/docx"):
        assert is_gone(client, address)


def test_a_link_from_before_a_restart_shows_the_expired_page(client: TestClient) -> None:
    link = finished(client)
    token = client.cookies["browser"]

    with browser(FakeSandbox()) as restarted:  # a fresh app, standing in for the service restarted
        assert is_gone(as_browser(restarted, token), link)


def test_a_link_that_never_existed_shows_the_expired_page(client: TestClient) -> None:
    assert is_gone(client, "/conversions/never-existed")


@pytest.mark.parametrize(
    ("source", "ended"),
    [
        pytest.param(legacy_doc, "refused", id="refused"),
        pytest.param(lambda: pdf(Scan(["หน้าสแกน"], dpi=50)), "failed", id="failed"),
    ],
)
def test_conversions_without_a_result_are_forgotten_after_10_minutes_too(
    source: Callable[[], bytes], ended: str
) -> None:
    clock = FakeClock()
    with browser(FakeSandbox(FailingEngine), clock=clock) as client:
        link = upload(client, source())

        assert ended_state(client, link) == ended
        forgotten_at_ten_minutes(client, clock, link)


def test_a_cancelled_conversion_is_forgotten_after_10_minutes() -> None:
    clock, held = FakeClock(), HeldSandbox()
    with browser(held, clock=clock) as client:
        link = upload(client, pdf(["หน้าแรก"]))
        wait_until(lambda: len(held.started) == 1, "the conversion to start")

        cancel(client, link)

        forgotten_at_ten_minutes(client, clock, link)
