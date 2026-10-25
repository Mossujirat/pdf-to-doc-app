"""The conversions the web app holds, in memory only: each one's state from upload to result.

A few conversions run at once, each in a sandbox, and the rest wait their turn, first in,
first out. What a sandbox sends back is read as untrusted. A source file's bytes are held
only while its conversion waits or runs.
"""

import asyncio
import logging
import secrets
from collections import Counter
from collections.abc import Callable
from contextlib import aclosing
from dataclasses import dataclass, field
from functools import partial
from typing import Literal

from pdf_to_doc.conversion import OutputFormat
from pdf_to_doc.exit_codes import EXIT_OK
from pdf_to_doc.progress import Stage
from pdf_to_doc.summary import Summary
from pdf_to_doc.web.allowance import Allowance, Charge
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
from pdf_to_doc.web.statistics import Statistics

State = Literal["waiting", "running", "finished", "refused", "failed", "cancelled", "over_allowance"]
Outcome = State | Literal["timed_out"]  # a failure, because the sandbox ran out of time
# Seconds on a clock that never goes back, such as time.monotonic. It tells no date.
Clock = Callable[[], float]

_log = logging.getLogger(__name__)


class QueueFull(Exception):
    """Every place is taken, and as many conversions wait as may."""


class HeldOutputsFull(Exception):
    """The outputs that ended conversions hold in memory total their cap or more."""


class AlreadyConverting(Exception):
    """The browser already has a conversion waiting or running: one file at a time."""

    def __init__(self, identifier: str) -> None:
        super().__init__("the browser already has a conversion waiting or running")
        self.identifier = identifier  # that conversion's


class _OverAllowance(Exception):
    """The source file has more pages than its client has left today."""


@dataclass
class Conversion:
    """One conversion. Only the browser whose token started it may see it."""

    token: str
    file_name: str  # only to show on its page and name the downloads
    # The client's address as its allowance counts it; held in memory only, and dropped when the
    # conversion ends.
    client_ip: str | None
    keep_images: bool = False  # the visitor's choice for the file's scans and pictures
    state: State = "waiting"
    charge: Charge | None = None  # its pages, charged to the client's allowance
    pages_left: int | None = None  # what the client had left today, when the file had more pages
    opened: OpenedEvent | None = None
    progress: ProgressEvent | None = None
    # The stages the sandbox has reported, so that its steps never show one it skipped as done.
    reached: set[Stage] = field(default_factory=set)
    summary: Summary | None = None
    outputs: dict[OutputFormat, bytes] = field(default_factory=dict)
    refusal: RefusalEvent | None = None
    failure: FailureEvent | None = None  # the sandbox's own word that it failed
    timed_out: bool = False  # failed because the sandbox was stopped by the time limit
    # On the app's clock: when it was queued, left the queue and ended.
    queued_at: float = 0.0
    started_at: float | None = None
    ended_at: float | None = None

    @property
    def ongoing(self) -> bool:
        """Whether it still waits or runs. A cancelled one has ended, even while its sandbox stops."""
        return self.state in ("waiting", "running")

    @property
    def outcome(self) -> Outcome:
        """Its state, with a failure told apart from a time-out."""
        return "timed_out" if self.state == "failed" and self.timed_out else self.state


