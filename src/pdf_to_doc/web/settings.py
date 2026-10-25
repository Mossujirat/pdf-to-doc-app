"""The web service's settings, and the values it runs with unless told otherwise.

Its containers take them from the environment: each setting as `PDF_TO_DOC_` and its name in
capitals, such as `PDF_TO_DOC_MAX_RUNNING`.
"""

import math
import os
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import MISSING, dataclass, fields
from typing import TYPE_CHECKING, Literal, TypeVar, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_PREFIX = "PDF_TO_DOC_"
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})


class Misconfigured(Exception):
    """The settings hold a value they cannot take, or would let the public service run unsafely,
    so the service refuses to start."""


@dataclass(frozen=True)
class Settings:
    max_running: int = 3  # conversions converting at once
    max_waiting: int = 20  # conversions waiting for one of those places
    # Bytes the outputs of ended conversions may hold in memory, 1 GB. At or over it, an upload is
    # refused as when the queue is full, and none waiting starts: only those running may add their
    # outputs on top.
    max_held_outputs: int = 1024 * 1024 * 1024
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
    # Where conversions run: in the launcher's sandboxes (ADR 0004), or, for development on a
    # machine without Docker, in a process of the machine's own.
    sandbox: Literal["launcher", "local"] = "launcher"
    # The commit the image was built from, which the Dockerfile records: every page links to the
    # source code at that commit, as the AGPL asks of a public service (ADR 0002).
    build_commit: str | None = None


# Where the launcher runs. Its sandboxes are named for it: staging's and production's share the
# server's Docker.
Environment = Literal["production", "staging", "local"]


@dataclass(frozen=True)
class LauncherSettings:
    environment: Environment
    # gVisor. Docker's own runtime, runc, serves local development, and is ADR 0004's fallback.
    sandbox_runtime: str = "runsc"
    time_limit: float = 30 * 60  # seconds a conversion may run in its sandbox


AnySettings = TypeVar("AnySettings", bound="DataclassInstance")


def from_environment(settings: type[AnySettings], environment: Mapping[str, str] = os.environ) -> AnySettings:
    """The `settings`, each one as the environment gives it, and otherwise its default. An empty
    value counts as not given. Raises `Misconfigured` for a value a setting cannot take, or for a
    setting with no default that is not given; it names the variable, but never the value,
    which could be a secret."""
    types = get_type_hints(settings)
    values: dict[str, object] = {}
    for field in fields(settings):
        name = _PREFIX + field.name.upper()
        if text := environment.get(name, ""):
            values[field.name] = _parsed(text, types[field.name], name)
        elif field.default is MISSING:
            raise Misconfigured(f"{name} must be set")
    return settings(**values)


def _parsed(text: str, wanted: object, name: str) -> object:
    """The value `text` gives a setting of the type `wanted`. A number of seconds must be more
    than none, and finite."""
    if wanted is bool and text.lower() in _TRUE | _FALSE:
        return text.lower() in _TRUE
    if wanted is int and text.isascii() and text.isdigit():
        return int(text)
    if wanted is float:
        with suppress(ValueError):
            if math.isfinite(seconds := float(text)) and seconds > 0:
                return seconds
    if get_origin(wanted) is Literal and text in get_args(wanted):
        return text
    if wanted in (str, str | None):
        return text
    raise Misconfigured(f"{name} holds a value it cannot take")
