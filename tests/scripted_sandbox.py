"""A sandbox that sends back what the test scripted, whatever the source file: for what a
real conversion would not do on cue, such as failing, running out of time or misbehaving."""

from collections.abc import AsyncGenerator

from pdf_to_doc.web.sandboxes import Ended


class ScriptedSandbox:
    def __init__(self, lines: list[bytes], ended: Ended | None) -> None:
        """`lines` are the event lines it sends; `ended` how it ends, or None to end without saying."""
        self._lines = lines
        self._ended = ended

    async def convert(self, source: bytes) -> AsyncGenerator[bytes | Ended]:
        for line in self._lines:
            yield line
        if self._ended is not None:
            yield self._ended
