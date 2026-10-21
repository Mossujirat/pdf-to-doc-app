"""The web service's settings, and the values it runs with unless told otherwise."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    max_running: int = 3  # conversions converting at once
    max_waiting: int = 20  # conversions waiting for one of those places
    secure_cookies: bool = True  # off only in local development, over plain HTTP
