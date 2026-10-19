"""Command line for the quality harness: score a corpus and gate on the result."""

import argparse
import json
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from pdf_to_doc.quality import BrokenText, CorpusError, PageReport, Report, evaluate

EXIT_OK = 0
EXIT_OVER_LIMIT = 1
EXIT_BAD_CORPUS = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc-eval",
        description="Convert every source file in a corpus and measure broken text against its reference text.",
    )
    parser.add_argument("corpus", type=Path, help="folder of <name>.pdf files and <name>/page-NNN.reference.md")
    parser.add_argument("--json", type=Path, help="also write the full report to this JSON file")
    parser.add_argument("--max-cer", type=float, help="fail when the corpus CER is above this")
    parser.add_argument("--max-broken", type=int, help="fail when there is more broken text than this")
    args = parser.parse_args(argv)

    # Windows consoles default to a code page that cannot print Thai.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        report = evaluate(args.corpus)
    except CorpusError as error:
        print(f"ERROR: {error}")
        return EXIT_BAD_CORPUS

    print(format_table(report))
    if args.json:
        args.json.write_text(json.dumps(as_dict(report), ensure_ascii=False, indent=1), encoding="utf-8")

    failures = []
    if args.max_cer is not None and report.cer > args.max_cer:
        failures.append(f"CER {report.cer:.4f} > {args.max_cer}")
    if args.max_broken is not None and report.broken.total > args.max_broken:
        failures.append(f"broken text {report.broken.total} > {args.max_broken}")
    for failure in failures:
        print(f"FAILED: {failure}")
    return EXIT_OVER_LIMIT if failures else EXIT_OK


def as_dict(report: Report) -> dict[str, Any]:
    return {
        "total": {
            "pages": len(report.pages),
            "cer": report.cer,
            "thai_cer": report.thai_cer,
            "broken": _broken_dict(report.broken),
            "uncertain": report.uncertain,
        },
        "pages": [_page_dict(page) for page in report.pages],
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
        "broken": _broken_dict(score.broken),
    }


def _broken_dict(broken: BrokenText) -> dict[str, int]:
    return asdict(broken) | {"total": broken.total}


_BROKEN_KINDS = [field.name for field in fields(BrokenText)]
_COLUMNS = ["source", "page", "kind", "engine", "CER", "Thai CER", *_BROKEN_KINDS, "broken", "uncertain"]


def format_table(report: Report) -> str:
    rows = [[column.replace("_", " ") for column in _COLUMNS]]
    for page in report.pages:
        rows.append(
            [page.source, str(page.number), page.kind, page.engine or "-"]
            + _measures(page.score.cer, page.score.thai_cer, page.score.broken, page.uncertain)
        )
    rows.append(
        ["TOTAL", str(len(report.pages)), "", ""]
        + _measures(report.cer, report.thai_cer, report.broken, report.uncertain)
    )
    widths = [max(len(row[i]) for row in rows) for i in range(len(_COLUMNS))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows)


def _measures(cer: float, thai_cer: float, broken: BrokenText, uncertain: int) -> list[str]:
    counts = [str(getattr(broken, kind)) for kind in _BROKEN_KINDS]
    return [f"{cer:.4f}", f"{thai_cer:.4f}", *counts, str(broken.total), str(uncertain)]


if __name__ == "__main__":
    sys.exit(main())
