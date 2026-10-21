"""Command-line wrapper around the conversion function."""

import argparse
import math
import sys
from pathlib import Path
from typing import get_args

from pdf_to_doc.console import thai_safe_output
from pdf_to_doc.conversion import DocxToDocx, OutputFormat, convert
from pdf_to_doc.intake import (
    MAX_BYTES,
    MAX_PAGES,
    MAX_UNPACKED_BYTES,
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
from pdf_to_doc.progress import Opened, Progress

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
_SUFFIXES: dict[OutputFormat, str] = {"markdown": ".md", "docx": ".docx"}
_LINE_START = chr(13)  # a carriage return: the next print overwrites the line

_EXIT_CODES = f"""\
exit code:
  {EXIT_OK}  แปลงสำเร็จ
  {EXIT_UNSUPPORTED_FORMAT}  ไม่ใช่ไฟล์ที่แปลงได้ (เช่น Word รุ่นเก่า .doc หรือไฟล์ Word ที่ล็อกรหัสผ่าน) หรือขอแปลง DOCX เป็น DOCX
  {EXIT_TOO_LARGE}  ไฟล์ใหญ่เกิน {MAX_BYTES // _MB} MB เกิน {MAX_PAGES} หน้า หรือเป็น DOCX ที่แตกออกมาใหญ่เกิน {MAX_UNPACKED_BYTES // _MB} MB
  {EXIT_PASSWORD_REQUIRED}  PDF ล็อกด้วยรหัสผ่าน แต่ไม่ได้ใส่ --password
  {EXIT_WRONG_PASSWORD}  รหัสผ่านไม่ถูกต้อง
  {EXIT_COPY_RESTRICTED}  PDF ตั้งสิทธิ์ห้ามคัดลอกข้อความ
  {EXIT_DAMAGED_FILE}  ไฟล์เสียหรือไม่สมบูรณ์
  {EXIT_MODELS_MISSING}  ยังไม่ได้ติดตั้ง model สำหรับ OCR (สั่ง pdf-to-doc-models)"""


def main(argv: list[str] | None = None, *, ocr: OcrEngine | None = None) -> int:
    """Run the command. `ocr` replaces the default OCR engine, for tests."""
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc",
        description="แปลง PDF เป็น Markdown หรือ DOCX และแปลง DOCX เป็น Markdown โดยข้อความไทยอ่านได้ตรงกับต้นฉบับ",
        epilog=_EXIT_CODES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="ไฟล์ PDF หรือ DOCX ต้นฉบับ")
    parser.add_argument(
        "--to",
        choices=get_args(OutputFormat),
        help="รูปแบบผลลัพธ์: markdown สำหรับใช้กับ AI หรือ docx สำหรับแก้ไขใน Word"
        " (ค่าเริ่มต้น: ตามนามสกุลของ --output ถ้าไม่ได้ระบุจะเป็น markdown)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, help="ไฟล์ผลลัพธ์ (ค่าเริ่มต้น: ชื่อเดียวกับต้นฉบับ นามสกุล .md หรือ .docx)"
    )
    parser.add_argument("--password", help="รหัสผ่านสำหรับเปิดไฟล์ PDF ที่ล็อกไว้")
    args = parser.parse_args(argv)

    thai_safe_output()

    output_format: OutputFormat = args.to or _format_named_by(args.output)
    output_path: Path = args.output or args.source.with_suffix(_SUFFIXES[output_format])
    try:
        source = args.source.read_bytes()
    except OSError as error:
        parser.error(f"อ่านไฟล์ {args.source} ไม่ได้ ({error.strerror})")
    try:
        result = convert(source, to=output_format, password=args.password, ocr=ocr, progress=_show_progress)
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


def _format_named_by(output: Path | None) -> OutputFormat:
    """The format an output file's name asks for, so a .docx file never gets Markdown by default."""
    suffix = output.suffix.lower() if output else ""
    return next((name for name, known in _SUFFIXES.items() if known == suffix), "markdown")


def _show_progress(update: Opened | Progress) -> None:
    """One line per OCR page; on a terminal, each page overwrites the last. Other reports pass unseen."""
    match update:
        case Progress(stage="ocr", current=int(current), total=int(total)):
            overwrite = sys.stderr.isatty() and current < total
            print(f"OCR หน้า {current}/{total}", end=_LINE_START if overwrite else None, file=sys.stderr, flush=True)


def _refusal(error: IntakeError) -> tuple[int, str]:
    """The exit code and the Thai message for a source file that was refused."""
    match error:
        case UnsupportedFormat(found="doc"):
            return EXIT_UNSUPPORTED_FORMAT, (
                "ไฟล์นี้เป็น Word รุ่นเก่า (.doc) ซึ่งแปลงไม่ได้ กรุณาเปิดใน Word แล้วบันทึกเป็น .docx ก่อน"
            )
        case UnsupportedFormat(found="locked office"):
            return EXIT_UNSUPPORTED_FORMAT, (
                "ไฟล์ Office นี้ล็อกด้วยรหัสผ่าน จึงแปลงไม่ได้ ถ้าเป็นไฟล์ Word"
                " กรุณาเปิดใน Word แล้วบันทึกใหม่โดยไม่ตั้งรหัสผ่าน"
            )
        case UnsupportedFormat():
            return EXIT_UNSUPPORTED_FORMAT, "ไฟล์นี้ไม่ใช่ PDF หรือ DOCX จึงแปลงไม่ได้"
        case DocxToDocx():
            return EXIT_UNSUPPORTED_FORMAT, "ไฟล์นี้เป็น DOCX อยู่แล้ว จึงไม่แปลงเป็น DOCX อีก แปลงเป็น Markdown ได้ด้วย --to markdown"
        case TooLarge(unit="bytes", size=size, limit=limit):
            return EXIT_TOO_LARGE, f"ไฟล์นี้ใหญ่ {_megabytes(size)} MB เกินขนาดสูงสุดที่แปลงได้ {limit // _MB} MB"
        case TooLarge(unit="unpacked bytes", size=size, limit=limit):
            return EXIT_TOO_LARGE, (
                f"ไฟล์ DOCX นี้เมื่อแตกออกมาใหญ่ {_megabytes(size)} MB เกินขนาดสูงสุดที่แปลงได้ {limit // _MB} MB"
            )
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


def _megabytes(size: int) -> str:
    """A size in megabytes to one decimal place, rounded up, so a file just over a limit never shows as the limit."""
    return f"{math.ceil(size * 10 / _MB) / 10:.1f}"


if __name__ == "__main__":
    sys.exit(main())
