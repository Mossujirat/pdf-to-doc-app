"""The web app's pages, in Thai, with no inline script or style.

Each page has one plain, centred task, as people already know a converter to look. The home
page is a title, one big drop area, the three steps of converting a file, and what the converter
does with it inside, each part beside a picture drawn in HTML. Every other page is one card
in the middle: a conversion's card holds its status, what it is doing now or how it ended, and
what the visitor can do next. A step that changes is tinted for a moment (`static/app.js`).
"""

import math
from html import escape

from pdf_to_doc.intake import MAX_BYTES, MAX_PAGES, PasswordRequired
from pdf_to_doc.model import Placeholder
from pdf_to_doc.refusals import refusal_message, too_large_unmeasured
from pdf_to_doc.validation import MIN_DICTIONARY_SHARE, MIN_WORDS_TO_JUDGE
from pdf_to_doc.web.bot_check import ACTION, SCRIPT
from pdf_to_doc.web.conversions import Conversion
from pdf_to_doc.web.protocol import RefusalEvent

_MB = 1024 * 1024
_NAME = "ครบคำ"
_REPOSITORY = "https://github.com/Mossujirat/pdf-to-doc-app"  # the source code, public under the AGPL (ADR 0002)
_ISSUES = f"{_REPOSITORY}/issues"  # where problems are reported
# Who runs the service, as the privacy page names them for the PDPA.
_OPERATOR = "Sujirat Attawibulkul"
_CONTACT = "sujirat.attawibulkul@gmail.com"

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
    """The title; the drop area, which is the upload form, with the bot check's widget, whose
    token goes with the file; the three steps of converting a file; and what the converter does
    with it inside. Without a site key there is no widget, and every upload is refused."""
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
<h2 class="part-title" id="how-title">แปลงอย่างไร</h2>
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
</section>
{_inside(kept)}{script}""",
    )


def _inside(kept: int) -> str:
    """What the converter does with a file, step by step, each beside a picture drawn in HTML.
    Every fact here is the converter's as it is, and its numbers come from the code that applies
    them: a change to a rule shown here changes this section in the same ticket. The examples
    are made up, never taken from a real document."""
    share = f"{MIN_DICTIONARY_SHARE:.0%}"
    checks = _ticked(
        [
            "เป็น PDF หรือ DOCX จริง ดูจากเนื้อในไฟล์",
            f"ไม่เกิน {MAX_BYTES // _MB}&nbsp;MB",
            f"ไม่เกิน {MAX_PAGES}&nbsp;หน้า",
            "ไม่ได้ล็อกด้วยรหัสผ่าน และไม่ได้ห้ามคัดลอกข้อความ",
        ]
    )
    return f"""<section class="inside" aria-labelledby="inside-title">
<div class="inside-head">
<h2 class="part-title" id="inside-title">ข้างในทำอะไรกับไฟล์ของคุณ</h2>
<p class="inside-intro">ทุกข้อด้านล่างคือสิ่งที่ตัวแปลงทำจริง ตัวอย่างทั้งหมดเป็นข้อความที่แต่งขึ้น ไม่ได้มาจากเอกสารของใคร</p>
</div>

<div class="inside-row">
<div class="inside-text">
<h3>ตรวจไฟล์ก่อนแปลง</h3>
<p>ชนิดของไฟล์ดูจากเนื้อในไฟล์ ไม่ได้ดูจากนามสกุล แล้วจึงตรวจขนาดและจำนวนหน้า
ไฟล์ Word รุ่นเก่า (.doc) ไฟล์ที่ล็อกด้วยรหัสผ่าน และ PDF ที่ห้ามคัดลอกข้อความ จะไม่ถูกแปลง และหน้าเว็บจะบอกเหตุผล</p>
</div>
<figure class="picture">
<div class="sheet-card">
<p class="file">{_FILE}<span class="file-name">สัญญาจ้าง-ตัวอย่าง.pdf</span></p>
<ul class="checks">
{checks}
</ul>
</div>
<figcaption class="visually-hidden">ตัวอย่างการตรวจไฟล์ PDF หนึ่งไฟล์ ผ่านทุกข้อ</figcaption>
</figure>
</div>

