"""Command-line wrapper around the conversion function."""

import argparse
import sys
from pathlib import Path

from pdf_to_doc.conversion import convert


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc",
        description="แปลง PDF เป็น Markdown ที่ข้อความไทยอ่านได้ตรงกับต้นฉบับ",
    )
    parser.add_argument("source", type=Path, help="ไฟล์ PDF ต้นฉบับ")
    parser.add_argument(
        "-o", "--output", type=Path, help="ไฟล์ผลลัพธ์ (ค่าเริ่มต้น: ชื่อเดียวกับต้นฉบับ นามสกุล .md)"
    )
    args = parser.parse_args(argv)

    # Windows consoles default to a code page that cannot print Thai.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    output_path: Path = args.output or args.source.with_suffix(".md")
    result = convert(args.source.read_bytes(), to="markdown")
    output_path.write_bytes(result.output)

    print(f"{output_path}: {result.summary.headline()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
