"""The web service's settings, and the values it runs with unless told otherwise."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    max_running: int = 3  # conversions converting at once
    max_waiting: int = 20  # conversions waiting for one of those places
    keep_for: float = 10 * 60  # seconds a conversion and its outputs are kept after it ends (ADR 0001)
    secure_cookies: bool = True  # off only in local development, over plain HTTP
