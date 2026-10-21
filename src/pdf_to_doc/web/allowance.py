"""The daily page allowance: so many pages a day for each client address, every page of a
source file counted. The day runs from midnight to midnight, Bangkok time. The counts are held
in memory only, and lost on restart."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# Bangkok's time: Thailand keeps no daylight saving time, so a fixed offset is exact, and needs
# no time zone database, which Windows lacks.
BANGKOK = timezone(timedelta(hours=7))

WallClock = Callable[[], datetime]  # the date and time now, aware of its time zone


@dataclass(frozen=True)
class Charge:
    """Pages charged to a client's allowance, on a day."""

    client_ip: str
    pages: int
    day: date


class Allowance:
    def __init__(self, pages_per_day: int, wall_clock: WallClock) -> None:
        self._pages_per_day = pages_per_day
        self._wall_clock = wall_clock
        self._day: date | None = None
        self._used: dict[str, int] = {}  # today's pages, by client address

    def charge(self, client_ip: str, pages: int) -> Charge | None:
        """Charge the pages to the client, if they fit in what it has left today."""
        used = self._today().get(client_ip, 0)
        if used + pages > self._pages_per_day:
            return None
        self._used[client_ip] = used + pages
        return Charge(client_ip, pages, self._day_now())

    def give_back(self, charge: Charge) -> None:
        """Give charged pages back, unless the day they were charged on has passed."""
        if charge.day == self._day_now() and charge.client_ip in self._today():
            self._used[charge.client_ip] -= charge.pages

    def left(self, client_ip: str) -> int:
        """How many pages the client may still convert today."""
        return self._pages_per_day - self._today().get(client_ip, 0)

    def _today(self) -> dict[str, int]:
        """Today's counts. A new day starts them afresh, and the old ones leave memory."""
        today = self._day_now()
        if today != self._day:
            self._day, self._used = today, {}
        return self._used

    def _day_now(self) -> date:
        return self._wall_clock().astimezone(BANGKOK).date()
