"""A browser on the web service, for its tests: uploads, links and states, as a browser sees them."""

import secrets
import time
from collections.abc import Callable
from typing import Any

import httpx
import httpx2  # the test client's HTTP library
from fake_clock import FakeClock
from fake_cloudflare import HOSTNAME, TOKEN, passing
from fastapi.testclient import TestClient

from pdf_to_doc.web.app import COOKIE, create_app
from pdf_to_doc.web.bot_check import TOKEN_FIELD
from pdf_to_doc.web.sandboxes import Sandbox
from pdf_to_doc.web.settings import Settings
from pdf_to_doc.web.statistics import Statistics

# The service as the tests run it: with its bot check's keys, for this test site.
SETTINGS = Settings(turnstile_site_key="site-key", turnstile_secret_key="secret-key", hostname=HOSTNAME)
SITE = f"https://{HOSTNAME}"  # the site's origin, as a browser names it


def browser(
    sandbox: Sandbox,
    settings: Settings = SETTINGS,
    clock: FakeClock | None = None,
    cloudflare: httpx.AsyncBaseTransport | None = None,
    address: str = "203.0.113.10",
    statistics: Statistics | None = None,
) -> TestClient:
    """A browser on the service, over HTTPS as in production, connecting from `address`. As a
    browser does, it names the site's own origin on every request from one of its pages.
    Cloudflare passes every bot check, unless `cloudflare` stands in for it otherwise.
    `clock` stands in for the time, monotonic and on the wall. `statistics` count what it does."""
    cloudflare = cloudflare or passing()
    if clock is None:
        app = create_app(sandbox, settings, cloudflare=cloudflare, statistics=statistics)
    else:
        app = create_app(sandbox, settings, clock, clock.wall, cloudflare=cloudflare, statistics=statistics)
    return TestClient(app, base_url=SITE, client=(address, 50000), headers={"origin": SITE})


def browser_token() -> str:
    """The token of a browser of its own, as the service would have set in its cookie."""
    return secrets.token_urlsafe(32)


def as_browser(client: TestClient, token: str) -> TestClient:
    """The client, from now on as the browser whose cookie holds `token`: several browsers on one
    service and one event loop. Call it again before each request as another browser."""
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    return client


def send(
    client: TestClient, source: bytes, name: str = "สัญญา.pdf", headers: list[tuple[str, str]] | None = None
) -> httpx2.Response:
    """Send a file from the home page's form, with the token its bot check put there, and any
    `headers` of the request's own."""
    return client.post(
        "/conversions",
        data={TOKEN_FIELD: TOKEN},
        files={"file": (name, source)},
        headers=headers,
        follow_redirects=False,
    )


def upload(
    client: TestClient, source: bytes, name: str = "สัญญา.pdf", headers: list[tuple[str, str]] | None = None
) -> str:
    """Send a file from the home page's form, and return the conversion's link."""
    response = send(client, source, name, headers)
    assert response.status_code == 303, response.text
    return str(response.headers["location"])


def converted(client: TestClient, source: bytes, headers: list[tuple[str, str]] | None = None) -> tuple[str, str]:
    """Send a file, wait for its conversion to end, and return how it ended and what its page says."""
    link = upload(client, source, headers=headers)
    return ended_state(client, link), client.get(link).text


def cancel(client: TestClient, link: str) -> None:
    """Press the conversion page's cancel button."""
    response = client.post(f"{link}/cancel", follow_redirects=False)
    assert response.status_code == 303


def title(client: TestClient, link: str) -> str:
    """The title of the conversion's page, as the browser's tab shows it."""
    return client.get(link).text.split("<title>")[1].split("</title>")[0]


def wait_until(done: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + 30
    while not done():
        assert time.monotonic() < deadline, f"waited too long for {what}"
        time.sleep(0.02)


def wait_for_state(client: TestClient, link: str, done: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    """Ask for the conversion's state as its page does, until `done` holds."""
    state: dict[str, Any] = {}

    def asked() -> bool:
        state.update(client.get(f"{link}/state").json())
        return done(state)

    wait_until(asked, f"the state of {link}, last {state}")
    return state


def ended_state(client: TestClient, link: str) -> str:
    return str(wait_for_state(client, link, lambda state: not state["ongoing"])["state"])
