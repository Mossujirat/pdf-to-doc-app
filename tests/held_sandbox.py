"""A sandbox the test drives: each conversion starts when the web app asks for one, reports
reading its first OCR page, or what the test chose, and goes no further until the test ends it."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing

from pdf_to_doc.web.sandboxes import Ended

_STARTED = (
    b'{"event": "opened", "source_type": "pdf", "pages": 2}',
    b'{"event": "progress", "stage": "ocr", "current": 1, "total": 2}',
)
_SUMMARY = (
    b'{"event": "summary", "pages": [{"number": 1, "kind": "ocr", "engine": "held",'
    b' "untrusted_text_layer": false, "placeholders": [], "uncertain": 0}]}'
)
_MARKDOWN = "เสร็จแล้ว".encode()


class HeldConversion:
    """One conversion in the held sandbox."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        source: bytes,
        reports: tuple[bytes, ...],
        stopping_takes: float,
        stopping_fails: bool,
    ) -> None:
        self.source = source
        self.stopped = False  # the web app stopped it before the test ended it
        self._loop = loop
        self._reports = reports
        self._ended = asyncio.Event()
        self._stopping_takes = stopping_takes
        self._stopping_fails = stopping_fails

    def end(self) -> None:
        """Let the conversion finish. Called from the test's thread."""
        self._loop.call_soon_threadsafe(self._ended.set)

    async def sent(self) -> AsyncGenerator[bytes | Ended]:
        finished = False
        try:
            for line in self._reports:
                yield line
            await self._ended.wait()
            yield _SUMMARY
            finished = True
            yield Ended(0, b"markdown %d\n" % len(_MARKDOWN) + _MARKDOWN)
        finally:
            if not finished:
                self.stopped = True
                await asyncio.sleep(self._stopping_takes)
                if self._stopping_fails:
                    raise ConnectionResetError("the sandbox could not be reached to stop it")


class HeldSandbox:
    def __init__(
        self, *, reports: tuple[bytes, ...] = _STARTED, stopping_takes: float = 0, stopping_fails: bool = False
    ) -> None:
        """`reports` are the event lines each conversion sends before it is held; `stopping_takes`
        is how long a conversion takes to stop, in seconds, as a container can; `stopping_fails`
        makes stopping one raise an error, as a broken connection can."""
        self.started: list[HeldConversion] = []  # in the order the web app started them
        self._reports = reports
        self._stopping_takes = stopping_takes
        self._stopping_fails = stopping_fails

    async def convert(self, source: bytes, *, keep_images: bool = False) -> AsyncGenerator[bytes | Ended]:
        conversion = HeldConversion(
            asyncio.get_running_loop(), source, self._reports, self._stopping_takes, self._stopping_fails
        )
        self.started.append(conversion)
        async with aclosing(conversion.sent()) as sent:
            async for item in sent:
                yield item
