"""The daily page allowance: each client address may convert so many pages a day, Bangkok time,
and the address comes only from the trusted proxy's header. A fake clock moves the days on."""

import logging
from dataclasses import replace

import pytest
from fake_clock import FakeClock
from fake_ocr import FailingEngine
from fake_sandbox import FakeSandbox
from fastapi.testclient import TestClient
from held_sandbox import HeldSandbox
from pdf_builder import Scan, pdf
from scripted_sandbox import ScriptedSandbox
from web_browser import SETTINGS, as_browser, browser, browser_token, cancel, converted, ended_state, upload, wait_until

from pdf_to_doc.web.allowance import Allowance
from pdf_to_doc.web.app import create_app
from pdf_to_doc.web.sandboxes import Ended
from pdf_to_doc.web.settings import Misconfigured

PROXY = "100.64.0.7"  # the Tailscale container
VISITOR = "203.0.113.5"
HEADER = "X-Forwarded-For"
# Five pages a day, for files of a few pages; the service's own default is 500.
FIVE_A_DAY = replace(SETTINGS, pages_per_day=5, trusted_proxy=PROXY, client_ip_header=HEADER)


def of_pages(count: int) -> bytes:
    """A source file of `count` text pages."""
    return pdf(*[[f"หน้าที่ {number}"] for number in range(1, count + 1)])


def from_new_browser(client: TestClient, source: bytes, *headers: tuple[str, str]) -> tuple[str, str]:
    """Convert from a browser of its own, sending `headers`: how it ended, and what its page says."""
    return converted(as_browser(client, browser_token()), source, list(headers))


def test_a_file_over_what_is_left_today_is_stopped_with_what_remains_and_when() -> None:
    with browser(FakeSandbox(), FIVE_A_DAY, FakeClock()) as client:
        assert from_new_browser(client, of_pages(3))[0] == "finished"

        state, page = from_new_browser(client, of_pages(3))

    assert state == "over_allowance"
    assert "ไฟล์นี้มี 3 หน้า แต่วันนี้แปลงได้อีก 2 หน้า" in page
    assert "เที่ยงคืนนี้ เวลาประเทศไทย" in page


def test_the_allowance_starts_again_at_midnight_bangkok_time() -> None:
    clock = FakeClock()  # noon in Bangkok
    with browser(FakeSandbox(), FIVE_A_DAY, clock) as client:
        from_new_browser(client, of_pages(5))
        clock.advance(12 * 60 * 60 - 1)
        assert from_new_browser(client, of_pages(1))[0] == "over_allowance"

        clock.advance(1)

        assert from_new_browser(client, of_pages(5))[0] == "finished"


def test_yesterdays_addresses_leave_memory_after_midnight_though_no_file_comes() -> None:
    clock = FakeClock()  # noon in Bangkok
    allowance = Allowance(5, clock.wall)
    allowance.charge(VISITOR, 2)
    assert allowance.forget_past_days() == 0  # still today

    clock.advance(12 * 60 * 60)

    assert allowance.forget_past_days() == 1  # the visitor's address, dropped
    assert allowance.forget_past_days() == 0


def test_a_failed_conversion_gives_its_pages_back() -> None:
    with browser(FakeSandbox(FailingEngine), FIVE_A_DAY, FakeClock()) as client:
        assert from_new_browser(client, pdf(*[Scan([f"สแกน {number}"], dpi=50) for number in range(5)]))[0] == "failed"

        assert from_new_browser(client, of_pages(5))[0] == "finished"


def test_a_conversion_stopped_by_the_time_limit_gives_its_pages_back() -> None:
    opened = b'{"event": "opened", "source_type": "pdf", "pages": 5}'
    with browser(ScriptedSandbox([opened], Ended(137, b"", timed_out=True)), FIVE_A_DAY, FakeClock()) as client:
        assert from_new_browser(client, of_pages(5))[0] == "failed"

        assert from_new_browser(client, of_pages(5))[0] == "failed"  # charged again, so given back before


