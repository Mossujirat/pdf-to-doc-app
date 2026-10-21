"""A clock the test moves on, in place of the web app's monotonic clock."""


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0  # seconds

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        """Move time on. Called from the test's thread: the app reads `now`, a single float."""
        self.now += seconds
