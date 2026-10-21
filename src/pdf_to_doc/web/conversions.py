"""The conversions the web app holds, in memory only: each one's state from upload to result.

A conversion runs in a sandbox, and what the sandbox sends back is read as untrusted.
The source file's bytes are held only until its conversion ends.
"""

import asyncio
import logging
import secrets
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import Literal

from pdf_to_doc.conversion import OutputFormat
from pdf_to_doc.exit_codes import EXIT_OK
from pdf_to_doc.summary import Summary
from pdf_to_doc.web.protocol import (
    Event,
    FailureEvent,
    Malformed,
    OpenedEvent,
    ProgressEvent,
    RefusalEvent,
    SummaryEvent,
    read_event,
    read_parts,
)
from pdf_to_doc.web.sandboxes import Ended, Sandbox

State = Literal["running", "finished", "refused", "failed"]

_log = logging.getLogger(__name__)


@dataclass
class Conversion:
    """One conversion. Only the browser whose token started it may see it."""

    token: str
    file_name: str  # only to name the downloads
    state: State = "running"
    opened: OpenedEvent | None = None
    progress: ProgressEvent | None = None
    summary: Summary | None = None
    outputs: dict[OutputFormat, bytes] = field(default_factory=dict)
    refusal: RefusalEvent | None = None


class Conversions:
    """Every conversion the web app holds, each converting in the sandbox as soon as it starts."""

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox
        self._held: dict[str, Conversion] = {}
        self._running: set[asyncio.Task[None]] = set()  # the event loop keeps only weak references

    def start(self, source: bytes, file_name: str, token: str) -> str:
        """Start converting the source file for the browser holding `token`, and return the
        conversion's identifier: 128 random bits, for its link."""
        identifier = secrets.token_urlsafe(16)
        conversion = Conversion(token, file_name)
        self._held[identifier] = conversion
        task = asyncio.get_running_loop().create_task(self._convert(conversion, source))
        self._running.add(task)
        task.add_done_callback(self._running.discard)
        return identifier

    def get(self, identifier: str, token: str | None) -> Conversion | None:
        """The conversion, if it exists and `token` is the one that started it."""
        conversion = self._held.get(identifier)
        if conversion is None or token is None or not secrets.compare_digest(conversion.token, token):
            return None
        return conversion

    async def _convert(self, conversion: Conversion, source: bytes) -> None:
        try:
            async with aclosing(self._sandbox.convert(source)) as sent:
                async for item in sent:
                    if isinstance(item, Ended):
                        _end(conversion, item)
                    else:
                        _apply(conversion, read_event(item))
        except Exception as error:
            # Only the type: a message could quote what the sandbox sent.
            _log.warning("conversion failed: %s", type(error).__name__)
            conversion.state = "failed"


def _apply(conversion: Conversion, event: Event) -> None:
    if conversion.summary is not None or conversion.refusal is not None:
        raise Malformed("an event after the conversion's last")
    match event:
        case OpenedEvent():
            conversion.opened = event
        case ProgressEvent():
            conversion.progress = event
        case SummaryEvent():
            conversion.summary = event.summary()
        case RefusalEvent():
            conversion.refusal = event
        case FailureEvent():
            _log.warning("conversion failed in the sandbox: %s", event.error)


def _end(conversion: Conversion, ended: Ended) -> None:
    if conversion.summary is not None and ended.exit_code == EXIT_OK:
        outputs = read_parts(ended.stdout)
        if "markdown" not in outputs:  # every source file gives Markdown
            raise Malformed("a conversion that gave no Markdown")
        conversion.outputs = outputs
        conversion.state = "finished"
    elif conversion.refusal is not None and ended.exit_code != EXIT_OK:
        conversion.state = "refused"
    else:
        conversion.state = "failed"