def test_a_cancelled_conversion_keeps_its_pages_charged() -> None:
    held = HeldSandbox()  # its conversions report 2 pages
    with browser(held, replace(FIVE_A_DAY, pages_per_day=3), FakeClock()) as client:
        link = upload(as_browser(client, browser_token()), of_pages(2))
        wait_until(lambda: client.get(f"{link}/state").json()["text"] == "OCR หน้า 1/2", "the pages to be charged")
        cancel(client, link)
        second = upload(as_browser(client, browser_token()), of_pages(2))

        assert ended_state(client, second) == "over_allowance"
        assert held.started[1].stopped  # stopped at the page count, before any page was read


# Whose allowance


def test_from_anywhere_but_the_trusted_proxy_forged_headers_change_nothing() -> None:
    with browser(FakeSandbox(), FIVE_A_DAY, FakeClock(), address=VISITOR) as client:
        from_new_browser(client, of_pages(3), (HEADER, "198.51.100.1"))

        state, _ = from_new_browser(client, of_pages(3), (HEADER, "198.51.100.2"), ("CF-Connecting-IP", "198.51.100.3"))

    assert state == "over_allowance"


def test_through_the_trusted_proxy_two_clients_are_counted_apart() -> None:
    with browser(FakeSandbox(), FIVE_A_DAY, FakeClock(), address=PROXY) as client:
        assert from_new_browser(client, of_pages(3), (HEADER, "198.51.100.1"))[0] == "finished"

        assert from_new_browser(client, of_pages(3), (HEADER, "198.51.100.2"))[0] == "finished"
        assert from_new_browser(client, of_pages(3), (HEADER, "198.51.100.1"))[0] == "over_allowance"


@pytest.mark.parametrize(
    "forged",
    [
        pytest.param([(HEADER, "198.51.100.9, 198.51.100.1")], id="first on the proxy's line"),
        pytest.param([(HEADER, "198.51.100.9"), (HEADER, "198.51.100.1")], id="on a line of its own"),
        pytest.param([(HEADER, "198.51.100.1"), ("CF-Connecting-IP", "198.51.100.9")], id="in another header"),
    ],
)
def test_through_the_trusted_proxy_only_the_address_it_added_counts(forged: list[tuple[str, str]]) -> None:
    # The proxy saw 198.51.100.1; the visitor sent 198.51.100.9 as well, to pass as someone else.
    with browser(FakeSandbox(), FIVE_A_DAY, FakeClock(), address=PROXY) as client:
        from_new_browser(client, of_pages(3), (HEADER, "198.51.100.1"))

        state, _ = from_new_browser(client, of_pages(3), *forged)

    assert state == "over_allowance"


def test_an_ipv6_client_is_counted_by_its_64_block() -> None:
    with browser(FakeSandbox(), FIVE_A_DAY, FakeClock(), address=PROXY) as client:
        from_new_browser(client, of_pages(3), (HEADER, "2001:db8:1:2::a"))

        assert from_new_browser(client, of_pages(3), (HEADER, "2001:db8:1:2:ffff::b"))[0] == "over_allowance"
        assert from_new_browser(client, of_pages(3), (HEADER, "2001:db8:1:3::a"))[0] == "finished"


def test_the_public_service_refuses_to_start_without_its_trusted_proxy() -> None:
    production = replace(SETTINGS, production=True, client_ip_header=HEADER)

    with pytest.raises(Misconfigured):
        create_app(FakeSandbox(), production)


def test_no_address_is_ever_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG), browser(FakeSandbox(), FIVE_A_DAY, FakeClock(), address=PROXY) as client:
        from_new_browser(client, of_pages(3), (HEADER, "198.51.100.1"))
        from_new_browser(client, of_pages(3), (HEADER, "198.51.100.1"))

    assert "198.51.100.1" not in caplog.text
    assert PROXY not in caplog.text
