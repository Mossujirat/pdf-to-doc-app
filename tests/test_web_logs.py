"""The web app's log could be published without harm: it holds nothing of a document, its file
name, a visitor's address or a conversion's link. It says only that the service started and
stopped, what was refused and why, and what failed, by the error's type and where."""

import logging
from collections.abc import Callable

import pytest
from fake_ocr import FailingEngine, FakeEngine
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from fragments import leaked
from pdf_builder import Scan, pdf, protected
from web_browser import SITE, browser, ended_state, upload

from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.web.app import create_app

TEXT_PAGE = ["สัญญาให้ทุนวิจัยเลขที่ ๐๔๑๗/๒๕๖๙ ระหว่างกองทุน", "ส่งเสริมการวิจัยกับบริษัทสยามอนาไลติกาจำกัด"]
SCAN = ["ผู้รับทุนตกลงดำเนินงานตามแผนที่กำหนดไว้ในสัญญาฉบับนี้ทุกประการ"]
NAME = "สัญญาทุนวิจัย-สยามอนาไลติกา.pdf"
ADDRESS = "198.51.100.23"


def app_log(caplog: pytest.LogCaptureFixture) -> str:
    """What the service logged: not the test client, which logs each address it asks for."""
    return "\n".join(record.getMessage() for record in caplog.records if not record.name.startswith("httpx2"))


@pytest.mark.parametrize(
    ("source", "engine", "ending", "said"),
    [
        pytest.param(
            lambda: pdf(TEXT_PAGE, Scan(SCAN, dpi=50)), lambda: FakeEngine(SCAN), "finished", [], id="a full conversion"
        ),
        pytest.param(
            lambda: protected(pdf(TEXT_PAGE), allow_copy=False),
            FakeEngine,
            "refused",
            ["refused: CopyRestricted"],
            id="a refusal",
        ),
        pytest.param(
            lambda: pdf(TEXT_PAGE, Scan(SCAN, dpi=50)),
            lambda: FailingEngine(f"cannot read {SCAN[0]}"),
            "failed",
            ["conversion failed in the sandbox: RuntimeError"],
            id="a failure",
        ),
    ],
)
def test_the_log_holds_nothing_of_the_document_its_name_the_address_or_the_link(
    caplog: pytest.LogCaptureFixture,
    source: Callable[[], bytes],
    engine: Callable[[], OcrEngine],
    ending: str,
    said: list[str],
) -> None:
    with caplog.at_level(logging.DEBUG), browser(FakeSandbox(engine), address=ADDRESS) as client:
        link = upload(client, source(), NAME)
        assert ended_state(client, link) == ending
        client.get(link)

    log = app_log(caplog)
    assert leaked([*TEXT_PAGE, *SCAN], log) == []
    assert NAME not in log
    assert NAME.removesuffix(".pdf") not in log
    assert ADDRESS not in log
    assert link.rsplit("/", 1)[-1] not in log
    for line in ["started", *said, "stopped"]:
        assert line in log


def test_an_unexpected_error_is_logged_by_its_type_and_route_alone(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(FakeSandbox())

    @app.get("/broken/{identifier}")
    async def broken(identifier: str) -> None:
        raise RuntimeError(f"could not show {TEXT_PAGE[0]}")

    with caplog.at_level(logging.DEBUG), TestClient(app, base_url=SITE, raise_server_exceptions=False) as client:
        response = client.get("/broken/a-link-of-its-own")

    log = app_log(caplog)
    assert response.status_code == 500
    assert "failed: RuntimeError at /broken/{identifier}" in log
    assert leaked(TEXT_PAGE, log) == []
    assert "a-link-of-its-own" not in log
