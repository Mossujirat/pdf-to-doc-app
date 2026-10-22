"""A stand-in for Cloudflare's Turnstile verification, for the web app's tests: it answers as the
test says, or cannot be reached, and remembers what it was asked."""

from typing import Any
from urllib.parse import parse_qsl

import httpx

HOSTNAME = "testserver"  # where the test client's pages are served
TOKEN = "token-from-the-widget"  # what the widget put in the form


class FakeCloudflare(httpx.MockTransport):
    def __init__(
        self,
        answer: dict[str, Any] | None = None,
        *,
        fails: type[httpx.TransportError] | None = None,
        unreachable_at_first: int = 0,
    ) -> None:
        """`answer` is the verification's JSON; `fails` is the error reaching it raises instead.
        The first `unreachable_at_first` connections never reach it, as a network drops one."""
        self.asked: list[dict[str, str]] = []  # each verification's form fields, as it reached Cloudflare
        self.connections = 0

        def verify(request: httpx.Request) -> httpx.Response:
            self.connections += 1
            if self.connections <= unreachable_at_first:
                raise httpx.ConnectError("the connection was dropped", request=request)
            self.asked.append(dict(parse_qsl(request.content.decode())))
            if fails is not None:
                raise fails("Cloudflare cannot be reached", request=request)
            return httpx.Response(200, json=answer)

        super().__init__(verify)


def passing(*, unreachable_at_first: int = 0, **different: Any) -> FakeCloudflare:
    """Cloudflare passing the token for this site's upload, unless `different` says otherwise."""
    return FakeCloudflare(
        {"success": True, "hostname": HOSTNAME, "action": "upload", "error-codes": [], **different},
        unreachable_at_first=unreachable_at_first,
    )


def failing() -> FakeCloudflare:
    return FakeCloudflare({"success": False, "error-codes": ["invalid-input-response"]})


def unreachable(error: type[httpx.TransportError] = httpx.ConnectError) -> FakeCloudflare:
    """Cloudflare out of reach, or, with `httpx.ReadTimeout`, not answering in time."""
    return FakeCloudflare(fails=error)
