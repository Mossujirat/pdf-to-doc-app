"""A conversion in a fresh Python process, cut off from the network, with a temp area of its own.

A fresh process loads the converter and PaddleOCR from scratch, as a user's
first conversion does. Run as a script, this module refuses network access
before it loads the converter, converts one source file, and reports what the
conversion left behind while the process is still running, as a web service's
would be. It converts either through the conversion function, or through the
sandbox entry point with the source file on its stdin, as the launcher runs it.
"""

import gc
import json
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    # Only for type checking: the converter must load after the audit hook is in place.
    from pdf_to_doc.conversion import OutputFormat

# Calls that reach beyond this machine. Creating a socket, binding it here and
# asking for the machine's own name stay allowed: urllib3 binds a socket on ::1
# at import, to learn whether IPv6 works.
_NETWORK_EVENTS = frozenset(
    {
        "socket.connect",
        "socket.sendto",
        "socket.sendmsg",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
    }
)


@dataclass(frozen=True)
class Run:
    """What a conversion in a fresh process did."""

    output: bytes | None  # the output, if the conversion succeeded
    failure: str | None  # the name of the error it raised, if it did not
    network: list[str]  # the network calls it tried, each one refused
    left_behind: list[str]  # files left in the temp area once it ended
    paddle_objects_alive: int  # Paddle predictors and tensors still alive once it ended; they hold what they last read
    log: str  # everything the process wrote to stdout and stderr, its error included


@dataclass(frozen=True)
class SandboxRun:
    """What the sandbox entry point did in a fresh process."""

    exit_code: int
    stdout: bytes
    stderr: bytes
    network: list[str]  # the network calls it tried, each one refused
    left_behind: list[str]  # files left in the temp area once it ended
    paddle_objects_alive: int  # Paddle predictors and tensors still alive once it ended; they hold what they last read


class ConversionStopped(Exception):
    """Raised to make a conversion fail partway."""


def convert_in_fresh_process(
    folder: Path, source: bytes, *, to: "OutputFormat" = "markdown", stop_at_ocr_page: int | None = None
) -> Run:
    """Convert `source` to the output format `to` in a fresh process, in default mode.

    The process's temp area is `folder/temp`, and PaddleX keeps its working
    files in it, as in the image. `stop_at_ocr_page` makes the conversion fail
    just before it reads that OCR page.
    """
    source_path, output_path, report_path = folder / "source.pdf", folder / "output", folder / "report.json"
    source_path.write_bytes(source)
    stop_argument = [] if stop_at_ocr_page is None else [str(stop_at_ocr_page)]
    process = subprocess.run(
        [sys.executable, __file__, str(source_path), str(output_path), str(report_path), to, *stop_argument],
        env=_environment_with_temp_area(folder),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        raise AssertionError(f"the fresh process crashed:\n{process.stderr}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return Run(
        output=output_path.read_bytes() if output_path.exists() else None,
        failure=report["failure"],
        network=report["network"],
        left_behind=report["left_behind"],
        paddle_objects_alive=report["paddle_objects_alive"],
        log=process.stdout + process.stderr,
    )


def sandbox_in_fresh_process(folder: Path, source: bytes, *, ocr_threads: int) -> SandboxRun:
    """Run the sandbox entry point in a fresh process, with `source` on its stdin and the OCR
    thread count set, as the launcher runs it. The temp area is as for `convert_in_fresh_process`."""
    report_path = folder / "report.json"
    process = subprocess.run(
        [sys.executable, __file__, "sandbox", str(report_path)],
        input=source,
        env={**_environment_with_temp_area(folder), "PDF_TO_DOC_OCR_THREADS": str(ocr_threads)},
        capture_output=True,
        check=False,
    )
    if not report_path.exists():
        raise AssertionError(f"the fresh process crashed:\n{process.stderr.decode('utf-8', errors='replace')}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return SandboxRun(
        exit_code=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
        network=report["network"],
        left_behind=report["left_behind"],
        paddle_objects_alive=report["paddle_objects_alive"],
    )


def _environment_with_temp_area(folder: Path) -> dict[str, str]:
    """The fresh process's environment, with its temp area in `folder/temp`."""
    temp = folder / "temp"
    temp.mkdir()
    return {
        **os.environ,
        "TMPDIR": str(temp),
        "TEMP": str(temp),
        "TMP": str(temp),
        "PADDLE_PDX_CACHE_HOME": str(temp / "paddlex"),
        # Thai written to a Windows console code page would turn into escapes, and hide in the log.
        "PYTHONIOENCODING": "utf-8",
    }


def _convert(source: Path, output: Path, report: Path, to: "OutputFormat", stop_at_ocr_page: int | None) -> None:
    refused = _refuse_network_and_log_everything()
    from pdf_to_doc import Opened, Progress, convert

    def stop_partway(update: Opened | Progress) -> None:
        if isinstance(update, Progress) and update.stage == "ocr" and update.current == stop_at_ocr_page:
            raise ConversionStopped()

    failure = None
    try:
        output.write_bytes(convert(source.read_bytes(), to=to, progress=stop_partway).output)
    except Exception as error:
        failure = type(error).__name__
        # Logged with its message and traceback, as a service would log a failed conversion.
        logging.exception("conversion failed")
    _write_report(report, {"failure": failure, "network": refused})


def _sandbox(report: Path) -> int:
    refused = _refuse_network_and_log_everything()
    from pdf_to_doc.sandbox import main

    exit_code = main()
    _write_report(report, {"network": refused})
    return exit_code


def _refuse_network_and_log_everything() -> list[str]:
    """Refuse every network call from now on, and log everything a logger lets through,
    as when a deployment turns logging up. Paddle's own loggers stay at ERROR, where the
    OCR adapter sets them. Returns the list the refused calls go into."""
    refused: list[str] = []

    def refuse_network(event: str, args: tuple[object, ...]) -> None:
        if event in _NETWORK_EVENTS:
            refused.append(f"{event} {args!r:.200}")
            raise OSError(f"network access refused: {event}")

    sys.addaudithook(refuse_network)
    logging.basicConfig(level=logging.DEBUG)
    return refused


def _write_report(report: Path, findings: dict[str, object]) -> None:
    """Write the findings, with what the conversion left behind, while the process still runs."""
    temp = Path(tempfile.gettempdir())
    left_behind = sorted(str(path.relative_to(temp)) for path in temp.rglob("*") if path.is_file())
    report.write_text(
        json.dumps({**findings, "left_behind": left_behind, "paddle_objects_alive": _paddle_objects_alive()}),
        encoding="utf-8",
    )


def _paddle_objects_alive() -> int:
    """How many Paddle predictors and tensors are still alive, once garbage is collected."""
    inference = sys.modules.get("paddle.inference")
    if inference is None:  # Paddle was never loaded
        return 0
    gc.collect()
    kinds = (inference.Predictor, inference.Tensor)
    # The collector does not track Paddle's objects, nor a dict or tuple that holds only
    # such objects, so everything reachable from what it does track is searched.
    seen: set[int] = set()
    alive: set[int] = set()
    waiting = gc.get_objects()
    while waiting:
        item = waiting.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, kinds):
            alive.add(id(item))
        waiting.extend(gc.get_referents(item))
    return len(alive)


if __name__ == "__main__":
    if sys.argv[1] == "sandbox":
        sys.exit(_sandbox(Path(sys.argv[2])))
    source, output, report, to, *stop_argument = sys.argv[1:]
    _convert(
        Path(source),
        Path(output),
        Path(report),
        cast("OutputFormat", to),
        int(stop_argument[0]) if stop_argument else None,
    )
