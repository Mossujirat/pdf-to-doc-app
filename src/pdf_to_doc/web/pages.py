"""The web app's pages, in Thai: plain HTML for now (ticket 11 designs them), with no inline script."""

import math
from html import escape

from pdf_to_doc.intake import MAX_BYTES, MAX_PAGES, PasswordRequired
from pdf_to_doc.refusals import refusal_message, too_large_unmeasured
from pdf_to_doc.web.bot_check import ACTION, SCRIPT
from pdf_to_doc.web.conversions import Conversion
from pdf_to_doc.web.protocol import RefusalEvent

_MB = 1024 * 1024
_NAME = "pdf-to-doc"


def home(bot_check_site_key: str | None) -> str:
    """The upload form, with the bot check's widget, whose token goes with the file. Without a
    site key there is no widget, and every upload is refused."""
    widget = script = ""
    if bot_check_site_key is not None:
        widget = f'\n<div class="cf-turnstile" data-sitekey="{escape(bot_check_site_key)}" data-action="{ACTION}"></div>'
        script = f'\n<script src="{SCRIPT}" async defer></script>'
    return _page(
        _NAME,
        f"""<h1>แปลง PDF หรือ DOCX เป็นข้อความ</h1>
<form id="upload" method="post" action="/conversions" enctype="multipart/form-data">{widget}
<input type="file" name="file" accept=".pdf,.docx" required>
<button type="submit">แปลงไฟล์</button>
</form>
<p>PDF หรือ DOCX ไม่เกิน {MAX_BYTES // _MB} MB และไม่เกิน {MAX_PAGES} หน้า</p>{script}""",
    )


def status(conversion: Conversion, place: int | None) -> str:
    """What the conversion is doing, or how it ended, in a few words. `place` is a waiting
    conversion's place in the queue. The tab's title shows it too."""
    progress = conversion.progress
    match conversion.state:
        case "waiting":
            return f"รอคิว ลำดับที่ {place}"
        case "finished":
            return "แปลงเสร็จแล้ว"
        case "refused":
            return "แปลงไฟล์นี้ไม่ได้"
        case "failed":
            return "การแปลงล้มเหลว"
        case "cancelled":
            return "ยกเลิกการแปลงแล้ว"
    if progress is not None and progress.stage == "ocr":
        return f"OCR หน้า {progress.current}/{progress.total}"
    if progress is not None and progress.stage == "writing":
        return "กำลังสร้างไฟล์ผลลัพธ์"
    if conversion.opened is not None:
        return f"กำลังอ่านไฟล์ {conversion.opened.pages} หน้า"
    return "กำลังเริ่มแปลง"


def conversion_page(identifier: str, conversion: Conversion, place: int | None, time_left: float | None) -> str:
    """The status as the title and the heading, and below it what the visitor can do now.
    `time_left` is how many more seconds an ended conversion's outputs are kept."""
    link = f"/conversions/{escape(identifier)}"
    text = status(conversion, place)
    heading = f"<h1>{escape(text)}</h1>"
    again = '<p><a href="/">แปลงไฟล์อื่น</a></p>'
    match conversion.state:
        case _ if conversion.ongoing:
            # The script keeps the heading up to date.
            heading = f'<h1 id="status" data-state="{link}/state" aria-live="polite">{escape(text)}</h1>'
            body = f'<form method="post" action="{link}/cancel"><button type="submit">ยกเลิก</button></form>'
        case "finished":
            assert conversion.summary is not None and time_left is not None
            downloads = [f'<a href="{link}/markdown" download>ดาวน์โหลด Markdown</a>']
            if "docx" in conversion.outputs:
                downloads.append(f'<a href="{link}/docx" download>ดาวน์โหลด DOCX</a>')
            body = f"""<p>{escape(conversion.summary.headline())}</p>
<p><button type="button" id="copy" data-markdown="{link}/markdown">คัดลอก Markdown</button></p>
<p>{" ".join(downloads)}</p>
<p>ไฟล์ผลลัพธ์จะถูกลบภายใน {_minutes(time_left)} นาที</p>
<form method="post" action="{link}/delete"><button type="submit">ลบเดี๋ยวนี้</button></form>
{again}"""
        case "refused":
            assert conversion.refusal is not None
            body = f"<p>{escape(_refusal(conversion.refusal))}</p>\n{again}"
        case "failed" if conversion.timed_out:
            body = f"<p>การแปลงใช้เวลานานเกินกำหนดจึงถูกหยุด กรุณาลองใหม่อีกครั้ง</p>\n{again}"
        case "failed":
            body = f"<p>กรุณาลองใหม่อีกครั้ง</p>\n{again}"
        case _:  # cancelled
            body = again
    return _page(text, f"{heading}\n{body}")


