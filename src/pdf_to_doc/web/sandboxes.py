"""Where the web app's conversions run: never in the web app itself, which only passes a
source file's bytes along and reads back what the sandbox sends (ADR 0004)."""

import asyncio
import os
import sys
from asyncio.subprocess import PIPE
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Protocol

from pdf_to_doc.sandbox import KEEP_IMAGES_VARIABLE, keep_images_setting
from pdf_to_doc.web.protocol import MAX_EVENT_LINE


@dataclass(frozen=True)
class Usage:
    """What a sandbox used, as Docker's stats showed it while it ran."""

    peak_memory: int  # bytes, at the most
    cpu_time: float  # seconds, in all


@dataclass(frozen=True)
class Ended:
    """How a sandbox's conversion ended: its exit code, and everything it wrote to stdout."""

    exit_code: int
    stdout: bytes
    timed_out: bool = False  # stopped by the launcher's time limit
    usage: Usage | None = None  # the launcher's, when Docker's stats said


class Sandbox(Protocol):
    def convert(self, source: bytes, *, keep_images: bool = False) -> AsyncGenerator[bytes | Ended]:
        """Convert the source file, keeping images if `keep_images`: each event line from the
        sandbox's stderr as it comes, then how it ended. Stopping early, as when the task reading
        it is cancelled, stops the conversion."""
        ...


class LocalSandbox:
    """The sandbox entry point in a process of its own, for development on a machine
    without Docker. It isolates nothing: the launcher's containers do that."""

    async def convert(self, source: bytes, *, keep_images: bool = False) -> AsyncGenerator[bytes | Ended]:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pdf_to_doc.sandbox",
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            limit=MAX_EVENT_LINE,
            env={**os.environ, KEEP_IMAGES_VARIABLE: keep_images_setting(keep_images)},
        )
        assert process.stdin is not None and process.stdout is not None and process.stderr is not None
        # Read alongside the events, or a full pipe would stall the sandbox before it ends.
        stdout = asyncio.ensure_future(process.stdout.read())
        try:
            process.stdin.write(source)
            await process.stdin.drain()
            process.stdin.close()
            while line := await process.stderr.readline():
                yield line.rstrip(b"\n")
            yield Ended(await process.wait(), await stdout)
        finally:
            stdout.cancel()
            if process.returncode is None:
                process.kill()
                await process.wait()
