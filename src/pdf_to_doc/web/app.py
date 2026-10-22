"""The web app: a browser uploads a source file, follows its conversion, and takes the outputs.

Every request about a conversion needs both its link and the token, in a cookie, of the
browser that started it. Anything else gets the same "not found" page. The routes are
all async, so that they read a conversion on the event loop that changes it.
"""

import argparse
import asyncio
import logging
import secrets
import string
import sys
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import get_args
from urllib.parse import quote, urlsplit

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from pdf_to_doc.conversion import SUFFIXES, OutputFormat
from pdf_to_doc.web import pages
from pdf_to_doc.web.allowance import Allowance, WallClock
from pdf_to_doc.web.bot_check import CLOUDFLARE, TOKEN_FIELD, BotCheck
from pdf_to_doc.web.client_ip import ClientIp
from pdf_to_doc.web.conversions import AlreadyConverting, Clock, Conversion, Conversions, QueueFull
from pdf_to_doc.web.launcher import LauncherSandbox
from pdf_to_doc.web.sandboxes import LocalSandbox, Sandbox
from pdf_to_doc.web.settings import Misconfigured, Settings, from_environment
from pdf_to_doc.web.statistics import PORT as STATISTICS_PORT
from pdf_to_doc.web.statistics import Statistics
from pdf_to_doc.web.upload import NotAnUpload, UploadTooLarge, read_upload