class Conversions:
    """Every conversion the web app holds: at most `max_running` converting at once, and at most
    `max_waiting` waiting for a place. A conversion is forgotten `keep_for` seconds after it
    ends, however it ends, or as soon as the visitor deletes it. A conversion's pages are charged
    to its client's allowance as soon as the sandbox has counted them, and given back if it fails.
    While the outputs of ended conversions total `max_held_outputs` bytes or more, no file is
    taken and none waiting starts: only those running may add their outputs on top."""

    def __init__(
        self,
        sandbox: Sandbox,
        allowance: Allowance,
        statistics: Statistics,
        *,
        max_running: int,
        max_waiting: int,
        max_held_outputs: int,
        keep_for: float,
        clock: Clock,
    ) -> None:
        self._sandbox = sandbox
        self._allowance = allowance
        self._statistics = statistics
        self._max_running = max_running
        self._max_waiting = max_waiting
        self._max_held_outputs = max_held_outputs
        self._keep_for = keep_for
        self._clock = clock
        self._held: dict[str, Conversion] = {}
        self._waiting: dict[str, bytes] = {}  # each waiting conversion's source file, in the order they came
        self._running: dict[str, asyncio.Task[None]] = {}
        self._stopping = False

    def start(self, source: bytes, file_name: str, token: str, client_ip: str, *, keep_images: bool = False) -> str:
        """Queue the source file for the browser holding `token`, at the client address `client_ip`,
        to convert as soon as a place is free, keeping images if `keep_images`, and return the
        conversion's identifier: 128 random bits, for its link.

        Raises `AlreadyConverting` when that browser has a conversion waiting or running,
        `QueueFull` when no more may wait, and `HeldOutputsFull` when the outputs held reach their
        cap. Whichever it raises, nothing of the file is kept.
        """
        self.forget_expired()
        for other, conversion in self._held.items():
            if conversion.ongoing and secrets.compare_digest(conversion.token, token):
                raise AlreadyConverting(other)
        # A cancelled conversion keeps its place until its sandbox has stopped.
        if len(self._running) >= self._max_running and len(self._waiting) >= self._max_waiting:
            raise QueueFull()
        if self._outputs_full():
            raise HeldOutputsFull()
        identifier = secrets.token_urlsafe(16)
        self._held[identifier] = Conversion(
            token, file_name, client_ip, keep_images=keep_images, queued_at=self._clock()
        )
        self._waiting[identifier] = source
        self._start_next()
        return identifier

    def get(self, identifier: str, token: str | None) -> Conversion | None:
        """The conversion, if it is still held and `token` is the one that started it."""
        self.forget_expired()
        conversion = self._held.get(identifier)
        if conversion is None or token is None or not secrets.compare_digest(conversion.token, token):
            return None
        return conversion

    def place(self, identifier: str) -> int | None:
        """A waiting conversion's place in the queue, counting from 1."""
        return list(self._waiting).index(identifier) + 1 if identifier in self._waiting else None

    def time_left(self, conversion: Conversion) -> float:
        """How many more seconds an ended conversion is kept."""
        assert conversion.ended_at is not None
        return conversion.ended_at + self._keep_for - self._clock()

    def cancel(self, identifier: str) -> None:
        """Cancel a conversion that waits or runs. A waiting one leaves the queue. A running one's
        sandbox is told to stop, and its place goes to the next one waiting once it has."""
        conversion = self._held[identifier]
        if not conversion.ongoing:
            return
        self._end(conversion, "cancelled")
        if identifier in self._waiting:
            del self._waiting[identifier]
            self._count_queue()
        else:
            self._running[identifier].cancel()

    def forget(self, identifier: str) -> None:
        """Forget an ended conversion now, and its outputs with it, as when the visitor deletes them.
        One waiting for the outputs held to fall under their cap may then start."""
        if not self._held[identifier].ongoing:
            del self._held[identifier]
            self._start_next()

    def forget_expired(self) -> None:
        """Forget every conversion that ended `keep_for` seconds ago or more, and, after midnight,
        the client addresses of the day before. One waiting for the outputs held to fall under
        their cap may then start."""
        expired = [
            identifier
            for identifier, conversion in self._held.items()
            if conversion.ended_at is not None and self.time_left(conversion) <= 0
        ]
        for identifier in expired:
            del self._held[identifier]
        if expired:
            self._start_next()
        self._allowance.forget_past_days()

    async def forget_expired_every(self, seconds: float) -> None:
        """Forget expired conversions for as long as the app runs, even when no one asks for
        anything, so that their outputs, and the day before's addresses, leave memory on time."""
        while True:
            await asyncio.sleep(seconds)
            self.forget_expired()

    async def stop(self) -> None:
        """Stop every running conversion, and start none of those waiting, as when the service
        stops, so that no sandbox outlives it."""
        self._stopping = True
        running = list(self._running.values())
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)

    def _outputs_full(self) -> bool:
        """Whether the outputs held total their cap or more. Only an ended conversion holds
        outputs: one that finished, until it is forgotten."""
        held_bytes = sum(len(output) for conversion in self._held.values() for output in conversion.outputs.values())
        return held_bytes >= self._max_held_outputs

    def _start_next(self) -> None:
        """Start the conversions first in the queue, while places are free and the outputs held are
        under their cap."""
        while (
            self._waiting and len(self._running) < self._max_running and not self._stopping and not self._outputs_full()
        ):
            identifier = next(iter(self._waiting))
            source = self._waiting.pop(identifier)
            conversion = self._held[identifier]
            conversion.state = "running"
            conversion.started_at = self._clock()
            self._statistics.waited(conversion.started_at - conversion.queued_at)
            task = asyncio.get_running_loop().create_task(self._convert(conversion, source))
            self._running[identifier] = task
            task.add_done_callback(partial(self._ended, identifier))
        self._count_queue()

    def _count_queue(self) -> None:
        self._statistics.queue(len(self._waiting), len(self._running))

    def _ended(self, identifier: str, task: asyncio.Task[None]) -> None:
        del self._running[identifier]
        self._start_next()

    async def _convert(self, conversion: Conversion, source: bytes) -> None:
        outcome: State = "failed"  # unless the sandbox says how it ended
        outputs: dict[OutputFormat, bytes] = {}
        try:
            async with aclosing(self._sandbox.convert(source, keep_images=conversion.keep_images)) as sent:
                async for item in sent:
                    if isinstance(item, Ended):
                        conversion.timed_out = item.timed_out
                        if item.usage is not None:
                            self._statistics.used(item.usage)
                        outcome, outputs = _outcome(conversion, item)
                    else:
                        self._apply(conversion, read_event(item))
        except Exception as error:
            if conversion.pages_left is None:
                # Only the type: a message could quote what the sandbox sent.
                _log.warning("conversion failed: %s", type(error).__name__)
            # Over the allowance, leaving the loop has stopped the sandbox before any page was
            # read; that stays the outcome even if stopping it went wrong.
            outcome = "over_allowance" if conversion.pages_left is not None else "failed"
        if conversion.state == "running":  # a cancel, even one that went wrong while stopping, stays a cancel
            self._end(conversion, outcome, outputs)

    def _apply(self, conversion: Conversion, event: Event) -> None:
        if conversion.summary is not None or conversion.refusal is not None or conversion.failure is not None:
            raise Malformed("an event after the conversion's last")
        match event:
            case OpenedEvent():
                self._charge(conversion, event)
            case ProgressEvent():
                if event.stage == "images" and not conversion.keep_images:
                    raise Malformed("pages kept as images when that was not asked for")
                conversion.progress = event
                conversion.reached.add(event.stage)
            case SummaryEvent():
                conversion.summary = event.summary()
            case RefusalEvent():
                conversion.refusal = event
            case FailureEvent():
                conversion.failure = event
                _log.warning("conversion failed in the sandbox: %s", event.error)

    def _charge(self, conversion: Conversion, opened: OpenedEvent) -> None:
        """Charge the source file's pages to its client, or stop it if they do not fit."""
        if conversion.opened is not None:
            raise Malformed("a second count of the pages")
        assert conversion.client_ip is not None  # held until the conversion ends
        conversion.opened = opened
        conversion.charge = self._allowance.charge(conversion.client_ip, opened.pages)
        if conversion.charge is None:
            conversion.pages_left = self._allowance.left(conversion.client_ip)
            raise _OverAllowance()

    def _end(self, conversion: Conversion, state: State, outputs: dict[OutputFormat, bytes] | None = None) -> None:
        """End the conversion, keeping its outputs only if it finished. A failure, the service's
        own, gives its pages back; a cancel does not. Its client's address is dropped."""
        conversion.state = state
        conversion.ended_at = self._clock()
        conversion.outputs = outputs if state == "finished" and outputs else {}
        if state == "failed" and conversion.charge is not None:
            self._allowance.give_back(conversion.charge)
        conversion.charge = None
        conversion.client_ip = None
        self._count(conversion)

    def _count(self, conversion: Conversion) -> None:
        """Count how the conversion ended, for the operator's statistics."""
        self._statistics.ended(conversion.outcome)
        if conversion.started_at is not None and conversion.ended_at is not None:
            self._statistics.ran(conversion.ended_at - conversion.started_at)
        if conversion.state == "finished" and conversion.summary is not None:
            self._statistics.pages(Counter(page.kind for page in conversion.summary.pages))
        if conversion.state == "refused" and conversion.refusal is not None:
            self._statistics.refused(conversion.refusal.kind)
        if conversion.state == "over_allowance":
            self._statistics.refused("over the allowance")


def _outcome(conversion: Conversion, ended: Ended) -> tuple[State, dict[OutputFormat, bytes]]:
    """How the conversion ended, by what the sandbox sent, and the outputs if it finished."""
    if ended.timed_out:
        return "failed", {}
    if conversion.summary is not None and ended.exit_code == EXIT_OK:
        outputs = read_parts(ended.stdout)
        if "markdown" not in outputs:  # every source file gives Markdown
            raise Malformed("a conversion that gave no Markdown")
        return "finished", outputs
    if conversion.refusal is not None and ended.exit_code != EXIT_OK:
        return "refused", {}
    return "failed", {}
