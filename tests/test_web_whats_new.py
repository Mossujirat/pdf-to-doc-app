"""The what's-new page: the known limitations as they are now, then what the latest releases
improved, newest first (GLOSSARY.md, "Web service")."""

import re
from datetime import date
from pathlib import Path

import pytest
from scripted_sandbox import ScriptedSandbox
from web_browser import browser, shown_text

from pdf_to_doc.web import pages
from pdf_to_doc.web.releases import KNOWN_LIMITATIONS, RELEASES, KnownLimitation, Release

# The issue tracker. The image leaves it out, so the tests that read it run on a developer's machine.
TRACKER = Path(__file__).parent.parent / ".scratch"

LIMITATION = KnownLimitation("ช่องที่ติ๊กไว้ในหน้าสแกนหายไป", ("converter-engine/issues/26-ticked-boxes-are-lost.md",))


def test_the_page_shows_the_known_limitations_then_the_latest_three_releases_newest_first() -> None:
    releases = (
        Release(date(2027, 1, 5), ("ตารางอ่านได้ดีขึ้น",)),
        Release(date(2026, 11, 20), ("หน้าตะแคงอ่านได้",)),
        Release(date(2026, 10, 31), ("หน้ากลับหัวอ่านได้",)),
        Release(date(2026, 10, 22), ("เปิดให้ใช้งานครั้งแรก",)),
    )

    text = shown_text(pages.whats_new(releases, (LIMITATION,)))

    order = [
        "ข้อจำกัดที่ควรรู้",
        "ช่องที่ติ๊กไว้ในหน้าสแกนหายไป",
        "5 มกราคม 2570 ล่าสุด",
        "ตารางอ่านได้ดีขึ้น",
        "20 พฤศจิกายน 2569",
        "หน้าตะแคงอ่านได้",
        "31 ตุลาคม 2569",
        "หน้ากลับหัวอ่านได้",
    ]
    places = [text.index(part) for part in order]
    assert places == sorted(places)
    assert text.count("ล่าสุด") == 1  # the newest release alone
    assert "22 ตุลาคม 2569" not in text and "เปิดให้ใช้งานครั้งแรก" not in text  # only the latest three


def test_with_no_known_limitation_the_section_is_left_out() -> None:
    text = shown_text(pages.whats_new((Release(date(2026, 10, 22), ("เปิดให้ใช้งานครั้งแรก",)),), ()))

    assert "ข้อจำกัดที่ควรรู้" not in text
    assert "22 ตุลาคม 2569 ล่าสุด เปิดให้ใช้งานครั้งแรก" in text


def test_every_page_links_to_the_whats_new_page_between_the_source_code_and_the_issues() -> None:
    with browser(ScriptedSandbox([], None)) as client:
        for path in ("/", "/privacy", "/whats-new", "/conversions/unknown"):
            footer = shown_text(client.get(path).text.split("<footer")[1])
            assert "ซอร์สโค้ด มีอะไรใหม่ แจ้งปัญหา" in footer
        page = client.get("/whats-new")

    assert page.status_code == 200
    assert 'href="/whats-new"' in page.text.split("<footer")[1]


def test_releases_are_newest_first_with_no_two_on_the_same_day() -> None:
    days = [release.went_live for release in RELEASES]

    assert days == sorted(set(days), reverse=True)
    assert all(release.improvements for release in RELEASES)


@pytest.mark.skipif(not TRACKER.is_dir(), reason="the issue tracker is not in the image")
@pytest.mark.parametrize("limitation", KNOWN_LIMITATIONS, ids=lambda limitation: limitation.tickets[0])
def test_every_known_limitation_stands_for_open_tickets(limitation: KnownLimitation) -> None:
    assert limitation.tickets
    for ticket in limitation.tickets:
        status = re.search(r"^\*\*Status:\*\* *(\S+)", (TRACKER / ticket).read_text(encoding="utf-8"), re.MULTILINE)
        assert status is not None, f"{ticket} has no status"
        assert status[1] != "done", f"{ticket} is done: drop its known limitation, and list the fix in the release"
