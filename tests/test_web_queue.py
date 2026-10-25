"""The queue: at most 3 conversions convert at once and 20 wait their turn, no file is taken
while the outputs held reach their cap, each browser converts one file at a time, and a visitor
can cancel. A held sandbox lets each test decide when a conversion ends."""

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace

import pytest
from fake_clock import FakeClock
from fastapi.testclient import TestClient
from held_sandbox import HeldSandbox
from scripted_sandbox import ScriptedSandbox
from web_browser import (
    SETTINGS,
    as_browser,
    browser,
    browser_token,
    cancel,
    send,
    title,
    upload,
    wait_for_state,
    wait_until,
)

from pdf_to_doc.web.sandboxes import Ended
from pdf_to_doc.web.statistics import Statistics


@pytest.fixture
def held() -> HeldSandbox:
    return HeldSandbox()


@pytest.fixture
def client(held: HeldSandbox) -> Iterator[TestClient]:
    with browser(held) as client:
        yield client


def source(number: int) -> bytes:
    """A file of its own for each upload: the web app never reads it, and the held sandbox keeps it."""
    return f"ไฟล์ที่ {number}".encode()


@dataclass(frozen=True)
class Sent:
    """A file one browser sent: the browser's token, and its conversion's link."""

    token: str
    link: str


def send_from_new_browsers(client: TestClient, count: int) -> list[Sent]:
    """One file from each of `count` new browsers, numbered from 1 in the order sent."""
    sent = []
    for number in range(1, count + 1):
        token = browser_token()
        sent.append(Sent(token, upload(as_browser(client, token), source(number))))
    return sent


def started(held: HeldSandbox, count: int) -> None:
    wait_until(lambda: len(held.started) >= count, f"{count} conversions to start")


def state(client: TestClient, sent: Sent) -> dict[str, object]:
    """The conversion's state as its page asks for it, without the steps it also gets."""
    answer = dict(as_browser(client, sent.token).get(f"{sent.link}/state").json())
    answer.pop("steps", None)
    return answer


# The queue


def test_a_fourth_conversion_waits_in_first_place_until_a_place_frees(client: TestClient, held: HeldSandbox) -> None:
    first, _, _, fourth = send_from_new_browsers(client, 4)
    started(held, 3)

    assert state(client, fourth) == {"state": "waiting", "text": "รอคิว ลำดับที่ 1", "ongoing": True}
    assert "รอคิว ลำดับที่ 1" in as_browser(client, fourth.token).get(fourth.link).text

    held.started[0].end()

    wait_for_state(as_browser(client, fourth.token), fourth.link, lambda state: state["state"] == "running")
    assert [conversion.source for conversion in held.started] == [source(1), source(2), source(3), source(4)]


def test_the_24th_upload_is_refused_as_queue_full_and_not_kept(client: TestClient, held: HeldSandbox) -> None:
    sent = send_from_new_browsers(client, 23)  # 3 converting and 20 waiting

    response = send(as_browser(client, browser_token()), source(24))

    assert response.status_code == 503
    assert "คิวเต็ม" in response.text
    for number, each in enumerate(sent):
        started(held, number + 1)
        held.started[number].end()
        wait_for_state(as_browser(client, each.token), each.link, lambda state: state["state"] == "finished")
    upload(as_browser(client, browser_token()), source(25))
    started(held, 24)
    assert held.started[23].source == source(25)  # the refused file had not been queued after the others


# The cap on the outputs held

OUTPUTS = 600  # bytes of Markdown that each conversion in `large_outputs` gives back
SUMMARY = b'{"event": "summary", "pages": []}'


def large_outputs() -> ScriptedSandbox:
    """A sandbox whose every conversion finishes with `OUTPUTS` bytes of Markdown."""
    return ScriptedSandbox([SUMMARY], Ended(0, b"markdown %d\n" % OUTPUTS + bytes(OUTPUTS)))


def finished_from_new_browsers(client: TestClient, count: int) -> list[Sent]:
    """One file from each of `count` new browsers, each converted to the end."""
    sent = send_from_new_browsers(client, count)
    for each in sent:
        wait_for_state(as_browser(client, each.token), each.link, lambda state: state["state"] == "finished")
    return sent


def test_once_the_outputs_held_reach_their_cap_an_upload_is_refused_as_queue_full_until_some_are_deleted() -> None:
    statistics = Statistics(FakeClock().wall)
    with browser(large_outputs(), replace(SETTINGS, max_held_outputs=2 * OUTPUTS), statistics=statistics) as client:
        first, _ = finished_from_new_browsers(client, 2)

        refused = send(as_browser(client, browser_token()), source(3))

        assert refused.status_code == 503
        assert "คิวเต็ม" in refused.text
        as_browser(client, first.token).post(f"{first.link}/delete")
        upload(as_browser(client, browser_token()), source(4))
    since_start = statistics.report()["since_start"]
    assert since_start["refusals"] == {"held outputs full": 1}  # apart from a full queue
    assert since_start["conversions"] == {"finished": 3}  # the refused file was never converted


def freed_by_deleting(client: TestClient, clock: FakeClock, finished: Sent) -> None:
    as_browser(client, finished.token).post(f"{finished.link}/delete")


def freed_by_expiring(client: TestClient, clock: FakeClock, finished: Sent) -> None:
    clock.advance(10 * 60)


