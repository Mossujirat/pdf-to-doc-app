"""A browser on the web service, for its tests: uploads, links and states, as a browser sees them."""

import secrets
import time
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from pdf_to_doc.web.app import COOKIE, create_app
from pdf_to_doc.web.conversions import Clock
from pdf_to_doc.web.sandboxes import Sandbox
from pdf_to_doc.web.settings import Settings


def browser(sandbox: Sandbox, settings: Settings = Settings(), clock: Clock = time.monotonic) -> TestClient:
    """A browser on the service, over HTTPS as in production."""
    return TestClient(create_app(sandbox, settings, clock), base_url="https://testserver")


def browser_token() -> str:
    """The token of a browser of its own, as the service would have set in its cookie."""
    return secrets.token_urlsafe(32)


def as_browser(client: TestClient, token: str) -> TestClient:
    """The client, from now on as the browser whose cookie holds `token`: several browsers on one
    service and one event loop. Call it again before each request as another browser."""
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    return client


def upload(client: TestClient, source: bytes, name: str = "สัญญา.pdf") -> str:
    """Send a file from the home page's form, and return the conversion's link."""
    response = client.post("/conversions", files={"file": (name, source)}, follow_redirects=False)
    assert response.status_code == 303, response.text
    return str(response.headers["location"])


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
