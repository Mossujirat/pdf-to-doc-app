"""The privacy page and the footer on every page: who runs the service and how to reach them,
how long what a visitor sends is kept, and a link to the source code the server runs (AGPL)."""

from dataclasses import replace

import pytest
from fake_sandbox import FakeSandbox
from scripted_sandbox import ScriptedSandbox
from web_browser import COMMIT, PRODUCTION, SETTINGS, browser, shown_text

from pdf_to_doc.web.app import create_app
from pdf_to_doc.web.settings import Misconfigured, Settings

REPOSITORY = "https://github.com/Mossujirat/pdf-to-doc-app"


def test_the_privacy_page_names_the_operator_the_contact_and_how_long_things_are_kept() -> None:
    with browser(ScriptedSandbox([], None), replace(SETTINGS, keep_for=300, pages_per_day=40)) as client:
        response = client.get("/privacy")
    text = shown_text(response.text)

    assert response.status_code == 200
    assert "Sujirat Attawibulkul" in text  # who runs it, as an individual
    assert "sujirat.attawibulkul@gmail.com" in text  # the contact for personal data
    assert "5 นาที" in text  # how long results are kept
    assert "40 หน้า" in text  # the daily allowance an address is held in memory for


def test_every_page_links_to_the_source_code_the_server_runs_the_privacy_page_and_the_issues() -> None:
    with browser(ScriptedSandbox([], None), replace(SETTINGS, build_commit=COMMIT)) as client:
        for path in ("/", "/privacy", "/conversions/unknown"):
            footer = client.get(path).text.split("<footer")[1]
            assert 'href="/source-code"' in footer and 'href="/privacy"' in footer
            assert f'href="{REPOSITORY}/issues"' in footer
        source_code = client.get("/source-code", follow_redirects=False)

    assert source_code.headers["location"] == f"{REPOSITORY}/tree/{COMMIT}"


def test_a_build_that_names_no_commit_links_to_the_repository_itself() -> None:
    with browser(ScriptedSandbox([], None)) as client:
        source_code = client.get("/source-code", follow_redirects=False)

    assert source_code.headers["location"] == REPOSITORY


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param(replace(PRODUCTION, build_commit=None), id="no commit, so no source code to offer"),
        pytest.param(replace(SETTINGS, build_commit="main; rm -rf /"), id="a commit that is no commit's hash"),
    ],
)
def test_the_service_refuses_to_start_without_a_commit_it_can_link_to(settings: Settings) -> None:
    with pytest.raises(Misconfigured):
        create_app(FakeSandbox(), settings)
