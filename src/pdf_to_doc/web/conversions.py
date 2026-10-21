"""The conversions the web app holds, in memory only: each one's state from upload to result.

A few conversions run at once, each in a sandbox, and the rest wait their turn, first in,
first out. What a sandbox sends back is read as untrusted. A source file's bytes are held
only while its conversion waits or runs.
"""

import asyncio
import logging
import secrets
from contextlib import aclosing
from dataclasses import dataclass, field
from functools import partial
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

State = Literal["waiting", "running", "finished", "refused", "failed", "cancelled"]

_log = logging.getLogger(__name__)


class QueueFull(Exception):
    """Every place is taken, and as many conversions wait as may."""


class AlreadyConverting(Exception):
    """The browser already has a conversion waiting or running: one file at a time."""

    def __init__(self, identifier: str) -> None:
        super().__init__("the browser already has a conversion waiting or running")
        self.identifier = identifier  # that conversion's


@dataclass
class Conversion:
    """One conversion. Only the browser whose token started it may see it."""

    token: str
    file_name: str  # only to name the downloads
    state: State = "waiting"
    opened: OpenedEvent | None = None
    progress: ProgressEvent | None = None
    summary: Summary | None = None
    outputs: dict[OutputFormat, bytes] = field(default_factory=dict)
    refusal: RefusalEvent | None = None

    @property
    def ongoing(self) -> bool:
        """Whether it still waits or runs. A cancelled one has ended, even while its sandbox stops."""
        return self.state in ("waiting", "running")


class Conversions:
    """Every conversion the web app holds: at most `max_running` converting at once, and at most
    `max_waiting` waiting for a place."""

    def __init__(self, sandbox: Sandbox, *, max_running: int, max_waiting: int) -> None:
        self._sandbox = sandbox
        self._max_running = max_running
        self._max_waiting = max_waiting
        self._held: dict[str, Conversion] = {}
        self._waiting: dict[str, bytes] = {}  # each waiting conversion's source file, in the order they came
        self._running: dict[str, asyncio.Task[None]] = {}
        self._stopping = False

    def start(self, source: bytes, file_name: str, token: str) -> str:
        """Queue the source file for the browser holding `token`, to convert as soon as a place
        is free, and return the conversion's identifier: 128 random bits, for its link.

        Raises `AlreadyConverting` when that browser has a conversion waiting or running, and
        `QueueFull` when no more may wait. Either way, nothing of the file is kept.
        """
        for other in (*self._waiting, *self._running):
            if self._held[other].ongoing and secrets.compare_digest(self._held[other].token, token):
                raise AlreadyConverting(other)
        # A cancelled conversion keeps its place until its sandbox has stopped.
        if len(self._running) >= self._max_running and len(self._waiting) >= self._max_waiting:
            raise QueueFull()
        identifier = secrets.token_urlsafe(16)
        self._held[identifier] = Conversion(token, file_name)
        self._waiting[identifier] = source
        self._start_next()
        return identifier

    def get(self, identifier: str, token: str | None) -> Conversion | None:
        """The conversion, if it exists and `token` is the one that started it."""
        conversion = self._held.get(identifier)
        if conversion is None or token is None or not secrets.compare_digest(conversion.token, token):
            return None
        return conversion

    def place(self, identifier: str) -> int | None:
        """A waiting conversion's place in the queue, counting from 1."""
        return list(self._waiting).index(identifier) + 1 if identifier in self._waiting else None

    def cancel(self, identifier: str) -> None:
        """Cancel a conversion that waits or runs. A waiting one leaves the queue. A running one's
        sandbox is told to stop, and its place goes to the next one waiting once it has."""
        conversion = self._held[identifier]
        if not conversion.ongoing:
            return
        conversion.state = "cancelled"
        if identifier in self._waiting:
            del self._waiting[identifier]
        else:
            self._running[identifier].cancel()

    async def stop(self) -> None:
        """Stop every running conversion, and start none of those waiting, as when the service
        stops, so that no sandbox outlives it."""
        self._stopping = True
        running = list(self._running.values())
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)

    def _start_next(self) -> None:
        """Start the conversions first in the queue, while places are free."""
        while self._waiting and len(self._running) < self._max_running and not self._stopping:
            identifier = next(iter(self._waiting))
            source = self._waiting.pop(identifier)
            conversion = self._held[identifier]
            conversion.state = "running"
            task = asyncio.get_running_loop().create_task(self._convert(conversion, source))
            self._running[identifier] = task
            task.add_done_callback(partial(self._ended, identifier))

    def _ended(self, identifier: str, task: asyncio.Task[None]) -> None:
        del self._running[identifier]
        self._start_next()

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
            if conversion.state == "running":  # a cancel that went wrong while stopping is still a cancel
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
