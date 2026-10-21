"""The web app's pages, in Thai: plain HTML for now (ticket 11 designs them), with no inline script."""

from html import escape

from pdf_to_doc.intake import MAX_BYTES, MAX_PAGES
from pdf_to_doc.web.conversions import Conversion

_MB = 1024 * 1024
_NAME = "pdf-to-doc"


def home() -> str:
    return _page(
        f"""<h1>แปลง PDF หรือ DOCX เป็นข้อความ</h1>
<form id="upload" method="post" action="/conversions" enctype="multipart/form-data">
<input type="file" name="file" accept=".pdf,.docx" required>
<button type="submit">แปลงไฟล์</button>
</form>
<p>PDF หรือ DOCX ไม่เกิน {MAX_BYTES // _MB} MB และไม่เกิน {MAX_PAGES} หน้า</p>"""
    )


def status(conversion: Conversion) -> str:
    """What the conversion is doing, or how it ended, in a few words."""
    progress = conversion.progress
    match conversion.state:
        case "finished":
            return "แปลงเสร็จแล้ว"
        case "refused":
            return "แปลงไฟล์นี้ไม่ได้"
        case "failed":
            return "การแปลงล้มเหลว"
    if progress is not None and progress.stage == "ocr":
        return f"OCR หน้า {progress.current}/{progress.total}"
    if progress is not None and progress.stage == "writing":
        return "กำลังสร้างไฟล์ผลลัพธ์"
    if conversion.opened is not None:
        return f"กำลังอ่านไฟล์ {conversion.opened.pages} หน้า"
    return "กำลังเริ่มแปลง"


def conversion_page(identifier: str, conversion: Conversion) -> str:
    """The status as the heading, and below it what the visitor can do now."""
    link = f"/conversions/{escape(identifier)}"
    again = '<p><a href="/">แปลงไฟล์อื่น</a></p>'
    match conversion.state:
        case "running":
            body = f'<p id="status" data-state="{link}/state" aria-live="polite">{escape(status(conversion))}</p>'
        case "finished":
            assert conversion.summary is not None
            downloads = [f'<a href="{link}/markdown" download>ดาวน์โหลด Markdown</a>']
            if "docx" in conversion.outputs:
                downloads.append(f'<a href="{link}/docx" download>ดาวน์โหลด DOCX</a>')
            body = f"""<p>{escape(conversion.summary.headline())}</p>
<p><button type="button" id="copy" data-markdown="{link}/markdown">คัดลอก Markdown</button></p>
<p>{" ".join(downloads)}</p>
{again}"""
        case "refused":
            body = again
        case "failed":
            body = f"<p>กรุณาลองใหม่อีกครั้ง</p>\n{again}"
    return _page(f"<h1>{escape(status(conversion))}</h1>\n{body}")


def not_found() -> str:
    return _page('<h1>ไม่พบหน้านี้</h1>\n<p><a href="/">กลับไปหน้าแรก</a></p>')


def too_large() -> str:
    return _page(f'<h1>ไฟล์ใหญ่เกิน {MAX_BYTES // _MB} MB</h1>\n<p><a href="/">เลือกไฟล์อื่น</a></p>')


def not_an_upload() -> str:
    return _page('<h1>ไม่ได้รับไฟล์</h1>\n<p><a href="/">กลับไปเลือกไฟล์</a></p>')


def _page(body: str) -> str:
    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_NAME}</title>
</head>
<body>
{body}
<script src="/static/app.js" defer></script>
</body>
</html>
"""
