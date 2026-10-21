"""The sandbox entry point: converts one source file inside a throwaway container (ADR 0004).

The source file's bytes come in on stdin. Each output goes out on stdout as a part:
a line with its format and its length in bytes, then the output itself. Events go
out on stderr, one JSON object per line, and never carry any of the file's content.
Its only setting is the OCR thread count, in `PDF_TO_DOC_OCR_THREADS`.
"""

import json
import os
import sys
from dataclasses import asdict
from typing import BinaryIO

from pdf_to_doc.conversion import convert
from pdf_to_doc.exit_codes import EXIT_FAILED, EXIT_MODELS_MISSING, EXIT_OK, REFUSAL_EXIT_CODES
from pdf_to_doc.intake import IntakeError, TooLarge, UnsupportedFormat
from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.ocr_models import ModelsMissing
from pdf_to_doc.progress import Opened, Progress


def main() -> int:
    """The command the sandbox container runs.

    Only the parts reach stdout, and only the events stderr. Anything else written
    to them, such as Paddle's own messages from its C++ side or a library's warning,
    goes nowhere: the standard streams are pointed at the null device, and the
    parts and events go out through copies of them made first.
    """
    stdout = os.fdopen(os.dup(sys.stdout.fileno()), "wb")
    stderr = os.fdopen(os.dup(sys.stderr.fileno()), "wb")
    nowhere = os.open(os.devnull, os.O_WRONLY)
    os.dup2(nowhere, sys.stdout.fileno())
    os.dup2(nowhere, sys.stderr.fileno())
    os.close(nowhere)
    return run(sys.stdin.buffer, stdout, stderr)


def run(stdin: BinaryIO, stdout: BinaryIO, stderr: BinaryIO, *, ocr: OcrEngine | None = None) -> int:
    """Convert the source file on `stdin` into both outputs, or Markdown only for a DOCX,
    and return the exit code. `ocr` replaces the default OCR engine, for tests."""

    def report(update: Opened | Progress) -> None:
        _send(stderr, {"event": "opened" if isinstance(update, Opened) else "progress", **asdict(update)})

    try:
        # No password reaches the sandbox, so a PDF that needs one is refused.
        result = convert(stdin.read(), to={"markdown", "docx"}, ocr=ocr, progress=report)
    except IntakeError as error:
        exit_code = REFUSAL_EXIT_CODES[type(error)]
        _send(stderr, _refusal_event(error))
        return exit_code
    except Exception as error:
        # An error's message can quote what it was reading, so only its type goes out.
        _send(stderr, {"event": "failure", "error": type(error).__name__})
        return EXIT_MODELS_MISSING if isinstance(error, ModelsMissing) else EXIT_FAILED
    _send(stderr, {"event": "summary", **asdict(result.summary)})
    for name, output in result.outputs.items():
        stdout.write(f"{name} {len(output)}\n".encode("ascii") + output)
    stdout.flush()
    return EXIT_OK


def _refusal_event(error: IntakeError) -> dict[str, object]:
    """The refusal event: the error's type, and what the web needs to explain it."""
    match error:
        case UnsupportedFormat(found=found):
            details: dict[str, object] = {"found": found}
        case TooLarge(unit=unit, size=size, limit=limit):
            details = {"unit": unit, "size": size, "limit": limit}
        case _:
            details = {}
    return {"event": "refusal", "kind": type(error).__name__, **details}


def _send(stderr: BinaryIO, event: dict[str, object]) -> None:
    """One event, as soon as it happens."""
    stderr.write(json.dumps(event).encode("ascii") + b"\n")
    stderr.flush()


if __name__ == "__main__":
    sys.exit(main())
