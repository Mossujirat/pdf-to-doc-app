"""Command-line wrapper around the conversion function."""

import argparse
import math
import sys
from pathlib import Path

from pdf_to_doc.console import thai_safe_output
from pdf_to_doc.conversion import convert
from pdf_to_doc.intake import (
    MAX_BYTES,
    MAX_PAGES,
    CopyRestricted,
    DamagedFile,
    IntakeError,
    PasswordRequired,
    TooLarge,
    UnsupportedFormat,
    WrongPassword,
)
from pdf_to_doc.ocr_models import ModelsMissing
from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.reading import Progress

EXIT_OK = 0
# Exit code 1 is Python's for a crash, and 2 is argparse's for bad arguments.
EXIT_UNSUPPORTED_FORMAT = 3
EXIT_TOO_LARGE = 4
EXIT_PASSWORD_REQUIRED = 5
EXIT_WRONG_PASSWORD = 6
EXIT_COPY_RESTRICTED = 7
EXIT_DAMAGED_FILE = 8
EXIT_MODELS_MISSING = 9

_MB = 1024 * 1024
_LINE_START = chr(13)  # a carriage return: the next print overwrites the line

_EXIT_CODES = f"""\
exit code:
  {EXIT_OK}  แปลงสำเร็จ
  {EXIT_UNSUPPORTED_FORMAT}  ไม่ใช่ไฟล์ที่แปลงได้ (เช่น Word รุ่นเก่า .doc)
  {EXIT_TOO_LARGE}  ไฟล์ใหญ่เกิน {MAX_BYTES // _MB} MB หรือเกิน {MAX_PAGES} หน้า
  {EXIT_PASSWORD_REQUIRED}  PDF ล็อกด้วยรหัสผ่าน แต่ไม่ได้ใส่ --password
  {EXIT_WRONG_PASSWORD}  รหัสผ่านไม่ถูกต้อง
  {EXIT_COPY_RESTRICTED}  PDF ตั้งสิทธิ์ห้ามคัดลอกข้อความ
  {EXIT_DAMAGED_FILE}  ไฟล์เสียหรือไม่สมบูรณ์
  {EXIT_MODELS_MISSING}  ยังไม่ได้ติดตั้ง model สำหรับ OCR (สั่ง pdf-to-doc-models)"""


def main(argv: list[str] | None = None, *, ocr: OcrEngine | None = None) -> int:
    """Run the command. `ocr` replaces the default OCR engine, for tests."""
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc",
        description="แปลง PDF เป็น Markdown ที่ข้อความไทยอ่านได้ตรงกับต้นฉบับ",
        epilog=_EXIT_CODES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="ไฟล์ PDF ต้นฉบับ")
    parser.add_argument(
        "-o", "--output", type=Path, help="ไฟล์ผลลัพธ์ (ค่าเริ่มต้น: ชื่อเดียวกับต้นฉบับ นามสกุล .md)"
    )
    parser.add_argument("--password", help="รหัสผ่านสำหรับเปิดไฟล์ PDF ที่ล็อกไว้")
    args = parser.parse_args(argv)

    thai_safe_output()

    output_path: Path = args.output or args.source.with_suffix(".md")
    try:
        source = args.source.read_bytes()
    except OSError as error:
        parser.error(f"อ่านไฟล์ {args.source} ไม่ได้ ({error.strerror})")
    try:
        result = convert(source, to="markdown", password=args.password, ocr=ocr, progress=_show_progress)
    except IntakeError as error:
        exit_code, message = _refusal(error)
        print(f"{args.source}: {message}", file=sys.stderr)
        return exit_code
    except ModelsMissing as error:
        print(
            f"ยังไม่ได้ติดตั้ง model สำหรับ OCR ที่ {error.folder} กรุณาสั่ง pdf-to-doc-models ก่อน",
            file=sys.stderr,
        )
        return EXIT_MODELS_MISSING
    output_path.write_bytes(result.output)

    print(f"{output_path}: {result.summary.headline()}")
    return EXIT_OK


def _show_progress(update: Progress) -> None:
    """One line per page; on a terminal, each page overwrites the last."""
    overwrite = sys.stderr.isatty() and update.current < update.total
    line = f"OCR หน้า {update.current}/{update.total}"
    print(line, end=_LINE_START if overwrite else None, file=sys.stderr, flush=True)


def _refusal(error: IntakeError) -> tuple[int, str]:
    """The exit code and the Thai message for a source file that was refused."""
    match error:
        case UnsupportedFormat(found="doc"):
            return EXIT_UNSUPPORTED_FORMAT, (
                "ไฟล์นี้เป็น Word รุ่นเก่า (.doc) ซึ่งแปลงไม่ได้ กรุณาเปิดใน Word แล้วบันทึกเป็น .docx ก่อน"
            )
        case UnsupportedFormat(found="docx"):
            return EXIT_UNSUPPORTED_FORMAT, "ยังแปลงไฟล์ DOCX ไม่ได้ในรุ่นนี้ ตอนนี้แปลงได้เฉพาะ PDF"
        case UnsupportedFormat():
            return EXIT_UNSUPPORTED_FORMAT, "ไฟล์นี้ไม่ใช่ PDF หรือ DOCX จึงแปลงไม่ได้"
        case TooLarge(unit="bytes", size=size, limit=limit):
            # Rounded up, so a file just over the limit never shows as the limit itself.
            megabytes = math.ceil(size * 10 / _MB) / 10
            return EXIT_TOO_LARGE, f"ไฟล์นี้ใหญ่ {megabytes:.1f} MB เกินขนาดสูงสุดที่แปลงได้ {limit // _MB} MB"
        case TooLarge(unit="pages", size=size, limit=limit):
            return EXIT_TOO_LARGE, (
                f"ไฟล์นี้มี {size} หน้า เกินจำนวนสูงสุดที่แปลงได้ {limit} หน้า กรุณาแบ่งไฟล์แล้วแปลงทีละส่วน"
            )
        case PasswordRequired():
            return EXIT_PASSWORD_REQUIRED, "ไฟล์ PDF นี้ล็อกด้วยรหัสผ่าน กรุณาใส่รหัสผ่านด้วย --password"
        case WrongPassword():
            return EXIT_WRONG_PASSWORD, "รหัสผ่านไม่ถูกต้อง เปิดไฟล์ PDF นี้ไม่ได้"
        case CopyRestricted():
            return EXIT_COPY_RESTRICTED, (
                "ไฟล์ PDF นี้ตั้งสิทธิ์ห้ามคัดลอกข้อความ ผู้สร้างเอกสารไม่อนุญาตให้นำข้อความออกไปใช้ จึงไม่แปลงไฟล์นี้"
            )
        case DamagedFile():
            return EXIT_DAMAGED_FILE, "ไฟล์เสียหรือไม่สมบูรณ์ จึงเปิดอ่านไม่ได้ ลองดาวน์โหลดหรือคัดลอกไฟล์มาใหม่"
    raise error


if __name__ == "__main__":
    sys.exit(main())
