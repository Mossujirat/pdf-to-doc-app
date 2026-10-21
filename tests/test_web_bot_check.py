"""The bot check: an upload is taken only once Cloudflare Turnstile has verified its token, and
refused whenever it cannot be verified. A stand-in answers for Cloudflare."""

import logging
from dataclasses import replace

import httpx
import httpx2  # the test client's HTTP library
import pytest
from fake_cloudflare import HOSTNAME, TOKEN, FakeCloudflare, failing, passing, unreachable
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from pdf_builder import pdf
from web_browser import SETTINGS, browser, send

from pdf_to_doc.web.app import create_app
from pdf_to_doc.web.bot_check import Misconfigured
from pdf_to_doc.web.settings import Settings

REFUSED = "ตรวจสอบไม่ได้ว่าไฟล์นี้ส่งมาจากผู้ใช้จริง"


def sent_with(cloudflare: FakeCloudflare, settings: Settings = SETTINGS) -> httpx2.Response:
    with browser(FakeSandbox(), settings, cloudflare=cloudflare) as client:
        return send(client, pdf(["หน้าแรก"]))


def test_an_upload_whose_token_cloudflare_verifies_is_taken() -> None:
    cloudflare = passing()

    response = sent_with(cloudflare)

    assert response.status_code == 303
    assert cloudflare.asked == [{"secret": "secret-key", "response": TOKEN}]


@pytest.mark.parametrize(
    ("cloudflare", "settings"),
    [
        pytest.param(failing(), SETTINGS, id="verification fails"),
        pytest.param(passing(), replace(SETTINGS, turnstile_secret_key=None), id="no secret key"),
        pytest.param(unreachable(), SETTINGS, id="Cloudflare cannot be reached"),
        pytest.param(unreachable(httpx.ReadTimeout), SETTINGS, id="Cloudflare does not answer in time"),
        pytest.param(passing(hostname="elsewhere.example"), SETTINGS, id="another site's token"),
        pytest.param(passing(action="login"), SETTINGS, id="another action's token"),
        pytest.param(FakeCloudflare({"unexpected": "answer"}), SETTINGS, id="an answer that says nothing"),
        pytest.param(
            FakeCloudflare({"success": True, "action": "upload"}),
            replace(SETTINGS, hostname=None),
            id="no hostname to confirm",
        ),
    ],
)
def test_an_upload_is_refused_whenever_its_token_cannot_be_verified(
    cloudflare: FakeCloudflare, settings: Settings
) -> None:
    response = sent_with(cloudflare, settings)

    assert response.status_code == 403
    assert REFUSED in response.text
    assert "set-cookie" not in response.headers  # nothing of the upload is kept, not even a conversion


@pytest.mark.parametrize(
    ("cloudflare", "logged"),
    [
        pytest.param(failing(), "failed", id="bots"),
        pytest.param(unreachable(), "unreachable", id="an outage"),
    ],
)
def test_a_refusal_is_logged_by_why_and_never_with_the_token(
    cloudflare: FakeCloudflare, logged: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="pdf_to_doc"):
        sent_with(cloudflare)

    assert f"upload refused by the bot check: {logged}" in caplog.text
    assert TOKEN not in caplog.text


def test_an_upload_without_a_token_is_refused_without_asking_cloudflare() -> None:
    cloudflare = passing()
    with browser(FakeSandbox(), cloudflare=cloudflare) as client:
        response = client.post("/conversions", files={"file": ("a.pdf", pdf(["หน้าแรก"]))}, follow_redirects=False)

    assert response.status_code == 403
    assert cloudflare.asked == []


def test_the_home_page_carries_the_widget_for_the_upload() -> None:
    with browser(FakeSandbox()) as client:
        page = client.get("/").text

    assert '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>' in page
    assert 'class="cf-turnstile" data-sitekey="site-key" data-action="upload"' in page


# Test mode


def test_test_mode_uses_cloudflares_test_keys() -> None:
    # As Cloudflare answered for its passing test secret on 2026-10-21: a hostname of its own, no action.
    cloudflare = FakeCloudflare({"success": True, "hostname": "example.com", "error-codes": []})
    test_mode = Settings(bot_check_test_mode=True)
    with browser(FakeSandbox(), test_mode, cloudflare=cloudflare) as client:
        page = client.get("/").text
        response = send(client, pdf(["หน้าแรก"]))

    assert 'data-sitekey="1x00000000000000000000BB"' in page  # invisible, and always passes
    assert response.status_code == 303
    assert cloudflare.asked[0]["secret"] == "1x0000000000000000000000000000000AA"


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param(Settings(production=True, bot_check_test_mode=True, hostname=HOSTNAME), id="test mode"),
        pytest.param(
            Settings(
                production=True,
                turnstile_site_key="1x00000000000000000000BB",
                turnstile_secret_key="1x0000000000000000000000000000000AA",
                hostname=HOSTNAME,
            ),
            id="test keys",
        ),
        pytest.param(replace(SETTINGS, production=True, turnstile_secret_key=None), id="no secret key"),
        pytest.param(replace(SETTINGS, production=True, turnstile_site_key=None), id="no site key"),
        pytest.param(replace(SETTINGS, production=True, hostname=None), id="no hostname"),
    ],
)
def test_production_refuses_to_start_without_real_keys(settings: Settings) -> None:
    with pytest.raises(Misconfigured):
        create_app(FakeSandbox(), settings)


def test_production_starts_with_real_keys() -> None:
    with TestClient(create_app(FakeSandbox(), replace(SETTINGS, production=True))) as client:
        assert 'data-sitekey="site-key"' in client.get("/").text