<div class="inside-row">
<div class="inside-text">
<h3>อ่านทีละหน้า ด้วยวิธีที่เหมาะกับหน้านั้น</h3>
<p>หน้าที่มีข้อความเก็บอยู่ในไฟล์และเชื่อถือได้ อ่านจากข้อความนั้นโดยตรง จึงได้ตัวอักษรตรงตามที่พิมพ์ไว้</p>
<p>หน้าที่ไม่มีข้อความให้อ่าน เช่น หน้าสแกน หรือตัวอักษรที่ถูกวาดเป็นเส้น และหน้าที่ข้อความในไฟล์ผิด
อ่านด้วย OCR คือให้โปรแกรมอ่านตัวอักษรจากภาพของหน้า ซึ่งช้ากว่า</p>
</div>
<figure class="picture">
<div class="sheets">
{_sheet("มีข้อความในไฟล์", "อ่านตรง")}
{_sheet("หน้าสแกน", "OCR", scan=True)}
{_sheet("ข้อความในไฟล์ผิด", "OCR", word="กำร")}
</div>
<figcaption class="visually-hidden">สามหน้า: หน้าที่มีข้อความในไฟล์อ่านตรง หน้าสแกนและหน้าที่ข้อความในไฟล์ผิดอ่านด้วย OCR</figcaption>
</figure>
</div>

<div class="inside-row">
<div class="inside-text">
<h3>จับข้อความในไฟล์ที่ผิด</h3>
<p>บางไฟล์เก็บข้อความไว้ผิด ทั้งที่หน้ากระดาษแสดงถูก เช่น ฟอนต์บางตัวทำให้คำว่า การ ถูกเก็บเป็น กำร
ตัวแปลงจึงตรวจข้อความของทุกหน้าก่อนใช้ หน้าที่เข้าข่ายข้อใดข้อหนึ่งจะถูกอ่านใหม่ด้วย OCR</p>
<ul class="points">
<li>มีตัวอักษรที่อ่านไม่ได้ คือตัวที่ฟอนต์ไม่ได้บอกว่าเป็นตัวอะไร</li>
<li>มีสระอำอยู่ผิดที่ เช่น ไม่ได้ตามหลังพยัญชนะหรือวรรณยุกต์</li>
<li>หน้าที่มีคำไทยอย่างน้อย {MIN_WORDS_TO_JUDGE} คำ แต่เป็นคำที่มีในพจนานุกรมไม่ถึง {share}</li>
</ul>
</div>
<figure class="picture">
<figcaption class="example-label">ตัวอย่าง: ข้อความที่ซ่อนอยู่ในไฟล์ผิด</figcaption>
<div class="example-row">
<p class="example-word example-word--wrong"><span>ในไฟล์เขียนว่า</span><strong>กำร</strong></p>
<span class="example-arrow">{_ARROW}<span class="visually-hidden">แก้เป็น</span></span>
<p class="example-word example-word--right"><span>{_NAME}ได้</span><strong>การ</strong></p>
</div>
<p class="example-note">หน้ากระดาษแสดงคำว่า การ แต่ข้อความในไฟล์เขียนว่า กำร ทั้งหน้า คำที่มีในพจนานุกรมจึงไม่ถึง {share}
หน้านั้นถูกอ่านใหม่ด้วย OCR และส่วนที่ยังไม่แน่ใจจะถูกทำเครื่องหมายไว้ให้ตรวจ</p>
</figure>
</div>

