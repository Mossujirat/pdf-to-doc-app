"""The home page, which explains a conversion: the limits it shows are the ones the service and
the converter use, and it loads nothing from another site but the bot check's script."""

import re
from dataclasses import replace
from urllib.parse import urlparse

from scripted_sandbox import ScriptedSandbox
from web_browser import SETTINGS, browser, shown_text

from pdf_to_doc.intake import MAX_BYTES, MAX_PAGES
from pdf_to_doc.validation import MIN_DICTIONARY_SHARE, MIN_WORDS_TO_JUDGE
from pdf_to_doc.web.bot_check import SCRIPT


def test_the_home_page_shows_the_limits_the_service_and_the_converter_use() -> None:
    with browser(ScriptedSandbox([], None), replace(SETTINGS, keep_for=300, pages_per_day=40)) as client:
        page = client.get("/").text
    inside = shown_text(page.split('id="inside-title"')[1])  # what the converter does with a file

    # The converter's limits on a source file, and when a text layer's words are too seldom
    # dictionary words: a change to either changes the page.
    assert f"{MAX_BYTES // 2**20} MB" in inside and f"{MAX_PAGES} หน้า" in inside
    assert f"{round(MIN_DICTIONARY_SHARE * 100)}%" in inside and f"{MIN_WORDS_TO_JUDGE} คำ" in inside
    assert "5 นาที" in inside  # how long results are kept
    assert "วันละ 40 หน้า" in shown_text(page)  # the daily allowance, beside the drop area


def test_the_home_page_loads_nothing_from_another_site_but_the_bot_checks_script() -> None:
    with browser(ScriptedSandbox([], None)) as client:
        page = client.get("/").text
        loaded = re.findall(r"<(?:img|script|iframe|source|video|audio|embed)\b[^>]*\ssrc=\"([^\"]+)\"", page)
        loaded += re.findall(r"<link\b[^>]*\shref=\"([^\"]+)\"", page)
        for stylesheet in [path for path in loaded if path.endswith(".css")]:
            loaded += re.findall(r"url\(\s*[\"']?([^\"')]+)", client.get(stylesheet).text)

    assert [path for path in loaded if urlparse(path).netloc] == [SCRIPT]
    assert "<img" not in page  # its pictures are drawn in the page itself, from no image file
