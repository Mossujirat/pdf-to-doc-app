"""A conversion in a fresh Python process, cut off from the network, with a temp area of its own.

A fresh process loads the converter and PaddleOCR from scratch, as a user's
first conversion does. Run as a script, this module refuses network access
before it loads the converter, converts one source file, and reports what the
conversion left behind while the process is still running, as a web service's
would be.
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

    output: str | None  # the Markdown, if the conversion succeeded
    failure: str | None  # the name of the error it raised, if it did not
    network: list[str]  # the network calls it tried, each one refused
    left_behind: list[str]  # files left in the temp area once it ended
    paddle_objects_alive: int  # Paddle predictors and tensors still alive once it ended; they hold what they last read
    log: str  # everything the process wrote to stdout and stderr, its error included


class ConversionStopped(Exception):
    """Raised to make a conversion fail partway."""


def convert_in_fresh_process(folder: Path, source: bytes, *, stop_at_ocr_page: int | None = None) -> Run:
    """Convert `source` to Markdown in a fresh process, in default mode.

    The process's temp area is `folder/temp`, and PaddleX keeps its working
    files in it, as in the image. `stop_at_ocr_page` makes the conversion fail
    just before it reads that OCR page.
    """
    temp = folder / "temp"
    temp.mkdir()
    source_path, output_path, report_path = folder / "source.pdf", folder / "output.md", folder / "report.json"
    source_path.write_bytes(source)
    environment = {
        **os.environ,
        "TMPDIR": str(temp),
        "TEMP": str(temp),
        "TMP": str(temp),
        "PADDLE_PDX_CACHE_HOME": str(temp / "paddlex"),
        # Thai written to a Windows console code page would turn into escapes, and hide in the log.
        "PYTHONIOENCODING": "utf-8",
    }
    stop_argument = [] if stop_at_ocr_page is None else [str(stop_at_ocr_page)]
    process = subprocess.run(
        [sys.executable, __file__, str(source_path), str(output_path), str(report_path), *stop_argument],
        env=environment,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        raise AssertionError(f"the fresh process crashed:\n{process.stderr}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return Run(
        output=output_path.read_text(encoding="utf-8") if output_path.exists() else None,
        failure=report["failure"],
        network=report["network"],
        left_behind=report["left_behind"],
        paddle_objects_alive=report["paddle_objects_alive"],
        log=process.stdout + process.stderr,
    )


def _convert(source: Path, output: Path, report: Path, stop_at_ocr_page: int | None) -> None:
    refused: list[str] = []

    def refuse_network(event: str, args: tuple[object, ...]) -> None:
        if event in _NETWORK_EVENTS:
            refused.append(f"{event} {args!r:.200}")
            raise OSError(f"network access refused: {event}")

    sys.addaudithook(refuse_network)
    # Everything a logger lets through, as when a deployment turns logging up. Paddle's
    # own loggers stay at ERROR, where the OCR adapter sets them.
    logging.basicConfig(level=logging.DEBUG)
    from pdf_to_doc import Progress, convert

    def stop_partway(update: Progress) -> None:
        if update.current == stop_at_ocr_page:
            raise ConversionStopped()

    failure = None
    try:
        output.write_bytes(convert(source.read_bytes(), progress=stop_partway).output)
    except Exception as error:
        failure = type(error).__name__
        # Logged with its message and traceback, as a service would log a failed conversion.
        logging.exception("conversion failed")
    temp = Path(tempfile.gettempdir())
    left_behind = sorted(str(path.relative_to(temp)) for path in temp.rglob("*") if path.is_file())
    report.write_text(
        json.dumps(
            {
                "failure": failure,
                "network": refused,
                "left_behind": left_behind,
                "paddle_objects_alive": _paddle_objects_alive(),
            }
        ),
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
    source, output, report, *stop_argument = sys.argv[1:]
    _convert(Path(source), Path(output), Path(report), int(stop_argument[0]) if stop_argument else None)