@pytest.mark.parametrize("free", [freed_by_deleting, freed_by_expiring], ids=["deleted", "expired"])
def test_while_the_outputs_held_reach_their_cap_a_waiting_conversion_does_not_start(
    free: Callable[[TestClient, FakeClock, Sent], None],
) -> None:
    # Only the running conversions may add their outputs on top of the cap (the user's choice, 2026-10-25).
    clock, held = FakeClock(), HeldSandbox()
    with browser(held, replace(SETTINGS, max_running=1, max_held_outputs=1), clock) as client:
        first, waiting = send_from_new_browsers(client, 2)
        started(held, 1)
        held.started[0].end()
        wait_for_state(as_browser(client, first.token), first.link, lambda state: state["state"] == "finished")

        time.sleep(0.5)  # time enough for the waiting one to start, if it could
        assert len(held.started) == 1
        assert state(client, waiting)["state"] == "waiting"

        free(client, clock, first)

        wait_for_state(as_browser(client, waiting.token), waiting.link, lambda state: state["state"] == "running")


def test_once_the_outputs_held_expire_uploads_are_taken_again() -> None:
    clock = FakeClock()
    with browser(large_outputs(), replace(SETTINGS, max_held_outputs=OUTPUTS), clock) as client:
        finished_from_new_browsers(client, 1)
        assert send(as_browser(client, browser_token()), source(2)).status_code == 503

        clock.advance(10 * 60)

        upload(as_browser(client, browser_token()), source(3))


# One file at a time


def test_a_browser_converts_one_file_at_a_time_and_others_are_not_held_up(
    client: TestClient, held: HeldSandbox
) -> None:
    mine, theirs = browser_token(), browser_token()
    link = upload(as_browser(client, mine), source(1))

    second = send(as_browser(client, mine), source(2))

    assert second.status_code == 409
    assert "มีไฟล์ที่กำลังแปลงอยู่แล้ว" in second.text
    assert f'href="{link}"' in second.text  # to go back to it, or cancel it
    upload(as_browser(client, theirs), source(3))
    started(held, 2)
    held.started[0].end()
    wait_for_state(as_browser(client, mine), link, lambda state: state["state"] == "finished")
    upload(as_browser(client, mine), source(4))


# Cancelling


def test_cancelling_a_waiting_conversion_takes_it_out_of_the_queue(client: TestClient, held: HeldSandbox) -> None:
    *_, fourth, fifth = send_from_new_browsers(client, 5)
    started(held, 3)

    cancel(as_browser(client, fourth.token), fourth.link)

    assert "ยกเลิกการแปลงแล้ว" in as_browser(client, fourth.token).get(fourth.link).text
    assert state(client, fifth)["text"] == "รอคิว ลำดับที่ 1"
    held.started[0].end()
    wait_for_state(as_browser(client, fifth.token), fifth.link, lambda state: state["state"] == "running")
    assert held.started[3].source == source(5)


def test_cancelling_a_running_conversion_stops_its_sandbox_and_starts_the_next(
    client: TestClient, held: HeldSandbox
) -> None:
    first, _, _, fourth = send_from_new_browsers(client, 4)
    started(held, 3)

    cancel(as_browser(client, first.token), first.link)

    wait_for_state(as_browser(client, fourth.token), fourth.link, lambda state: state["state"] == "running")
    assert held.started[0].stopped
    assert "ยกเลิกการแปลงแล้ว" in as_browser(client, first.token).get(first.link).text


def test_a_browser_may_send_another_file_as_soon_as_it_cancels_even_while_the_sandbox_stops() -> None:
    held = HeldSandbox(stopping_takes=2)
    with browser(held) as client:
        [first] = send_from_new_browsers(client, 1)
        started(held, 1)

        cancel(as_browser(client, first.token), first.link)

        upload(as_browser(client, first.token), source(2))


def test_a_cancel_stays_a_cancel_when_stopping_the_sandbox_fails() -> None:
    held = HeldSandbox(stopping_fails=True)
    with browser(held) as client:
        [first] = send_from_new_browsers(client, 1)
        started(held, 1)

        cancel(as_browser(client, first.token), first.link)

        wait_until(lambda: held.started[0].stopped, "the sandbox to be told to stop")
        assert state(client, first)["state"] == "cancelled"
        assert "ยกเลิกการแปลงแล้ว" in as_browser(client, first.token).get(first.link).text


def test_another_browser_cannot_cancel_a_conversion(client: TestClient, held: HeldSandbox) -> None:
    [first] = send_from_new_browsers(client, 1)

    response = as_browser(client, browser_token()).post(f"{first.link}/cancel", follow_redirects=False)

    assert response.status_code == 404
    started(held, 1)
    assert not held.started[0].stopped


# The tab's title


def test_the_tab_title_shows_waiting_converting_and_done(client: TestClient, held: HeldSandbox) -> None:
    first, _, _, fourth = send_from_new_browsers(client, 4)
    started(held, 3)
    wait_for_state(as_browser(client, first.token), first.link, lambda state: state["text"] == "OCR หน้า 1/2")

    assert title(as_browser(client, first.token), first.link) == "OCR หน้า 1/2"
    assert title(as_browser(client, fourth.token), fourth.link) == "รอคิว ลำดับที่ 1"
    held.started[0].end()
    wait_for_state(as_browser(client, first.token), first.link, lambda state: state["state"] == "finished")
    assert title(as_browser(client, first.token), first.link) == "แปลงเสร็จแล้ว"
