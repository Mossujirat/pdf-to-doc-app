"""The home page, which explains a conversion: the limits it shows are the ones the service and
the converter use, and it loads nothing from another site but the bot check's script."""

import re
from dataclasses import replace
from urllib.parse import urlparse

from scripted_sandbox import ScriptedSandbox
from web_browser import SETTINGS, browser, shown_text

from pdf_to_doc.intake import MAX_BYTES, MAX_PAGES
from pdf_to_doc.model import Placeholder
from pdf_to_doc.validation import MIN_DICTIONARY_SHARE, MIN_WORDS_TO_JUDGE
from pdf_to_doc.web.bot_check import SCRIPT
from pdf_to_doc.web.upload import KEEP_IMAGES_FIELD, KEEP_IMAGES_VALUES


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


def attribute(tag: str, name: str) -> str:
    found = re.search(rf'\s{name}="([^"]*)"', tag)
    assert found is not None, f"no {name} in {tag}"
    return found[1]


def test_the_choice_of_kept_images_sits_in_the_upload_form_above_the_drop_area_with_ocr_chosen() -> None:
    with browser(ScriptedSandbox([], None)) as client:
        page = client.get("/").text
    form = page.split('<form id="upload"')[1].split("</form>")[0]
    options = re.findall(r"<input\b[^>]*\stype=\"radio\"[^>]*>", form)

    assert [attribute(option, "name") for option in options] == [KEEP_IMAGES_FIELD] * 2
    assert [KEEP_IMAGES_VALUES[attribute(option, "value")] for option in options] == [False, True]
    # OCR is chosen whenever the page opens: the browser does not bring back a choice made before.
    assert ["checked" in option for option in options] == [True, False]
    assert all('autocomplete="off"' in option for option in options)
    # Above the drop area, and outside the file input's label, so that choosing never opens the picker.
    drop_area = form.index('class="drop-frame"')
    assert all(form.index(option) < drop_area for option in options)


def inside_row(page: str, heading: str) -> str:
    """The text of the row under "ข้างในทำอะไรกับไฟล์ของคุณ" with that heading, as a visitor reads it."""
    return shown_text(page.split(f"<h3>{heading}</h3>")[1].split('class="inside-row"')[0])


def test_the_home_page_explains_what_keeping_scans_as_images_does() -> None:
    with browser(ScriptedSandbox([], None)) as client:
        page = client.get("/").text
    how = shown_text(page.split('id="how-title"')[1].split('id="inside-title"')[0])
    reading = inside_row(page, "อ่านทีละหน้า ด้วยวิธีที่เหมาะกับหน้านั้น")
    wrong_text = inside_row(page, "จับข้อความในไฟล์ที่ผิด")
    placeholders = inside_row(page, "เก็บโครงสร้าง และไม่เดาสิ่งที่อ่านไม่ได้")
    outputs = inside_row(page, "เอกสารเดียว ได้สองไฟล์")

    # Waiting: OCR takes minutes, and keeping scans as images is the other way.
    assert "เก็บหน้าสแกนเป็นภาพ" in how
    # Reading page by page: a kept scan is its image in the DOCX, and its placeholder in the Markdown.
    assert "เก็บหน้าสแกนเป็นภาพ" in reading and f"[{Placeholder('scan').name}]" in reading
    # A kept scan's wrong text is dropped, not read again with OCR.
    assert "หน้าสแกนที่เลือกเก็บเป็นภาพ" in wrong_text
    # Placeholders: pictures show as themselves in the DOCX when images are kept, and so the two
    # outputs differ there.
    assert "เก็บหน้าสแกนเป็นภาพ" in placeholders and "เก็บหน้าสแกนเป็นภาพ" in outputs


def test_the_home_page_loads_nothing_from_another_site_but_the_bot_checks_script() -> None:
    with browser(ScriptedSandbox([], None)) as client:
        page = client.get("/").text
        loaded = re.findall(r"<(?:img|script|iframe|source|video|audio|embed)\b[^>]*\ssrc=\"([^\"]+)\"", page)
        loaded += re.findall(r"<link\b[^>]*\shref=\"([^\"]+)\"", page)
        for stylesheet in [path for path in loaded if path.endswith(".css")]:
            loaded += re.findall(r"url\(\s*[\"']?([^\"')]+)", client.get(stylesheet).text)

    assert [path for path in loaded if urlparse(path).netloc] == [SCRIPT]
    assert "<img" not in page  # its pictures are drawn in the page itself, from no image file
