"""Console output for the command-line tools."""

import sys


def thai_safe_output() -> None:
    """Write stdout and stderr as UTF-8: Windows consoles default to a code page that cannot print Thai."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
