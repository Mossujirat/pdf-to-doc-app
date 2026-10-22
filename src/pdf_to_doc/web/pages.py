"""The web app's pages, in Thai, with no inline script or style.

Each page has one plain, centred task, as people already know a converter to look. The home
page is a title, one big drop area and the steps of a conversion. Every other page is one card
in the middle: a conversion's card holds its status, what it is doing now or how it ended, and
what the visitor can do next. A step that changes is tinted for a moment (`static/app.js`).
"""

import math
from html import escape

from pdf_to_doc.intake import MAX_BYTES, MAX_PAGES, PasswordRequired
from pdf_to_doc.model import Placeholder
from pdf_to_doc.refusals import refusal_message, too_large_unmeasured
from pdf_to_doc.web.bot_check import ACTION, SCRIPT
from pdf_to_doc.web.conversions import Conversion
from pdf_to_doc.web.protocol import RefusalEvent

_MB = 1024 * 1024
_NAME = "ครบคำ"

# Icons, drawn in one stroke weight. They are decoration beside words that say the same.
_SVG = (
    '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{weight}" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{paths}</svg>'
)
_PLUS = _SVG.format(size=34, weight=2.5, paths='<path d="M12 5v14"/><path d="M5 12h14"/>')
_ARROW = _SVG.format(size=26, weight=2, paths='<path d="M4 12h15"/><path d="M13 6l6 6-6 6"/>')
_LOCK = _SVG.format(size=18, weight=2, paths='<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>')
_FILE = _SVG.format(
    size=22, weight=2, paths='<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'
)
_TICK = _SVG.format(size=16, weight=3, paths='<path d="M5 12.5l4.5 4.5L19 7.5"/>')
_COPY = _SVG.format(
    size=20,
    weight=2,
    paths='<rect x="8" y="8" width="12" height="12" rx="1.5"/>'
    '<path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8"/>',
)
_DOWN = _SVG.format(size=20, weight=2, paths='<path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M5 20h14"/>')
_CLOCK = _SVG.format(size=18, weight=2, paths='<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>')

# The steps of a conversion, as its card lists them while it waits or runs.
_STEPS = [
    ("queue", "รอคิว"),
    ("open", "เปิดไฟล์"),
    ("read", "อ่านข้อความในไฟล์"),
    ("ocr", "อ่านด้วย OCR"),
    ("write", "สร้างไฟล์ผลลัพธ์"),
]
_STEP_STATES = {"done": "เสร็จแล้ว", "skipped": "ข้าม", "now": "กำลังทำ", "later": "ยังไม่ถึง"}