<div class="inside-row">
<div class="inside-text">
<h3>ซ่อมข้อความไทย</h3>
<p>แม้ข้อความในไฟล์จะเชื่อถือได้ ก็ยังมีจุดเล็กๆ ที่ทำให้คัดลอกหรือค้นหาคำไม่เจอ ตัวแปลงแก้ให้ทุกครั้ง
โดยไม่ลบตัวอักษรที่มองเห็นได้สักตัว</p>
<ul class="points">
<li>เรียงสระและวรรณยุกต์ให้อยู่ในลำดับมาตรฐาน</li>
<li>รวมสระอำที่ถูกเก็บแยกเป็นสองตัวให้เป็นตัวเดียว</li>
<li>แปลงตัวอักษรพิเศษของฟอนต์ไทยรุ่นเก่ากลับเป็นอักษรไทยปกติ</li>
<li>ลบตัวอักษรที่มองไม่เห็น และช่องว่างที่แทรกอยู่หน้าสระบน สระล่าง หรือวรรณยุกต์</li>
<li>ต่อบรรทัดที่ถูกตัดตามความกว้างกระดาษกลับเป็นย่อหน้าเดียว โดยไม่เติมช่องว่างตรงรอยต่อระหว่างอักษรไทย</li>
</ul>
</div>
<figure class="picture">
<div class="before-after">
<div class="before">
<p class="example-label">ในไฟล์ สองบรรทัด</p>
<p class="before-lines"><span>ตกลงจ้างที &#x0E48;ปรึกษา</span><span>เพื่อให้คำแนะนำ</span></p>
</div>
<span class="example-arrow">{_ARROW}<span class="visually-hidden">ซ่อมเป็น</span></span>
<div class="after">
<p class="example-label">ผลลัพธ์ ย่อหน้าเดียว</p>
<p>ตกลงจ้างที่ปรึกษาเพื่อให้คำแนะนำ</p>
</div>
</div>
<figcaption class="example-note">ช่องว่างหน้าไม้เอกถูกลบ และสองบรรทัดต่อกันโดยไม่มีช่องว่างกลางประโยค</figcaption>
</figure>
</div>

<div class="inside-row">
<div class="inside-text">
<h3>เก็บโครงสร้าง และไม่เดาสิ่งที่อ่านไม่ได้</h3>
<p>หัวข้อและรายการ ยังเป็นหัวข้อและรายการ ตารางใน DOCX และตารางที่มีเส้นตารางใน PDF ยังเป็นตาราง
ส่วนหน้าที่อ่านด้วย OCR ยังไม่แยกหัวข้อและตาราง ข้อความที่ซ้ำกันที่ขอบบนหรือขอบล่างของหลายหน้า
เช่น หัวกระดาษและเลขหน้า ถูกตัดออก</p>
<p>ในหน้าที่มีข้อความในไฟล์ รูปภาพ ลายเซ็น และตราประทับที่ฝังอยู่ ถูกแทนด้วยป้าย เช่น <span class="nowrap">[ลายเซ็น]</span>
ไม่มีการเดาเป็นข้อความ ส่วนหน้าที่อ่านด้วย OCR ไม่มีป้ายเหล่านี้ และสิ่งที่ OCR อ่านได้ไม่ชัด เช่น ลายมือหรือรอยเปื้อน
ถูกทำเครื่องหมายว่าไม่แน่ใจ</p>
</div>
<figure class="picture">
<div class="sheet-card doc">
<p class="doc-cut"><s>หน้าที่ 2/7</s> <span class="chip">ตัดออก</span></p>
<p class="doc-heading">ข้อ 3 ค่าจ้างและการชำระเงิน</p>
<ol class="doc-list">
<li>ค่าจ้างเดือนละ 30,000 บาท</li>
<li>ชำระภายในวันที่ 5 ของเดือนถัดไป</li>
</ol>
<p class="doc-placeholders"><span class="chip">[ลายเซ็น]</span><span class="chip">[ตราประทับ]</span></p>
</div>
<figcaption class="visually-hidden">ตัวอย่างหน้าเอกสาร: เลขหน้าถูกตัดออก หัวข้อและรายการยังอยู่ ลายเซ็นและตราประทับกลายเป็นป้าย</figcaption>
</figure>
</div>

<div class="inside-row">
<div class="inside-text">
<h3>เอกสารเดียว ได้สองไฟล์</h3>
<p>ทุกหน้าถูกรวมเป็นเอกสารเดียวก่อน แล้วจึงเขียนออกเป็น Markdown สำหรับวางในแชต AI และ DOCX สำหรับแก้ใน Word
ทั้งสองไฟล์จึงมีเนื้อหาเดียวกัน และบอกส่วนที่ไม่แน่ใจไว้ทั้งคู่ ไฟล์ DOCX ที่ส่งมาได้ Markdown อย่างเดียว</p>
</div>
<figure class="picture">
<div class="outputs">
<div class="output">
<p class="example-label">Markdown</p>
<p><code>ส่งงานภายใน &lt;mark&gt;เจ็ดวัน&lt;/mark&gt;</code></p>
</div>
<div class="output">
<p class="example-label">DOCX</p>
<p>ส่งงานภายใน <mark>เจ็ดวัน</mark></p>
</div>
</div>
<figcaption class="example-note">คำที่ OCR อ่านได้ไม่แน่ใจ ถูกครอบด้วย &lt;mark&gt; ใน Markdown และไฮไลต์สีเหลืองใน DOCX</figcaption>
</figure>
</div>

