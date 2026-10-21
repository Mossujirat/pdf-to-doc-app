"""Reads back what the sandbox entry point wrote: the parts on stdout, and the events on stderr."""

import json
from typing import Any


def parts(stdout: bytes) -> dict[str, bytes]:
    """The parts on stdout, by name: each a line with its name and length, then that many bytes."""
    found: dict[str, bytes] = {}
    while stdout:
        header, stdout = stdout.split(b"\n", 1)
        name, length = header.decode("ascii").split(" ")
        found[name], stdout = stdout[: int(length)], stdout[int(length) :]
    return found


def events(stderr: bytes) -> list[dict[str, Any]]:
    """The events on stderr, one JSON object per line. Any other line fails to read."""
    return [json.loads(line) for line in stderr.decode("ascii").splitlines()]
