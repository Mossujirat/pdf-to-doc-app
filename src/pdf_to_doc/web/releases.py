"""The what's-new page's content: what each release gave visitors, and the known limitations as
they are now (GLOSSARY.md, "Web service"). It is plain Thai for readers with no technical
background: no ticket or PR numbers, and no word such as OCR or DOCX where a plain one serves.

A release's entry is written before it goes to staging, dated the day it goes to production; the
operator approves its wording. A deploy visitors cannot tell apart from the one before gets none.
The release that closes the ticket behind a known limitation drops the limitation and lists the
fix among its improvements.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Release:
    went_live: date  # the day, in Bangkok, it reached production
    improvements: tuple[str, ...]


@dataclass(frozen=True)
class KnownLimitation:
    text: str
    tickets: tuple[str, ...]  # the open tickets behind it, as paths under .scratch/


# Newest first.
RELEASES = (
    Release(
        date(2026, 11, 2),
        ('เพิ่มหน้า "มีอะไรใหม่" ลิงก์อยู่ท้ายทุกหน้า บอกว่าแต่ละรอบปรับอะไร และข้อจำกัดที่ควรรู้ก่อนนำไปใช้',),
    ),
    Release(
        date(2026, 10, 31),
        (
            "หน้าสแกนที่หมุน ตะแคง หรือกลับหัว อ่านได้ถูกแล้ว ไม่ต้องหมุนไฟล์เองก่อนส่ง",
            "เอกสารที่แบ่งเป็นสองคอลัมน์ อ่านจบทีละฝั่ง ข้อความสองฝั่งไม่ปนกันแล้ว",
            "ตารางที่มีเส้นตีช่องในหน้าสแกน ออกมาเป็นตาราง ถ้าตารางไหนอ่านได้ไม่ครบ จะมีป้ายบอกให้ตรวจ",
            'เลือก "เก็บหน้าสแกนเป็นภาพ" ได้ ไฟล์ Word จะแสดงหน้าสแกนและรูปภาพเหมือนต้นฉบับ รวมถึงลายเซ็น และรอยไฮไลต์บนหน้าสแกน',
            "สีเหลืองที่บอกจุดที่ไม่แน่ใจ ตอนนี้บอกตัวเลขหรือจำนวนเงินที่มีตัวอักษรปน เช่น 12,ooo.oo ด้วย และขึ้นบนคำไทยที่ถูกอยู่แล้วน้อยลง",
            "ข้อความที่ถูกลายน้ำทับหายน้อยลง และเลขข้อที่ตกไปขึ้นบรรทัดใหม่ไม่กลายเป็นข้อใหม่อีก",
        ),
    ),
    Release(date(2026, 10, 22), ("เปิดให้ใช้งานครั้งแรก",)),
)

KNOWN_LIMITATIONS = (
    KnownLimitation(
        'รอยไฮไลต์ไม่ติดมาในข้อความ และโน้ตที่แปะไว้ใน PDF บางไฟล์ก็หายไป ถ้าเป็นเอกสารสแกน เลือก "เก็บหน้าสแกนเป็นภาพ" แล้วจะเห็นรอยเหล่านี้ในไฟล์ Word',
        (
            "converter-engine/issues/20-highlights-and-notes-on-text-pages.md",
            "converter-engine/issues/36-highlights-and-notes-on-scans-read-with-ocr.md",
        ),
    ),
    KnownLimitation(
        'ลายเซ็น ตราประทับ และรูปภาพบนหน้าสแกน ไม่มีป้ายบอกในข้อความ จึงดูไม่ออกว่าเอกสารลงนามแล้ว ถ้าต้องการเห็น เลือก "เก็บหน้าสแกนเป็นภาพ"',
        (
            "converter-engine/issues/24-pictures-on-ocr-pages-that-are-not-scans.md",
            "converter-engine/issues/38-pictures-inside-scans.md",
        ),
    ),
    KnownLimitation(
        "เลขหน้า หัวกระดาษ และท้ายกระดาษของหน้าสแกนยังติดมาในเนื้อหา ลบออกเองก่อนใช้",
        ("converter-engine/issues/22-page-furniture-on-scans.md",),
    ),
    KnownLimitation(
        "เครื่องหมายติ๊กในช่องบนหน้าสแกนหายไป จึงไม่รู้ว่าเลือกข้อไหนไว้ ดูจากต้นฉบับ",
        ("converter-engine/issues/26-ticked-boxes-are-lost.md",),
    ),
    KnownLimitation(
        "ลายเซ็นหลายชุดที่วางเรียงกัน หรือแถบข้อความข้างจดหมาย บนหน้าสแกน ถูกอ่านปนกับข้อความข้างๆ ชื่อกับตำแหน่งของผู้ลงนามอาจจับคู่ผิด",
        ("converter-engine/issues/32-short-line-columns-on-ocr-pages.md",),
    ),
    KnownLimitation(
        "ข้อความที่เขียนเฉียงบนหน้าสแกน เช่น ตัวลายน้ำเอง หรือข้อความที่เขียนคร่อมสำเนาบัตรประชาชน ไม่ถูกอ่าน",
        ("converter-engine/issues/34-diagonal-text-on-scans.md",),
    ),
    KnownLimitation(
        'คำไทยในหน้าสแกนที่อ่านผิดแต่บังเอิญเป็นคำที่มีจริง เช่น "ที" แทน "ที่" ไม่มีสีเหลืองบอก',
        ("converter-engine/issues/35-thai-misreads-that-are-real-words.md",),
    ),
    KnownLimitation(
        "ตัวเลขในหน้าสแกนที่อ่านผิดเป็นตัวเลขอื่นแต่ยังดูเป็นตัวเลขปกติ เช่น จำนวนเงินที่หลักเกินแต่จุลภาคยังอยู่ถูกที่"
        " หรือวันที่ที่กลายเป็นอีกวันหนึ่ง ไม่มีสีเหลืองบอก ตรวจจำนวนเงินและวันที่กับต้นฉบับเสมอ",
        ("converter-engine/issues/40-number-misreads-left-after-37.md",),
    ),
    KnownLimitation(
        "ตารางที่ตีเส้นเฉพาะช่องตัวเลข เช่น ตารางงบประมาณ ชื่อรายการจะแยกออกมาอยู่นอกตาราง ต้องจับคู่กับแถวเอง",
        ("tables-on-ocr-pages/issues/10-row-labels-beside-a-ruled-table.md",),
    ),
)