<div class="inside-row">
<div class="inside-text">
<h3>ไฟล์ของคุณไปที่ไหน</h3>
<p>ไฟล์ถูกเข้ารหัสตลอดทางจนถึงเซิร์ฟเวอร์ของเราเอง และแปลงในกล่องที่สร้างใหม่สำหรับไฟล์นี้ ซึ่งไม่มีอินเทอร์เน็ต
ผลลัพธ์เปิดได้เฉพาะเบราว์เซอร์ที่ส่งไฟล์</p>
<p>บันทึกการทำงานของระบบไม่มีเนื้อหา ชื่อไฟล์ หรือลิงก์</p>
</div>
<figure class="picture">
<ol class="route">
<li><strong>เบราว์เซอร์ของคุณ</strong><span>ส่งไฟล์แบบเข้ารหัส</span></li>
<li><strong>เซิร์ฟเวอร์ของเรา</strong><span>ไม่ส่งต่อให้บริการอื่น</span></li>
<li><strong>กล่องแปลงไฟล์</strong><span>ไม่มีอินเทอร์เน็ต ถูกทิ้งเมื่อแปลงเสร็จ</span></li>
<li><strong>ลบ</strong><span>ต้นฉบับทันทีที่แปลงเสร็จ ผลลัพธ์ภายใน {kept}&nbsp;นาที หรือเมื่อคุณกดลบ</span></li>
</ol>
<figcaption class="visually-hidden">เส้นทางของไฟล์ จากเบราว์เซอร์ ถึงเซิร์ฟเวอร์ เข้ากล่องแปลงไฟล์ แล้วถูกลบ</figcaption>
</figure>
</div>
</section>"""


def _sheet(caption: str, read: str, *, scan: bool = False, word: str = "") -> str:
    """A page in miniature, grey bars for its lines, with how it is read. `word`, if any, takes
    the second line's place, as the one word the picture is about."""
    second = f'<span class="sheet-word">{word}</span>' if word else '<span class="sheet-line"></span>'
    lines = f'<span class="sheet-line"></span>{second}<span class="sheet-line sheet-line--short"></span><span class="sheet-line"></span>'
    return f"""<div class="sheet-item">
<div class="sheet{" sheet--scan" if scan else ""}" aria-hidden="true">{lines}</div>
<p>{caption}</p>
<span class="chip">{read}</span>
</div>"""


def _ticked(items: list[str]) -> str:
    """List items, each led by a tick. The items are HTML already escaped."""
    return "\n".join(f"<li>{_TICK}<span>{item}</span></li>" for item in items)


def code_at(commit: str | None) -> str:
    """The repository's source code at the commit, or, for a build that names none, on a
    developer's machine, the repository itself."""
    return f"{_REPOSITORY}/tree/{commit}" if commit else _REPOSITORY


