"""The operator's counters: how the service is used, since it started and for today. They are
served by an app of their own, for a listener on the server's loopback address, and never by
the public app."""

from dataclasses import replace
from typing import Any

from fake_clock import FakeClock
from fake_cloudflare import failing
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from held_sandbox import HeldSandbox
from pdf_builder import pdf
from scripted_sandbox import ScriptedSandbox
from web_browser import SETTINGS, as_browser, browser, browser_token, converted, ended_state, send, upload, wait_until
from word_builder import legacy_doc

from pdf_to_doc.web.app import statistics_app
from pdf_to_doc.web.sandboxes import Ended, Usage
from pdf_to_doc.web.statistics import Statistics

SOURCE = pdf(["หน้าแรก"])
OPENED = b'{"event": "opened", "source_type": "pdf", "pages": 1}'


def counted(statistics: Statistics) -> dict[str, Any]:
    """What the operator reads on the statistics listener."""
    with TestClient(statistics_app(statistics)) as client:
        response = client.get("/")
    assert response.status_code == 200
    return dict(response.json())


def test_conversions_are_counted_by_how_they_ended_with_their_pages_refusals_and_sandbox_use() -> None:
    clock = FakeClock()
    statistics = Statistics(clock.wall)
    failing_sandbox = ScriptedSandbox([OPENED, b'{"event": "failure", "error": "MemoryError"}'], Ended(10, b""))
    used = Usage(peak_memory=1_300_000_000, cpu_time=1700.0)
    timing_out = ScriptedSandbox([OPENED], Ended(137, b"", timed_out=True, usage=used))

    with browser(FakeSandbox(), clock=clock, statistics=statistics) as client:
        converted(as_browser(client, browser_token()), pdf(["หน้าแรก"], ["หน้าที่สอง"]))
        converted(as_browser(client, browser_token()), legacy_doc())
    for sandbox in [failing_sandbox, timing_out]:
        with browser(sandbox, clock=clock, statistics=statistics) as client:
            converted(client, SOURCE)
    with browser(FakeSandbox(), clock=clock, statistics=statistics, cloudflare=failing()) as client:
        send(client, SOURCE)
        send(client, SOURCE, headers=[("origin", "https://attacker.example")])

    since_start = counted(statistics)["since_start"]
    assert since_start["conversions"] == {"finished": 1, "refused": 1, "failed": 1, "timed_out": 1}
    assert since_start["pages"] == {"text": 2}
    assert since_start["refusals"] == {"UnsupportedFormat": 1, "another site": 1}
    assert since_start["bot_check_failures"] == {"failed": 1}
    assert since_start["peak_sandbox_memory"] == 1_300_000_000
    assert since_start["longest_sandbox_cpu_time"] == 1700.0


def test_how_long_conversions_ran_and_waited_and_the_longest_queue_are_counted() -> None:
    clock = FakeClock()
    statistics = Statistics(clock.wall)
    held = HeldSandbox()
    with browser(held, replace(SETTINGS, max_running=1), clock, statistics=statistics) as client:
        upload(as_browser(client, browser_token()), SOURCE)
        wait_until(lambda: len(held.started) == 1, "the first conversion to start")
        second = browser_token()
        link = upload(as_browser(client, second), SOURCE)  # it waits for the first
        clock.advance(10)
        held.started[0].end()
        wait_until(lambda: len(held.started) == 2, "the second conversion to start")
        clock.advance(5)
        held.started[1].end()
        assert ended_state(as_browser(client, second), link) == "finished"

    report = counted(statistics)
    assert report["since_start"]["run_times"] == {"count": 2, "total": 15.0, "longest": 10.0}
    assert report["since_start"]["queue_waits"] == {"count": 2, "total": 10.0, "longest": 10.0}
    assert report["since_start"]["longest_queue"] == 1
    assert report["queue"] == {"waiting": 0, "running": 0}


def test_todays_counts_start_again_at_midnight_in_bangkok_and_those_since_the_start_go_on() -> None:
    clock = FakeClock()  # noon in Bangkok
    statistics = Statistics(clock.wall)
    with browser(FakeSandbox(), clock=clock, statistics=statistics) as client:
        converted(as_browser(client, browser_token()), SOURCE)
        clock.advance(12 * 60 * 60)
        converted(as_browser(client, browser_token()), SOURCE)

    report = counted(statistics)
    assert report["day"] == "2026-10-22"
    assert report["today"]["conversions"] == {"finished": 1}
    assert report["since_start"]["conversions"] == {"finished": 2}


def test_the_public_app_does_not_serve_the_counters() -> None:
    with browser(FakeSandbox()) as client:
        for address in ["/statistics", "/stats", "/counters"]:
            assert client.get(address).status_code == 404