COOKIE = "browser"
_log = logging.getLogger(__name__)
_DAY = 24 * 60 * 60
_TOKEN_BYTES = 32
_TOKEN_LENGTH = len(secrets.token_urlsafe(_TOKEN_BYTES))
_TOKEN_CHARACTERS = frozenset(string.ascii_letters + string.digits + "-_")  # URL-safe base64
_STATIC = Path(__file__).parent / "static"
# How often expired conversions are looked for when no request comes, in seconds.
_FORGET_EVERY = 15
_MEDIA_TYPES: dict[OutputFormat, str] = {
    "markdown": "text/markdown; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# `pdf-to-doc-web --dev`, on a developer's machine.
_DEVELOPMENT = Settings(sandbox="local", secure_cookies=False, bot_check_test_mode=True)
# This site alone, and Cloudflare's for the bot check's script and frame, as Turnstile asks
# (developers.cloudflare.com, read 2026-10-21). There is no inline script or style.
_CONTENT_SECURITY_POLICY = (
    f"default-src 'self'; script-src 'self' {CLOUDFLARE}; frame-src {CLOUDFLARE}; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


def _now() -> datetime:
    return datetime.now(UTC)


def create_app(
    sandbox: Sandbox,
    settings: Settings = Settings(),
    clock: Clock = time.monotonic,
    wall_clock: WallClock = _now,
    cloudflare: httpx.AsyncBaseTransport | None = None,
    statistics: Statistics | None = None,
) -> FastAPI:
    """The web app, converting in `sandbox`. `clock` times how long outputs are kept, `wall_clock`
    tells the day for the allowance and the statistics, `cloudflare` stands in for Cloudflare in
    tests, and `statistics` counts how the service is used, for `statistics_app`. Raises
    `Misconfigured` for a public service whose bot check would not really check, that cannot tell
    its clients apart, that would convert outside the launcher's sandboxes, or whose cookie would
    not be Secure, so that it never starts."""
    bot_check = BotCheck.from_settings(settings, cloudflare)
    client_ip = ClientIp.from_settings(settings)
    if settings.production and settings.sandbox != "launcher":
        raise Misconfigured("the public service converts only in the launcher's sandboxes")
    if settings.production and not settings.secure_cookies:
        raise Misconfigured("the public service's cookie must be Secure")
    statistics = statistics or Statistics(wall_clock)
    conversions = Conversions(
        sandbox,
        Allowance(settings.pages_per_day, wall_clock),
        statistics,
        max_running=settings.max_running,
        max_waiting=settings.max_waiting,
        keep_for=settings.keep_for,
        clock=clock,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        forgetting = asyncio.create_task(conversions.forget_expired_every(_FORGET_EVERY))
        _log.info("started")
        yield
        forgetting.cancel()
        await conversions.stop()
        _log.info("stopped")

    # There is no API for programs, so no API documentation either.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")

    @app.middleware("http")
    async def guard(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Every request that changes something, an upload, a cancel or a delete, must come from
        one of this site's own pages; an upload is refused before it is read. The site loads
        nothing from elsewhere but the bot check, and tells no other site where a visitor came
        from. A conversion's pages and downloads are neither cached nor indexed. An unexpected
        error is logged by its type and its route alone: its message could quote a conversion,
        and the address holds the conversion's link."""
        if request.method not in ("GET", "HEAD") and not from_this_site(request):
            response: Response = refuse("another site", pages.from_another_site(), 403)
        else:
            try:
                response = await call_next(request)
            except Exception as error:
                route = getattr(request.scope.get("route"), "path", "an unknown route")
                _log.error("failed: %s at %s", type(error).__name__, route)
                response = HTMLResponse(pages.unexpected_error(), status_code=500)
        response.headers.setdefault("Content-Security-Policy", _CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Not no-referrer: a browser then names no origin on a form it posts, so that the
        # checks on where a request came from would refuse every cancel and delete.
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.url.path.startswith("/conversions"):  # the answer to an upload too
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("X-Robots-Tag", "noindex")
        return response

    def refuse(kind: str, page: str, status_code: int) -> HTMLResponse:
        statistics.refused(kind)
        return HTMLResponse(page, status_code=status_code)

    def from_this_site(request: Request) -> bool:
        """Whether a request that changes something came from one of this site's own pages, by
        the origin the browser names: the site is its hostname, or without one, wherever the
        request was sent. Another site's page can make a browser post to this one, but cannot
        make it name this site as the origin."""
        origin = request.headers.get("origin")
        site = settings.hostname or request.headers.get("host")
        return origin is not None and site is not None and urlsplit(origin).netloc == site

    @app.exception_handler(404)
    async def not_found(request: Request, error: Exception) -> HTMLResponse:
        return HTMLResponse(pages.not_found(settings.keep_for), status_code=404)

    @app.get("/health")
    async def health() -> PlainTextResponse:
        return PlainTextResponse("ok")

    def conversion_or_404(request: Request, identifier: str) -> Conversion:
        conversion = conversions.get(identifier, request.cookies.get(COOKIE))
        if conversion is None:
            raise HTTPException(404)
        return conversion

    @app.get("/")
    async def home() -> HTMLResponse:
        return HTMLResponse(pages.home(bot_check.site_key, settings.keep_for, settings.pages_per_day))

    @app.post("/conversions")
    async def start(request: Request) -> Response:
        try:
            upload = await read_upload(request)
        except UploadTooLarge:
            return refuse("too large", pages.too_large(), 413)
        except NotAnUpload:
            return refuse("not an upload", pages.not_an_upload(), 400)
        verdict = await bot_check.check(upload.fields.get(TOKEN_FIELD))
        if verdict != "passed":
            _log.info("upload refused by the bot check: %s", verdict)
            statistics.bot_check_failed(verdict)
            return HTMLResponse(pages.bot_check_failed(), status_code=403)
        token = _token(request.cookies.get(COOKIE))
        try:
            identifier = conversions.start(upload.source, upload.file_name, token, client_ip.of(request))
        except AlreadyConverting as converting:
            return refuse("one at a time", pages.already_converting(converting.identifier), 409)
        except QueueFull:
            return refuse("queue full", pages.queue_full(), 503)
        response = RedirectResponse(f"/conversions/{identifier}", status_code=303)
        response.set_cookie(
            COOKIE, token, max_age=_DAY, secure=settings.secure_cookies, httponly=True, samesite="strict"
        )
        return response

    @app.get("/conversions/{identifier}")
    async def conversion_page(request: Request, identifier: str) -> HTMLResponse:
        conversion = conversion_or_404(request, identifier)
        time_left = None if conversion.ongoing else conversions.time_left(conversion)
        return HTMLResponse(pages.conversion_page(identifier, conversion, conversions.place(identifier), time_left))

    @app.get("/conversions/{identifier}/state")
    async def state(request: Request, identifier: str) -> JSONResponse:
        conversion = conversion_or_404(request, identifier)
        place = conversions.place(identifier)
        answer = {"state": conversion.state, "text": pages.status(conversion, place), "ongoing": conversion.ongoing}
        if conversion.ongoing:
            answer["steps"] = pages.steps(conversion, place)  # for the page to swap in
        return JSONResponse(answer)

    @app.post("/conversions/{identifier}/cancel")
    async def cancel(request: Request, identifier: str) -> Response:
        conversion_or_404(request, identifier)
        conversions.cancel(identifier)
        return RedirectResponse(f"/conversions/{identifier}", status_code=303)

    @app.post("/conversions/{identifier}/delete")
    async def delete(request: Request, identifier: str) -> HTMLResponse:
        conversion_or_404(request, identifier)
        conversions.forget(identifier)
        return HTMLResponse(pages.deleted())

    @app.get("/conversions/{identifier}/{output}")
    async def download(request: Request, identifier: str, output: str) -> Response:
        conversion = conversion_or_404(request, identifier)
        found = next((known for known in get_args(OutputFormat) if known == output and known in conversion.outputs), None)
        if found is None:
            raise HTTPException(404)
        headers = {"Content-Disposition": _attachment(conversion.file_name, SUFFIXES[found]), "Referrer-Policy": "no-referrer"}
        return Response(conversion.outputs[found], media_type=_MEDIA_TYPES[found], headers=headers)

    return app


def statistics_app(statistics: Statistics) -> FastAPI:
    """The operator's counters, for a listener of their own on the loopback address alone, which
    the public one never forwards to."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/")
    async def counters() -> JSONResponse:
        return JSONResponse(statistics.report())

    return app


class _SecondServer(uvicorn.Server):
    """A second server in the process. The first one takes the signals, and this one stops after it."""

    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


async def _serve(public: uvicorn.Server, statistics: _SecondServer) -> None:
    """Serve the public app and the statistics side by side, until the public server is stopped."""
    serving_statistics = asyncio.create_task(statistics.serve())
    try:
        await public.serve()
    finally:
        statistics.should_exit = True
        await serving_statistics


def main(argv: list[str] | None = None) -> int:
    """Serve the web app with its settings from the environment, as its container does. With
    `--dev`, for local development, it ignores them: conversions run in subprocesses, the cookie
    is not Secure, so that it works over plain HTTP, and the bot check uses Cloudflare's test keys."""
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc-web",
        description="เปิดเว็บแปลงไฟล์ ตามค่าที่ตั้งไว้ใน environment (PDF_TO_DOC_...)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="สำหรับพัฒนาบนเครื่องนี้: แต่ละการแปลงรันใน process ของตัวเองโดยไม่มี sandbox, "
        "cookie ใช้ได้กับ http และ bot check ใช้ test key ของ Cloudflare",
    )
    parser.add_argument("--host", default="127.0.0.1", help="ที่อยู่ที่รับการเชื่อมต่อ (ค่าเริ่มต้น: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="พอร์ต (ค่าเริ่มต้น: 8000)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # it would log each bot check sent to Cloudflare
    try:
        settings = _DEVELOPMENT if args.dev else from_environment(Settings)
        sandbox: Sandbox = LocalSandbox() if settings.sandbox == "local" else LauncherSandbox.at()
        statistics = Statistics(_now)
        app = create_app(sandbox, settings, statistics=statistics)
    except (Misconfigured, NotImplementedError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    # The access log would record visitors' IP addresses and conversion links. The app reads the
    # client's address itself, from the trusted proxy alone: uvicorn would otherwise take
    # X-Forwarded-For from any local connection.
    public = uvicorn.Server(uvicorn.Config(app, host=args.host, port=args.port, access_log=False, proxy_headers=False))
    # On the loopback address of the machine, or container, the app runs on: nothing else reaches it.
    counters = statistics_app(statistics)
    statistics_server = _SecondServer(
        uvicorn.Config(counters, host="127.0.0.1", port=STATISTICS_PORT, access_log=False, lifespan="off")
    )
    asyncio.run(_serve(public, statistics_server))
    return 0


def _token(sent: str | None) -> str:
    """The browser's token: the one its cookie holds, if it is one this app could have made."""
    if sent and len(sent) == _TOKEN_LENGTH and set(sent) <= _TOKEN_CHARACTERS:
        return sent
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _attachment(file_name: str, suffix: str) -> str:
    """A download named after the source file. Thai names come through in `filename*`;
    a browser that reads only `filename` gets a plain one."""
    stem = PurePosixPath(file_name.replace("\\", "/")).stem[:100] or "document"
    name = stem + suffix
    plain = name if all(c.isascii() and (c.isalnum() or c in " ._-()") for c in name) else "document" + suffix
    return f"attachment; filename=\"{plain}\"; filename*=UTF-8''{quote(name, safe='')}"


if __name__ == "__main__":
    sys.exit(main())