def privacy(keep_for: float, pages_per_day: int, cookie: str, cookie_lasts: float) -> str:
    """The privacy policy, for the PDPA: who runs the service and how to reach them, what it
    receives, what becomes of it and when, what it never keeps, its one cookie, named `cookie`
    and kept `cookie_lasts` seconds, what Cloudflare's bot check sees, and the visitor's rights.
    Every fact is the service's as it is."""
    kept = _minutes(keep_for)
    issues = f'<a href="{_ISSUES}">GitHub Issues</a>'
    return _page(
        f"นโยบายความเป็นส่วนตัว {_NAME}",
        f"""<article class="card prose" aria-labelledby="privacy-title">
<h1 class="status" id="privacy-title">นโยบายความเป็นส่วนตัว</h1>
<p class="message">หน้านี้บอกว่า{_NAME}ทำอะไรกับไฟล์และข้อมูลของคุณ ใครเป็นผู้ดูแล และติดต่อได้อย่างไร
ตามพระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)</p>

<h2>ผู้ให้บริการและการติดต่อ</h2>
<p>{_NAME}ดำเนินการโดย {_OPERATOR} ในฐานะบุคคลธรรมดา ซึ่งเป็นผู้ควบคุมข้อมูลส่วนบุคคลของบริการนี้</p>
<ul class="points">
<li>เรื่องข้อมูลส่วนบุคคล ติดต่อ <a href="mailto:{_CONTACT}">{_CONTACT}</a></li>
<li>ปัญหาการใช้งานหรือข้อผิดพลาด แจ้งได้ที่ {issues}</li>
</ul>

<h2>ข้อมูลที่ได้รับ</h2>
<ul class="points">
<li>ไฟล์ที่คุณส่ง และชื่อไฟล์ ซึ่งใช้แสดงบนหน้าของการแปลงและตั้งชื่อไฟล์ดาวน์โหลด</li>
<li>ที่อยู่ IP ของคุณ ใช้นับจำนวนหน้าที่แปลงได้ต่อวัน วันละ {pages_per_day}&nbsp;หน้า</li>
<li>คุกกี้หนึ่งตัว ซึ่งบอกว่าการแปลงใดเป็นของเบราว์เซอร์นี้</li>
<li>ผลการตรวจว่าเป็นคนจริงจาก Cloudflare Turnstile</li>
</ul>

<h2>ไฟล์ของคุณไปที่ไหนและถูกลบเมื่อไร</h2>
<ul class="points">
<li>ไฟล์ถูกเข้ารหัสตั้งแต่เบราว์เซอร์จนถึงเซิร์ฟเวอร์ของเราเอง ระหว่างทางผ่านตัวส่งต่อของ Tailscale
ซึ่งเห็นที่อยู่ IP ของคุณเพื่อส่งต่อการเชื่อมต่อ แต่อ่านเนื้อหาไม่ได้ ไม่มีบริการอื่นได้เห็นเนื้อหา</li>
<li>ไฟล์ถูกแปลงในกล่องที่สร้างใหม่สำหรับไฟล์นี้ ซึ่งไม่มีอินเทอร์เน็ต และถูกทิ้งเมื่อแปลงเสร็จ
ไม่มีการส่งไฟล์ให้บริการ AI หรือบริการอื่นใด</li>
<li>ไฟล์ต้นฉบับถูกลบทันทีที่การแปลงจบ ไม่ว่าจะแปลงสำเร็จหรือไม่</li>
<li>ผลลัพธ์และชื่อไฟล์อยู่ในหน่วยความจำ เปิดได้เฉพาะเบราว์เซอร์ที่ส่งไฟล์ และถูกลบภายใน {kept}&nbsp;นาทีหลังการแปลงจบ
หรือทันทีที่คุณกด "ลบเดี๋ยวนี้"</li>
<li>เมื่อระบบเริ่มทำงานใหม่ ทุกอย่างที่อยู่ในหน่วยความจำจะหายไปทั้งหมด</li>
</ul>

<h2>สิ่งที่ไม่เก็บ</h2>
<ul class="points">
<li>บันทึกการทำงานของระบบไม่มีเนื้อหา ชื่อไฟล์ ที่อยู่ IP หรือลิงก์ของการแปลง</li>
<li>ที่อยู่ IP อยู่ในหน่วยความจำเท่านั้น เพื่อนับจำนวนหน้าของวันนั้น และถูกล้างภายในไม่กี่วินาทีหลังเที่ยงคืนตามเวลาประเทศไทย
หรือเมื่อระบบเริ่มทำงานใหม่</li>
<li>ตัวเลขรวมของบริการ เช่น จำนวนการแปลงและจำนวนหน้า ไม่มีข้อมูลที่บอกได้ว่าเป็นใคร</li>
<li>ไม่มีระบบวิเคราะห์การใช้งาน ไม่มีโฆษณา และไม่มีตัวติดตาม</li>
</ul>

<h2>คุกกี้</h2>
<p>เว็บนี้ตั้งคุกกี้ของตัวเองเพียงตัวเดียว ชื่อ {cookie} เพื่อจำว่าการแปลงใดเป็นของเบราว์เซอร์นี้
ซึ่งจำเป็นต่อการทำงาน หมดอายุใน {_hours(cookie_lasts)}&nbsp;ชั่วโมง และไม่ได้ใช้ติดตามหรือโฆษณา</p>

<h2>การตรวจว่าเป็นคนจริง</h2>
<p>หน้าแรกโหลดสคริปต์ของ Cloudflare Turnstile เพื่อกันโปรแกรมอัตโนมัติ Cloudflare จึงได้รับข้อมูลของเบราว์เซอร์
เช่น ที่อยู่ IP, User-Agent, ลักษณะการเชื่อมต่อ TLS และเว็บไซต์ที่ใช้ เพื่อตรวจและพัฒนาการตรวจโปรแกรมอัตโนมัติ</p>
<p>ตามเอกสารของ Cloudflare, Turnstile ไม่เข้าถึง ไม่เก็บ และไม่ส่งต่อสิ่งที่กรอกในหน้าเว็บ และ{_NAME}ไม่ส่งไฟล์ของคุณให้ Cloudflare
ฝั่งเซิร์ฟเวอร์ส่งไปถามเพียงผลการตรวจเท่านั้น
อ่านเพิ่มได้ที่ <a href="https://www.cloudflare.com/turnstile-privacy-policy/">Turnstile Privacy Addendum</a></p>

<h2>สิทธิของคุณ</h2>
<p>ตาม PDPA คุณมีสิทธิขอเข้าถึงและขอสำเนาข้อมูลของคุณ ขอให้แก้ไข ขอให้ลบ ขอให้ระงับการใช้ คัดค้านการใช้
และขอให้โอนย้ายข้อมูล ใช้สิทธิได้โดยส่งอีเมลถึง <a href="mailto:{_CONTACT}">{_CONTACT}</a></p>
<p>เนื่องจากไฟล์และผลลัพธ์ถูกลบภายใน {kept}&nbsp;นาที และที่อยู่ IP อยู่ในหน่วยความจำเท่านั้น
ส่วนใหญ่จึงไม่มีข้อมูลของคุณเหลืออยู่ให้ขอ คุณลบผลลัพธ์ได้เองทันทีด้วยปุ่ม "ลบเดี๋ยวนี้"</p>
<p>หากเห็นว่าข้อมูลของคุณถูกใช้ไม่ถูกต้อง ร้องเรียนได้ที่
<a href="https://www.pdpc.or.th/">สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล (สคส.)</a></p>

<h2>ซอร์สโค้ด</h2>
<p>ซอร์สโค้ดของ{_NAME}เปิดเผยภายใต้สัญญาอนุญาต AGPL-3.0 ใครก็ตรวจได้ว่าบริการทำตามที่หน้านี้บอก
ลิงก์ <a href="/source-code">ซอร์สโค้ด</a> ท้ายทุกหน้าพาไปยังโค้ดรุ่นที่เซิร์ฟเวอร์ใช้อยู่</p>

<p class="summary">ปรับปรุงล่าสุด 22 ตุลาคม 2569</p>
<div class="actions"><a class="button button--primary" href="/">กลับไปแปลงไฟล์</a></div>
</article>""",
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
    return f"""<h2 class="section-title">ไฟล์นี้เป็นอย่างไรแล้ว</h2>
<ul class="facts">
{_ticked(facts)}
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


def _hours(seconds: float) -> int:
    """Whole hours, rounded up."""
    return max(0, math.ceil(seconds / 3600))


def _page(title: str, body: str) -> str:
    """A page under the top bar, which carries the name and the one-line claim, and over the
    footer, which links to the privacy page, to the source the server runs (AGPL), and to where
    problems are reported."""
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
<footer class="footer">
<div class="footer-inner">
<p>{_NAME} · ซอร์สโค้ดเปิดเผยภายใต้ AGPL-3.0</p>
<ul class="footer-links">
<li><a href="/privacy">นโยบายความเป็นส่วนตัว</a></li>
<li><a href="/source-code">ซอร์สโค้ด</a></li>
<li><a href="{_ISSUES}">แจ้งปัญหา</a></li>
</ul>
</div>
</footer>
<script src="/static/app.js" defer></script>
</body>
</html>
"""
