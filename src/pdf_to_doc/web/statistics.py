"""How the service is used, for its operator: counters held in memory, since the service started
and for today, Bangkok's day, and lost on restart. They hold no address, file name, link or
content. Only a listener on the server's own loopback address serves them, and
`pdf-to-doc-statistics` reads them there.
"""

import json
import logging
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from typing import Any

import httpx

from pdf_to_doc.web.allowance import BANGKOK, WallClock
from pdf_to_doc.web.sandboxes import Usage

PORT = 8001  # on the loopback address
_log = logging.getLogger(__name__)


@dataclass
class Durations:
    """How long something took, every time it happened, in seconds."""

    count: int = 0
    total: float = 0.0
    longest: float = 0.0

    def add(self, seconds: float) -> None:
        self.count += 1
        self.total += seconds
        self.longest = max(self.longest, seconds)


@dataclass
class Counts:
    conversions: Counter[str] = field(default_factory=Counter)  # by how they ended
    pages: Counter[str] = field(default_factory=Counter)  # of finished conversions, by kind
    refusals: Counter[str] = field(default_factory=Counter)  # of uploads, and by the sandbox, by kind
    bot_check_failures: Counter[str] = field(default_factory=Counter)  # by why
    run_times: Durations = field(default_factory=Durations)  # from leaving the queue to ending
    queue_waits: Durations = field(default_factory=Durations)
    longest_queue: int = 0  # conversions waiting at once
    peak_sandbox_memory: int = 0  # bytes, the most a sandbox used
    longest_sandbox_cpu_time: float = 0.0  # seconds, the most a sandbox used


class Statistics:
    def __init__(self, wall_clock: WallClock) -> None:
        self._wall_clock = wall_clock
        self._since_start = Counts()
        self._today = Counts()
        self._day: date | None = None
        self._waiting = 0
        self._running = 0

    def ended(self, outcome: str) -> None:
        """A conversion ended: finished, refused, failed, timed out, cancelled, or over the allowance."""
        for counts in self._counts():
            counts.conversions[outcome] += 1

    def pages(self, kinds: Counter[str]) -> None:
        """A finished conversion's pages, by kind."""
        for counts in self._counts():
            counts.pages.update(kinds)

    def refused(self, kind: str) -> None:
        """An upload refused, or a source file the sandbox refused. It is logged too, by its kind."""
        _log.info("refused: %s", kind)
        for counts in self._counts():
            counts.refusals[kind] += 1

    def bot_check_failed(self, why: str) -> None:
        for counts in self._counts():
            counts.bot_check_failures[why] += 1

    def ran(self, seconds: float) -> None:
        for counts in self._counts():
            counts.run_times.add(seconds)

    def waited(self, seconds: float) -> None:
        for counts in self._counts():
            counts.queue_waits.add(seconds)

    def queue(self, waiting: int, running: int) -> None:
        """The queue as it is now."""
        self._waiting, self._running = waiting, running
        for counts in self._counts():
            counts.longest_queue = max(counts.longest_queue, waiting)

    def used(self, usage: Usage) -> None:
        """What a sandbox used."""
        for counts in self._counts():
            counts.peak_sandbox_memory = max(counts.peak_sandbox_memory, usage.peak_memory)
            counts.longest_sandbox_cpu_time = max(counts.longest_sandbox_cpu_time, usage.cpu_time)

    def report(self) -> dict[str, Any]:
        """Every counter, as the operator reads them."""
        self._counts()  # so that a new day shows today's counts afresh
        return {
            "day": str(self._day),
            "queue": {"waiting": self._waiting, "running": self._running},
            "since_start": _reported(self._since_start),
            "today": _reported(self._today),
        }

    def _counts(self) -> tuple[Counts, Counts]:
        """The counts since the start and today's. A new day starts today's afresh, from the
        queue as it is."""
        today = self._wall_clock().astimezone(BANGKOK).date()
        if today != self._day:
            self._day, self._today = today, Counts(longest_queue=self._waiting)
        return self._since_start, self._today


def _reported(counts: Counts) -> dict[str, Any]:
    """The counts as plain data. Not `asdict`, which would rebuild each `Counter` from its items."""
    reported: dict[str, Any] = {}
    for counter in fields(counts):
        value = getattr(counts, counter.name)
        reported[counter.name] = asdict(value) if isinstance(value, Durations) else value
    return reported


def main() -> int:
    """`pdf-to-doc-statistics`: print the counters of the web app running beside it, as the
    operator reads them inside its container."""
    try:
        response = httpx.get(f"http://127.0.0.1:{PORT}/", timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as error:
        print(f"pdf-to-doc-statistics: {type(error).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
