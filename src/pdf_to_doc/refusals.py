"""The Thai message for each refused source file: one table, for the command line and the web.

A refusal whose advice depends on where the file was sent, such as how to give a password,
has no message here: each front end words its own.
"""

import math

from pdf_to_doc.intake import (
    CopyRestricted,
    DamagedFile,
    IntakeError,
    TooLarge,
    UnsupportedFormat,
    WrongPassword,
)

_MB = 1024 * 1024


def refusal_message(error: IntakeError) -> str | None:
    """The message for the refusal, or None for one each front end words for itself:
    a PDF that needs a password, and a DOCX asked to become a DOCX."""
    match error:
        case UnsupportedFormat(found="doc"):
            return "ไฟล์นี้เป็น Word รุ่นเก่า (.doc) ซึ่งแปลงไม่ได้ กรุณาเปิดใน Word แล้วบันทึกเป็น .docx ก่อน"
        case UnsupportedFormat(found="locked office"):
            return (
                "ไฟล์ Office นี้ล็อกด้วยรหัสผ่าน จึงแปลงไม่ได้ ถ้าเป็นไฟล์ Word"
                " กรุณาเปิดใน Word แล้วบันทึกใหม่โดยไม่ตั้งรหัสผ่าน"
            )
        case UnsupportedFormat():
            return "ไฟล์นี้ไม่ใช่ PDF หรือ DOCX จึงแปลงไม่ได้"
        case TooLarge(unit="bytes", size=size, limit=limit):
            return f"ไฟล์นี้ใหญ่ {_megabytes(size)} MB เกินขนาดสูงสุดที่แปลงได้ {limit // _MB} MB"
        case TooLarge(unit="unpacked bytes", size=size, limit=limit):
            return f"ไฟล์ DOCX นี้เมื่อแตกออกมาใหญ่ {_megabytes(size)} MB เกินขนาดสูงสุดที่แปลงได้ {limit // _MB} MB"
        case TooLarge(unit="pages", size=size, limit=limit):
            return f"ไฟล์นี้มี {size} หน้า เกินจำนวนสูงสุดที่แปลงได้ {limit} หน้า กรุณาแบ่งไฟล์แล้วแปลงทีละส่วน"
        case WrongPassword():
            return "รหัสผ่านไม่ถูกต้อง เปิดไฟล์ PDF นี้ไม่ได้"
        case CopyRestricted():
            return "ไฟล์ PDF นี้ตั้งสิทธิ์ห้ามคัดลอกข้อความ ผู้สร้างเอกสารไม่อนุญาตให้นำข้อความออกไปใช้ จึงไม่แปลงไฟล์นี้"
        case DamagedFile():
            return "ไฟล์เสียหรือไม่สมบูรณ์ จึงเปิดอ่านไม่ได้ ลองดาวน์โหลดหรือคัดลอกไฟล์มาใหม่"
    return None


def too_large_unmeasured(limit: int) -> str:
    """The message for a file refused as over `limit` bytes before its whole size was known, as
    when an upload stops being read at the limit."""
    return f"ไฟล์นี้ใหญ่เกินขนาดสูงสุดที่แปลงได้ {limit // _MB} MB"


def _megabytes(size: int) -> str:
    """A size in megabytes to one decimal place, rounded up, so a file just over a limit never shows as the limit."""
    return f"{math.ceil(size * 10 / _MB) / 10:.1f}"
