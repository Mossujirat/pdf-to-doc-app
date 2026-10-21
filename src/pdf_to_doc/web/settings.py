"""The web service's settings, and the values it runs with unless told otherwise."""

from dataclasses import dataclass


class Misconfigured(Exception):
    """The public service's settings would let it run unsafely, so it refuses to start."""


@dataclass(frozen=True)
class Settings:
    max_running: int = 3  # conversions converting at once
    max_waiting: int = 20  # conversions waiting for one of those places
    keep_for: float = 10 * 60  # seconds a conversion and its outputs are kept after it ends (ADR 0001)
    pages_per_day: int = 500  # for each client address, Bangkok's day
    # Where a client's address comes from: the header the trusted proxy (Tailscale's container)
    # sets, read only on requests from that proxy. Without both, it is the connection's address.
    trusted_proxy: str | None = None
    client_ip_header: str | None = None
    secure_cookies: bool = True  # off only in local development, over plain HTTP
    # The public service. It refuses to start unless the bot check would really check.
    production: bool = False
    # The bot check (Cloudflare Turnstile). Its test mode uses Cloudflare's test keys, for local
    # development and staging; otherwise the keys are the widget's own, made in Cloudflare's dashboard.
    bot_check_test_mode: bool = False
    turnstile_site_key: str | None = None
    turnstile_secret_key: str | None = None
    hostname: str | None = None  # where the pages are served, which Turnstile must confirm
