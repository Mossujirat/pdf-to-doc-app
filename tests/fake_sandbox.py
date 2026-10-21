"""A fake sandbox for the web app's tests: the real sandbox entry point, run in process.

It converts in a thread with an OCR engine the test chooses, and sends back what the
entry point writes, line by line as it comes, so the web app reads the real protocol.
"""

import asyncio
import io
from collections.abc import AsyncGenerator, Callable
from typing import Any

from fake_ocr import BlankEngine

from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.sandbox import run
from pdf_to_doc.web.sandboxes import Ended


class FakeSandbox:
    def __init__(self, engine: Callable[[], OcrEngine] = BlankEngine) -> None:
        """`engine` makes a fresh OCR engine for each conversion."""
        self._engine = engine

    async def convert(self, source: bytes) -> AsyncGenerator[bytes | Ended]:
        loop = asyncio.get_running_loop()
        lines: asyncio.Queue[bytes | None] = asyncio.Queue()
        stdout = io.BytesIO()

        def convert_in_thread() -> int:
            try:
                return run(io.BytesIO(source), stdout, _Lines(loop, lines), ocr=self._engine())
            finally:
                loop.call_soon_threadsafe(lines.put_nowait, None)

        exit_code = loop.run_in_executor(None, convert_in_thread)
        while (line := await lines.get()) is not None:
            yield line
        yield Ended(await exit_code, stdout.getvalue())


class _Lines(io.BytesIO):
    """A stderr that hands each line to the event loop as soon as it is written."""

    def __init__(self, loop: asyncio.AbstractEventLoop, lines: asyncio.Queue[bytes | None]) -> None:
        super().__init__()
        self._loop = loop
        self._lines = lines
        self._pending = b""

    def write(self, data: Any) -> int:
        self._pending += bytes(data)
        *complete, self._pending = self._pending.split(b"\n")
        for line in complete:
            self._loop.call_soon_threadsafe(self._lines.put_nowait, line)
        return len(data)
