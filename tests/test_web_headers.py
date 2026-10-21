"""The headers every page and download carries, the check on where a request that changes
something came from, and the health address."""

from collections.abc import Iterator

import httpx2  # the test client's HTTP library
import pytest
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from held_sandbox import HeldSandbox
from pdf_builder import pdf
from web_browser import browser, ended_state, send, upload, wait_until

ELSEWHERE = "https://attacker.example"
# Turnstile's script and frame come from Cloudflare (developers.cloudflare.com, read 2026-10-21).
CSP = (
    "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; "
    "frame-src https://challenges.cloudflare.com; object-src 'none'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with browser(FakeSandbox()) as client:
        yield client


def finished(client: TestClient) -> str:
    link = upload(client, pdf(["หน้าแรก"]))
    assert ended_state(client, link) == "finished"
    return link


def assert_private(response: httpx2.Response) -> None:
    """What every conversion page and download sends: it is neither cached nor indexed."""
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex"


def test_every_page_allows_this_site_alone_and_cloudflares_bot_check(client: TestClient) -> None:
    link = finished(client)

    for page in ["/", link, "/conversions/unknown", "/health"]:
        response = client.get(page)
        assert response.headers["content-security-policy"] == CSP, page
        assert response.headers["x-content-type-options"] == "nosniff", page
        assert response.headers["referrer-policy"] == "same-origin", page


def test_a_conversions_page_and_its_state_are_neither_cached_nor_indexed(client: TestClient) -> None:
    link = finished(client)

    for address in [link, f"{link}/state", "/conversions/unknown"]:
        assert_private(client.get(address))


def test_a_download_tells_no_one_where_it_came_from_and_is_neither_cached_nor_indexed(client: TestClient) -> None:
    link = finished(client)

    for output in ["markdown", "docx"]:
        response = client.get(f"{link}/{output}")
        assert response.status_code == 200
        assert response.headers["referrer-policy"] == "no-referrer"
        assert_private(response)


def test_the_answer_to_an_upload_is_neither_cached_nor_indexed(client: TestClient) -> None:
    taken = send(client, pdf(["หน้าแรก"]))
    refused = send(client, pdf(["หน้าแรก"]), headers=[("origin", ELSEWHERE)])

    for response in [taken, refused]:
        assert_private(response)


def test_the_home_page_may_be_cached_and_indexed(client: TestClient) -> None:
    response = client.get("/")

    assert "cache-control" not in response.headers
    assert "x-robots-tag" not in response.headers


@pytest.mark.parametrize("origin", [ELSEWHERE, "null", None], ids=["another site", "no origin it will name", "none"])
def test_an_upload_from_anywhere_but_this_site_is_refused(client: TestClient, origin: str | None) -> None:
    client.headers.pop("origin")
    headers = [] if origin is None else [("origin", origin)]

    response = send(client, pdf(["หน้าแรก"]), headers=headers)

    assert response.status_code == 403
    assert "set-cookie" not in response.headers  # no conversion was made


def test_a_cancel_from_another_site_is_refused() -> None:
    held = HeldSandbox()
    with browser(held) as client:
        link = upload(client, pdf(["หน้าแรก"]))
        wait_until(lambda: len(held.started) == 1, "the conversion to start")

        response = client.post(f"{link}/cancel", headers={"origin": ELSEWHERE}, follow_redirects=False)

        assert response.status_code == 403
        assert client.get(f"{link}/state").json()["ongoing"]
        held.started[0].end()
        assert ended_state(client, link) == "finished"


def test_a_delete_from_another_site_is_refused(client: TestClient) -> None:
    link = finished(client)

    response = client.post(f"{link}/delete", headers={"origin": ELSEWHERE})

    assert response.status_code == 403
    assert client.get(f"{link}/markdown").status_code == 200


def test_the_health_address_says_only_that_the_service_is_up(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.text == "ok"
