"""A clock the test moves on, in place of the web app's clocks: the monotonic one that times
how long outputs are kept, and the wall clock that tells the day."""

from datetime import UTC, datetime, timedelta

# Noon in Bangkok, 2026-10-21.
_START = datetime(2026, 10, 21, 5, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0  # seconds

    def __call__(self) -> float:
        return self.now

    def wall(self) -> datetime:
        """The date and time, moving on with `now`."""
        return _START + timedelta(seconds=self.now)

    def advance(self, seconds: float) -> None:
        """Move time on. Called from the test's thread: the app reads `now`, a single float."""
        self.now += seconds