def _refusal(refusal: RefusalEvent) -> str:
    """Why the file was refused, in the command line's words, or the web's own where only the web
    meets it. The sandbox's own text never shows: only the kind of refusal it sent."""
    error = refusal.intake_error()
    if isinstance(error, PasswordRequired):  # the web takes no password yet
        return "ยังแปลง PDF ที่ล็อกด้วยรหัสผ่านไม่ได้ กรุณาปลดรหัสผ่านออกแล้วส่งไฟล์มาใหม่"
    return refusal_message(error) or "ไฟล์นี้แปลงไม่ได้"


def not_found(keep_for: float) -> str:
    """For a link that has expired, been deleted, been lost to a restart, never existed, or
    belongs to another browser: it never says which."""
    return _page(
        _NAME,
        "<h1>ไม่พบหน้านี้</h1>\n"
        "<p>ถ้าเป็นลิงก์ของการแปลงไฟล์ การแปลงนั้นอาจหมดเวลาเก็บแล้ว ถูกลบ หรือหายไปเมื่อระบบเริ่มทำงานใหม่"
        f" ผลการแปลงเก็บไว้ {_minutes(keep_for)} นาทีหลังแปลงเสร็จ</p>\n"
        '<p><a href="/">แปลงไฟล์ใหม่</a></p>',
    )


def deleted() -> str:
    return _page(_NAME, '<h1>ลบไฟล์ผลลัพธ์แล้ว</h1>\n<p><a href="/">แปลงไฟล์อื่น</a></p>')


def too_large() -> str:
    """For an upload past the size limit. Unlike the command line's, its message gives no size:
    reading stopped at the limit, before the whole file came."""
    return _page(
        _NAME,
        f'<h1>แปลงไฟล์นี้ไม่ได้</h1>\n<p>{too_large_unmeasured(MAX_BYTES)}</p>\n<p><a href="/">เลือกไฟล์อื่น</a></p>',
    )


def not_an_upload() -> str:
    return _page(_NAME, '<h1>ไม่ได้รับไฟล์</h1>\n<p><a href="/">กลับไปเลือกไฟล์</a></p>')


def bot_check_failed() -> str:
    return _page(
        _NAME,
        "<h1>ส่งไฟล์ไม่สำเร็จ</h1>\n"
        "<p>ตรวจสอบไม่ได้ว่าไฟล์นี้ส่งมาจากผู้ใช้จริง กรุณากลับไปหน้าแรก รอสักครู่แล้วส่งไฟล์อีกครั้ง</p>\n"
        '<p><a href="/">กลับไปหน้าแรก</a></p>',
    )


def queue_full() -> str:
    return _page(_NAME, '<h1>คิวเต็ม</h1>\n<p>กรุณาลองใหม่อีกสักครู่</p>\n<p><a href="/">กลับไปหน้าแรก</a></p>')


def already_converting(identifier: str) -> str:
    """For a browser that sends a file while its conversion of another waits or runs."""
    return _page(
        _NAME,
        "<h1>มีไฟล์ที่กำลังแปลงอยู่แล้ว</h1>\n"
        "<p>แปลงได้ทีละไฟล์ กรุณารอให้ไฟล์ก่อนหน้าแปลงเสร็จ หรือยกเลิกไฟล์นั้นก่อน</p>\n"
        f'<p><a href="/conversions/{escape(identifier)}">ไปที่ไฟล์ที่กำลังแปลง</a></p>',
    )


def _minutes(seconds: float) -> int:
    """Whole minutes, rounded up, so that time left never reads as none while some remains."""
    return max(0, math.ceil(seconds / 60))


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
</head>
<body>
{body}
<script src="/static/app.js" defer></script>
</body>
</html>
"""
