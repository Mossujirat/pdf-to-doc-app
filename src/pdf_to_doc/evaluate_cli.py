"""Command line for the quality harness: score a corpus and gate on the result."""

import argparse
import json
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from pdf_to_doc.console import thai_safe_output
from pdf_to_doc.model import PageKind
from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.quality import BrokenText, CorpusError, PageReport, Report, evaluate

EXIT_OK = 0
EXIT_OVER_LIMIT = 1
EXIT_BAD_CORPUS = 2

_KINDS: tuple[PageKind, ...] = ("text", "ocr")


def main(argv: list[str] | None = None, *, ocr: OcrEngine | None = None) -> int:
    """Run the command. `ocr` replaces the default OCR engine, for tests."""
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc-eval",
        description="Convert every source file in a corpus and measure broken text against its reference text.",
    )
    parser.add_argument("corpus", type=Path, help="folder of <name>.pdf or <name>.docx files and <name>/page-NNN.reference.md")
    parser.add_argument("--json", type=Path, help="also write the full report to this JSON file")
    # The quality gate covers text pages; OCR pages are measured, and their gate
    # comes with the OCR baseline (ticket 17).
    parser.add_argument("--max-cer", type=float, help="fail when the CER on text pages is above this")
    parser.add_argument("--max-broken", type=int, help="fail when text pages hold more broken text than this")
    args = parser.parse_args(argv)

    thai_safe_output()

    try:
        report = evaluate(args.corpus, ocr=ocr)
    except CorpusError as error:
        print(f"ERROR: {error}")
        return EXIT_BAD_CORPUS

    print(format_table(report))
    if args.json:
        args.json.write_text(json.dumps(as_dict(report), ensure_ascii=False, indent=1), encoding="utf-8")

    text_pages = report.of_kind("text")
    failures = []
    if args.max_cer is not None and text_pages.cer > args.max_cer:
        failures.append(f"CER on text pages {text_pages.cer:.4f} > {args.max_cer}")
    if args.max_broken is not None and text_pages.broken.total > args.max_broken:
        failures.append(f"broken text on text pages {text_pages.broken.total} > {args.max_broken}")
    for failure in failures:
        print(f"FAILED: {failure}")
    return EXIT_OVER_LIMIT if failures else EXIT_OK


def as_dict(report: Report) -> dict[str, Any]:
    return {
        "total": _total_dict(report),
        "by_kind": {kind: _total_dict(report.of_kind(kind)) for kind in _KINDS},
        "pages": [_page_dict(page) for page in report.pages],
    }


def _total_dict(report: Report) -> dict[str, Any]:
    return {
        "pages": len(report.pages),
        "cer": report.cer,
        "thai_cer": report.thai_cer,
        "broken": _broken_dict(report.broken),
        "uncertain": report.uncertain,
        "unmarked_share": report.unmarked_share,
        "cells": report.cells,
        "cells_right": report.cells_right,
    }


def _page_dict(page: PageReport) -> dict[str, Any]:
    score = page.score
    return {
        "source": page.source,
        "page": page.number,
        "kind": page.kind,
        "engine": page.engine,
        "uncertain": page.uncertain,
        "cer": score.cer,
        "thai_cer": score.thai_cer,
        "edits": score.edits,
        "characters": score.characters,
        "unmarked_edits": score.unmarked_edits,
        "marked_characters": score.marked_characters,
        "broken": _broken_dict(score.broken),
        "cells": score.cells,
        "cells_right": score.cells_right,
    }


def _broken_dict(broken: BrokenText) -> dict[str, int]:
    return asdict(broken) | {"total": broken.total}


_BROKEN_KINDS = [field.name for field in fields(BrokenText)]
# "unmarked" is the share of edits that fall outside uncertain text; "cells", the reference
# tables' cells that the output holds in the same place, out of all of them.
_COLUMNS = ["source", "page", "kind", "engine", "CER", "Thai CER", *_BROKEN_KINDS, "broken", "uncertain", "unmarked", "cells"]


def format_table(report: Report) -> str:
    rows = [[column.replace("_", " ") for column in _COLUMNS]]
    for page in report.pages:
        rows.append([page.source, str(page.number), page.kind, page.engine or "-"] + _measures(Report(pages=(page,))))
    totals = [("TOTAL", report)] + [(f"TOTAL {kind}", report.of_kind(kind)) for kind in _KINDS]
    for label, part in totals:
        if part.pages:
            rows.append([label, str(len(part.pages)), "", ""] + _measures(part))
    widths = [max(len(row[i]) for row in rows) for i in range(len(_COLUMNS))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows)


def _measures(report: Report) -> list[str]:
    counts = [str(getattr(report.broken, kind)) for kind in _BROKEN_KINDS]
    return [
        f"{report.cer:.4f}",
        f"{report.thai_cer:.4f}",
        *counts,
        str(report.broken.total),
        str(report.uncertain),
        f"{report.unmarked_share:.2f}",
        f"{report.cells_right}/{report.cells}" if report.cells else "-",
    ]


if __name__ == "__main__":
    sys.exit(main())
