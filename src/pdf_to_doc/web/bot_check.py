"""The bot check: Cloudflare Turnstile's token, verified with Cloudflare before an upload is taken.

It fails closed. Whenever a token cannot be verified, because it fails, there is no key, Cloudflare
cannot be reached or does not answer in time, or the answer is for another site or action, the
upload is refused. Only the token goes to Cloudflare: never the file, and not the visitor's address.
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Literal, Self

import httpx

from pdf_to_doc.web.settings import Misconfigured, Settings

CLOUDFLARE = "https://challenges.cloudflare.com"  # where the widget's script and frame come from
SCRIPT = f"{CLOUDFLARE}/turnstile/v0/api.js"
TOKEN_FIELD = "cf-turnstile-response"  # the form field the widget puts its token in
ACTION = "upload"
_SITEVERIFY = f"{CLOUDFLARE}/turnstile/v0/siteverify"
_TIMEOUT = 10  # seconds in all, as Cloudflare's own examples wait
_CONNECTION_TRIES = 3  # within that time
_BETWEEN_TRIES = 0.5  # seconds
_LONGEST_TOKEN = 2048
# Cloudflare's test keys: an invisible widget, and a secret, that always pass. Asked on 2026-10-21,
# the secret passed any token, and answered with Cloudflare's own hostname and no action.
TEST_SITE_KEY = "1x00000000000000000000BB"
TEST_SECRET_KEY = "1x0000000000000000000000000000000AA"
_TEST_KEY = re.compile("[123]x0+[A-F]{2}")  # the shape of every test key, site or secret

# How a check came out, for the logs; only "passed" lets the upload in.
Verdict = Literal["passed", "not configured", "no token", "failed", "unreachable", "another site"]


@dataclass(frozen=True)
class BotCheck:
    site_key: str | None  # for the widget on the page
    secret_key: str | None
    hostname: str | None
    test_mode: bool  # Cloudflare's test keys, which confirm no hostname or action of ours
    cloudflare: httpx.AsyncBaseTransport | None = None  # stands in for Cloudflare in tests

    @classmethod
    def from_settings(cls, settings: Settings, cloudflare: httpx.AsyncBaseTransport | None = None) -> Self:
        """The bot check the settings ask for. The public service refuses test mode, test keys,
        and a missing key or hostname."""
        if settings.bot_check_test_mode:
            check = cls(TEST_SITE_KEY, TEST_SECRET_KEY, None, True, cloudflare)
        else:
            check = cls(
                settings.turnstile_site_key, settings.turnstile_secret_key, settings.hostname, False, cloudflare
            )
        real_keys = _real(check.site_key) and _real(check.secret_key)
        if settings.production and (check.test_mode or not check.hostname or not real_keys):
            raise Misconfigured("the public service needs the bot check's own keys and its hostname")
        return check

    async def check(self, token: str | None) -> Verdict:
        """Whether Cloudflare verifies the token for this site's upload, and if not, why not."""
        if not self.secret_key or not (self.test_mode or self.hostname):
            return "not configured"
        if not token or len(token) > _LONGEST_TOKEN:
            return "no token"
        try:
            async with asyncio.timeout(_TIMEOUT), httpx.AsyncClient(transport=self.cloudflare) as client:
                response = await _verify(client, self.secret_key, token)
            answer = response.json()
        except (httpx.HTTPError, TimeoutError, ValueError):
            return "unreachable"
        if not isinstance(answer, dict) or answer.get("success") is not True:
            return "failed"
        if not self.test_mode and (answer.get("hostname") != self.hostname or answer.get("action") != ACTION):
            return "another site"
        return "passed"


async def _verify(client: httpx.AsyncClient, secret_key: str, token: str) -> httpx.Response:
    """Ask Cloudflare to verify the token. A connection that never reached Cloudflare is tried
    again, as gmt's network drops one now and then (staging, 2026-10-22). A request that may have
    reached it is not, since each token is good for one verification."""
    for attempt in range(1, _CONNECTION_TRIES + 1):
        try:
            return await client.post(_SITEVERIFY, data={"secret": secret_key, "response": token})
        except (httpx.ConnectError, httpx.ConnectTimeout):
            if attempt == _CONNECTION_TRIES:
                raise
            await asyncio.sleep(_BETWEEN_TRIES)
    raise AssertionError("unreachable")  # the loop returns or raises


def _real(key: str | None) -> bool:
    return key is not None and not _TEST_KEY.fullmatch(key)