def home(bot_check_site_key: str | None, keep_for: float, pages_per_day: int) -> str:
    """The title, the drop area, which is the upload form, with the bot check's widget, whose
    token goes with the file, and the steps of a conversion. Without a site key there is no
    widget, and every upload is refused."""
    widget = script = ""
    if bot_check_site_key is not None:
        widget = f'\n<div class="cf-turnstile" data-sitekey="{escape(bot_check_site_key)}" data-action="{ACTION}"></div>'
        script = f'\n<script src="{SCRIPT}" async defer></script>'
    kept = _minutes(keep_for)
    limits = f"ไม่เกิน {MAX_BYTES // _MB}&nbsp;MB และ {MAX_PAGES}&nbsp;หน้า"  # a number stays on its unit's line
    return _page(
        f"{_NAME} แปลง PDF เป็น Word และ Markdown",
        f"""<section class="hero" aria-labelledby="title">
<h1 class="title" id="title">แปลง PDF เป็น Word และ Markdown</h1>
<p class="subtitle">ข้อความภาษาไทยออกมาตรงต้นฉบับ สระและวรรณยุกต์อยู่ที่เดิม ไม่มีช่องว่างกลางคำ
พร้อมวางในแชต AI หรือแก้ต่อใน Word ใช้ฟรี ไม่ต้องสมัคร</p>
</section>
<form id="upload" class="upload" method="post" action="/conversions" enctype="multipart/form-data">{widget}
<div class="drop-frame">
<label class="drop">
<span class="drop-plus">{_PLUS}</span>
<span class="drop-title" data-drop-title>วางไฟล์ PDF หรือ DOCX ที่นี่</span>
<span class="drop-note">หรือกดเพื่อเลือกไฟล์</span>
<span class="drop-note" id="upload-limits">ไฟล์ละ{limits} · วันละ {pages_per_day}&nbsp;หน้า</span>
<span class="drop-name" data-file-name></span>
<input class="drop-input" type="file" name="file" accept=".pdf,.docx" required aria-describedby="upload-limits">
</label>
</div>
<noscript><button type="submit" class="button button--primary upload-submit">แปลงไฟล์</button></noscript>
<p class="assurance">{_LOCK}<span>ไฟล์ส่งถึงเซิร์ฟเวอร์ของเราเองแบบเข้ารหัส และแปลงในที่ที่ไม่มีอินเทอร์เน็ต
ไฟล์ต้นฉบับถูกลบทันทีที่แปลงเสร็จ ส่วนผลลัพธ์ถูกลบภายใน {kept} นาที</span></p>
</form>
<section class="how" aria-labelledby="how-title">
<h2 class="how-title" id="how-title">แปลงอย่างไร</h2>
<ol class="how-steps">
<li class="how-step"><div><h3>วางหรือเลือกไฟล์</h3>
<p>PDF หรือ DOCX ครั้งละหนึ่งไฟล์ {limits} แปลงได้วันละ {pages_per_day}&nbsp;หน้า</p></div></li>
<li class="how-step"><div><h3>รอแปลง</h3>
<p>หน้าเว็บบอกลำดับคิวและความคืบหน้า ไฟล์สแกนต้องอ่านด้วย OCR จึงอาจใช้เวลาหลายนาที
สลับไปทำอย่างอื่นแล้วกลับมาที่หน้าเดิมได้</p></div></li>
<li class="how-step"><div><h3>คัดลอกหรือดาวน์โหลด</h3>
<p>คัดลอก Markdown ไปวางในแชต AI หรือดาวน์โหลด DOCX ไปแก้ใน Word
ผลลัพธ์ถูกลบภายใน {kept} นาที หรือกดลบเองได้ทันที</p></div></li>
</ol>
<figure class="example">
<figcaption class="example-label">ตัวอย่าง: ข้อความที่ซ่อนอยู่ในไฟล์ผิด</figcaption>
<div class="example-row">
<p class="example-word example-word--wrong"><span>ในไฟล์เขียนว่า</span><strong>กำร</strong></p>
<span class="example-arrow">{_ARROW}<span class="visually-hidden">แก้เป็น</span></span>
<p class="example-word example-word--right"><span>{_NAME}ได้</span><strong>การ</strong></p>
</div>
<p class="example-note">หน้ากระดาษแสดงคำว่า การ แต่ข้อความในไฟล์เขียนว่า กำร หน้านั้นจึงถูกอ่านใหม่ด้วย OCR
ส่วนที่ยังไม่แน่ใจจะถูกทำเครื่องหมายไว้ให้ตรวจ</p>
</figure>
</section>{script}""",
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
        case "over_allowance":
            return "เกินจำนวนหน้าที่แปลงได้ในวันนี้"
    if progress is not None and progress.stage == "ocr":
        return f"OCR หน้า {progress.current}/{progress.total}"
    if progress is not None and progress.stage == "writing":
        return "กำลังสร้างไฟล์ผลลัพธ์"
    if conversion.opened is not None:
        return f"กำลังอ่านไฟล์ {conversion.opened.pages} หน้า"
    return "กำลังเริ่มแปลง"


def steps(conversion: Conversion, place: int | None) -> str:
    """The steps of a conversion that waits or runs: each done, skipped, happening now, or yet to
    come. OCR is skipped by a file with no page that needs it. The page asks for them again every
    2 seconds, with its state."""
    at = _step_at(conversion)
    items = []
    for index, (step, label) in enumerate(_STEPS):
        if index < at:
            state = "skipped" if step == "ocr" and not conversion.read_with_ocr else "done"
        else:
            state = "now" if index == at else "later"
        detail = meter = ""
        if step == "queue" and conversion.state == "waiting":
            detail = f"ลำดับที่ {place}"
        elif step == "open" and conversion.opened is not None:
            detail = f"{conversion.opened.pages} หน้า"
        elif step == "ocr" and conversion.progress is not None and conversion.progress.stage == "ocr":
            current, total = conversion.progress.current, conversion.progress.total
            detail = f"หน้า {current}/{total}"
            if current is not None and total:
                meter = f'\n<progress class="step-meter" max="{total}" value="{current}">{current}/{total}</progress>'
        elif state == "skipped":
            detail = "ไม่ต้องใช้"
        mark = _TICK if state == "done" else ""
        items.append(
            f'<li class="step step--{state}" data-step="{step}" data-at="{state}">'
            f'<span class="step-mark" aria-hidden="true">{mark}</span>'
            f'<span class="step-label">{label}<span class="visually-hidden"> {_STEP_STATES[state]}</span></span>'
            f'<span class="step-detail">{detail}</span>{meter}</li>'
        )
    return "\n".join(items)


def conversion_page(identifier: str, conversion: Conversion, place: int | None, time_left: float | None) -> str:
    """The conversion's card, with its status as the heading and the title, and below it what it
    is doing now or how it ended, and what the visitor can do next. `time_left` is how many more
    seconds an ended conversion's outputs are kept."""
    link = f"/conversions/{escape(identifier)}"
    text = status(conversion, place)
    polling = f' data-state="{link}/state"' if conversion.ongoing else ""
    chips = ""
    match conversion.outcome:
        case _ if conversion.ongoing:
            body = f"""<ol class="steps" id="steps">
{steps(conversion, place)}
</ol>
<p class="summary">หน้านี้อัปเดตเองทุก 2 วินาที สลับไปทำอย่างอื่นแล้วกลับมาที่หน้านี้ได้</p>
<div class="actions">
<form class="inline" method="post" action="{link}/cancel"><button type="submit" class="button button--secondary">ยกเลิก</button></form>
</div>"""
        case "finished":
            assert conversion.summary is not None and time_left is not None
            downloads = [f'<a class="button button--secondary" href="{link}/markdown" download>{_DOWN} ดาวน์โหลด Markdown</a>']
            if "docx" in conversion.outputs:
                downloads.append(f'<a class="button button--secondary" href="{link}/docx" download>{_DOWN} ดาวน์โหลด DOCX</a>')
            pages = conversion.summary.pages
            chips = f'<span class="chip">{len(pages)} หน้า</span>'
            to_check = sum(1 for page in pages if page.uncertain)
            if to_check:
                chips += f'<span class="chip chip--warn">ควรตรวจ {to_check} หน้า</span>'
            body = f"""<p class="summary">{escape(conversion.summary.headline())}</p>
<div class="actions actions--result">
<button type="button" class="button button--primary" id="copy" data-markdown="{link}/markdown">{_COPY} คัดลอก Markdown</button>
{"\n".join(downloads)}
</div>
<h2 class="section-title">อ่านทีละหน้า</h2>
<div class="pages-wrap" tabindex="0" role="region" aria-label="อ่านทีละหน้า">
<table class="pages">
<thead><tr><th scope="col">หน้า</th><th scope="col">อ่านจาก</th><th scope="col">ควรดู</th></tr></thead>
<tbody>
{_page_rows(conversion)}
</tbody>
</table>
</div>
<div class="ended">
<p class="kept">{_CLOCK} ไฟล์ผลลัพธ์จะถูกลบภายใน {_minutes(time_left)} นาที</p>
<form class="inline" method="post" action="{link}/delete"><button type="submit" class="button button--danger">ลบเดี๋ยวนี้</button></form>
</div>
<div class="actions"><a class="button button--secondary" href="/">แปลงไฟล์อื่น</a></div>"""
        case _:
            body = f"{_ended_message(conversion)}{_what_became_of_it(conversion)}"
    head = f"""<div class="card-head">
<p class="file">{_FILE}<span class="file-name">{escape(conversion.file_name)}</span></p>{f'<span class="chips">{chips}</span>' if chips else ""}
</div>"""
    return _page(
        text,
        f"""<section class="card" aria-labelledby="status">
{head}
<h1 class="status" id="status"{polling} aria-live="polite">{escape(text)}</h1>
{body}
</section>""",
    )


def _ended_message(conversion: Conversion) -> str:
    """Why a conversion that ended gave no result, where there is more to say than its status."""
    match conversion.outcome:
        case "refused":
            assert conversion.refusal is not None
            message = escape(_refusal(conversion.refusal))
        case "timed_out":
            message = "การแปลงใช้เวลานานเกินกำหนดจึงถูกหยุด กรุณาลองใหม่อีกครั้ง"
        case "failed":
            message = "กรุณาลองใหม่อีกครั้ง"
        case "over_allowance":
            assert conversion.opened is not None and conversion.pages_left is not None
            message = (
                f"ไฟล์นี้มี {conversion.opened.pages} หน้า แต่วันนี้แปลงได้อีก {conversion.pages_left} หน้า"
                " จำนวนหน้าจะเริ่มนับใหม่เที่ยงคืนนี้ เวลาประเทศไทย"
            )
        case _:  # cancelled
            return ""
    return f'<p class="message">{message}</p>\n'


def _what_became_of_it(conversion: Conversion) -> str:
    """For a conversion that ended with no result: what became of the file. One cancelled while it
    waited never had a sandbox."""
    facts = ["ไฟล์ต้นฉบับถูกลบออกจากหน่วยความจำแล้ว"]
    if conversion.started_at is not None:
        facts.append("ที่ที่ใช้แปลงไฟล์นี้ถูกทิ้งไปพร้อมกับการแปลง")
    facts += [
        "ไม่มีผลลัพธ์ จึงไม่มีอะไรให้ลบ",
        "บันทึกการทำงานของระบบไม่มีเนื้อหา ชื่อไฟล์ หรือลิงก์",
    ]
    items = "\n".join(f"<li>{_TICK}<span>{fact}</span></li>" for fact in facts)
    return f"""<h2 class="section-title">ไฟล์นี้เป็นอย่างไรแล้ว</h2>
<ul class="facts">
{items}
</ul>
<div class="actions"><a class="button button--primary" href="/">แปลงไฟล์อื่น</a></div>"""


def _page_rows(conversion: Conversion) -> str:
    """A finished conversion's pages: how each was read, and what on it the visitor should check.
    A page with uncertain text is tagged to check, as the summary's headline says."""
    assert conversion.summary is not None
    rows = []
    for page in conversion.summary.pages:
        read = "อ่านด้วย OCR" if page.kind == "ocr" else "ข้อความในไฟล์"
        notes = []
        if page.untrusted_text_layer:
            notes.append("ข้อความในไฟล์ผิด จึงอ่านด้วย OCR")
        if page.uncertain:
            notes.append(f"ไม่แน่ใจ {page.uncertain} จุด")
        for kind in dict.fromkeys(page.placeholders):
            notes.append(f"{Placeholder(kind).name} {page.placeholders.count(kind)}")
        noted = escape(" · ".join(notes)) if notes else '<span class="none">–</span>'
        if page.uncertain:
            noted = f'<span class="chip chip--warn">ตรวจ</span> {noted}'
        rows.append(f'<tr><th scope="row">หน้า {page.number}</th><td>{read}</td><td>{noted}</td></tr>')
    return "\n".join(rows)


def _step_at(conversion: Conversion) -> int:
    """Which of `_STEPS` the conversion is at."""
    if conversion.state == "waiting":
        return 0
    if conversion.opened is None:
        return 1
    stage = conversion.progress.stage if conversion.progress is not None else "reading"
    return {"reading": 2, "ocr": 3, "writing": 4}[stage]


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
    return _notice(
        "ไม่พบหน้านี้",
        "ถ้าเป็นลิงก์ของการแปลงไฟล์ การแปลงนั้นอาจหมดเวลาเก็บแล้ว ถูกลบ หรือหายไปเมื่อระบบเริ่มทำงานใหม่"
        f" ผลการแปลงเก็บไว้ {_minutes(keep_for)} นาทีหลังแปลงเสร็จ",
        "แปลงไฟล์ใหม่",
    )


def deleted() -> str:
    return _notice("ลบไฟล์ผลลัพธ์แล้ว", "ไม่มีอะไรของไฟล์นี้เหลืออยู่บนเซิร์ฟเวอร์", "แปลงไฟล์อื่น")


def too_large() -> str:
    """For an upload past the size limit. Unlike the command line's, its message gives no size:
    reading stopped at the limit, before the whole file came."""
    return _notice("แปลงไฟล์นี้ไม่ได้", too_large_unmeasured(MAX_BYTES), "เลือกไฟล์อื่น")


def not_an_upload() -> str:
    return _notice("ไม่ได้รับไฟล์", "กรุณาเลือกไฟล์ PDF หรือ DOCX หนึ่งไฟล์", "กลับไปเลือกไฟล์")


def bot_check_failed() -> str:
    return _notice(
        "ส่งไฟล์ไม่สำเร็จ",
        "ตรวจสอบไม่ได้ว่าไฟล์นี้ส่งมาจากผู้ใช้จริง กรุณากลับไปหน้าแรก รอสักครู่แล้วส่งไฟล์อีกครั้ง",
        "กลับไปหน้าแรก",
    )


def unexpected_error() -> str:
    return _notice("เกิดข้อผิดพลาด", "กรุณาลองใหม่อีกครั้ง", "กลับไปหน้าแรก")


def from_another_site() -> str:
    """For an upload, a cancel or a delete that did not come from one of this site's pages."""
    return _notice(
        "ทำรายการไม่สำเร็จ",
        "คำขอนี้ไม่ได้ส่งมาจากหน้าเว็บของบริการนี้ กรุณากลับไปหน้าแรกแล้วลองใหม่อีกครั้ง",
        "กลับไปหน้าแรก",
    )


def queue_full() -> str:
    return _notice("คิวเต็ม", "กรุณาลองใหม่อีกสักครู่", "กลับไปหน้าแรก")


def already_converting(identifier: str) -> str:
    """For a browser that sends a file while its conversion of another waits or runs."""
    return _notice(
        "มีไฟล์ที่กำลังแปลงอยู่แล้ว",
        "แปลงได้ทีละไฟล์ กรุณารอให้ไฟล์ก่อนหน้าแปลงเสร็จ หรือยกเลิกไฟล์นั้นก่อน",
        "ไปที่ไฟล์ที่กำลังแปลง",
        f"/conversions/{escape(identifier)}",
    )


def _notice(heading: str, message: str, action: str, href: str = "/") -> str:
    """A card that says why nothing more can happen here, and where to go instead."""
    return _page(
        _NAME,
        f"""<section class="card" aria-labelledby="notice-title">
<h1 class="status" id="notice-title">{heading}</h1>
<p class="message">{message}</p>
<div class="actions"><a class="button button--primary" href="{href}">{action}</a></div>
</section>""",
    )


def _minutes(seconds: float) -> int:
    """Whole minutes, rounded up, so that time left never reads as none while some remains."""
    return max(0, math.ceil(seconds / 60))


def _page(title: str, body: str) -> str:
    """A page under the top bar, which carries the name and the one-line claim."""
    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#ffffff">
<title>{escape(title)}</title>
<link rel="preload" href="/static/fonts/Prompt-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/static/fonts/Prompt-SemiBold.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/static/site.css">
<link rel="icon" href="/static/icon.svg" type="image/svg+xml">
</head>
<body>
<header class="topbar">
<div class="topbar-inner">
<a class="wordmark" href="/" aria-label="{_NAME} หน้าแรก">{_NAME}</a>
<p class="topbar-line">แปลง PDF และ DOCX เป็นข้อความไทยที่ตรงต้นฉบับ</p>
</div>
</header>
<main>
{body}
</main>
<script src="/static/app.js" defer></script>
</body>
</html>
"""
