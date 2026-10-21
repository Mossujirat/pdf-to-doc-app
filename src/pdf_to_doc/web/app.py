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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import get_args
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from pdf_to_doc.conversion import SUFFIXES, OutputFormat
from pdf_to_doc.web import pages
from pdf_to_doc.web.allowance import Allowance, WallClock
from pdf_to_doc.web.bot_check import TOKEN_FIELD, BotCheck
from pdf_to_doc.web.client_ip import ClientIp
from pdf_to_doc.web.conversions import AlreadyConverting, Clock, Conversion, Conversions, QueueFull
from pdf_to_doc.web.sandboxes import LocalSandbox, Sandbox
from pdf_to_doc.web.settings import Settings
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


def create_app(
    sandbox: Sandbox,
    settings: Settings = Settings(),
    clock: Clock = time.monotonic,
    wall_clock: WallClock = lambda: datetime.now(UTC),
    cloudflare: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """The web app, converting in `sandbox`. `clock` times how long outputs are kept, `wall_clock`
    tells the day for the allowance, and `cloudflare` stands in for Cloudflare in tests. Raises
    `Misconfigured` for a public service whose bot check would not really check, or that cannot
    tell its clients apart, so that it never starts."""
    bot_check = BotCheck.from_settings(settings, cloudflare)
    client_ip = ClientIp.from_settings(settings)
    conversions = Conversions(
        sandbox,
        Allowance(settings.pages_per_day, wall_clock),
        max_running=settings.max_running,
        max_waiting=settings.max_waiting,
        keep_for=settings.keep_for,
        clock=clock,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        forgetting = asyncio.create_task(conversions.forget_expired_every(_FORGET_EVERY))
        yield
        forgetting.cancel()
        await conversions.stop()

    # There is no API for programs, so no API documentation either.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")

    @app.exception_handler(404)
    async def not_found(request: Request, error: Exception) -> HTMLResponse:
        return HTMLResponse(pages.not_found(settings.keep_for), status_code=404)

    def conversion_or_404(request: Request, identifier: str) -> Conversion:
        conversion = conversions.get(identifier, request.cookies.get(COOKIE))
        if conversion is None:
            raise HTTPException(404)
        return conversion

    @app.get("/")
    async def home() -> HTMLResponse:
        return HTMLResponse(pages.home(bot_check.site_key))

    @app.post("/conversions")
    async def start(request: Request) -> Response:
        try:
            upload = await read_upload(request)
        except UploadTooLarge:
            return HTMLResponse(pages.too_large(), status_code=413)
        except NotAnUpload:
            return HTMLResponse(pages.not_an_upload(), status_code=400)
        verdict = await bot_check.check(upload.fields.get(TOKEN_FIELD))
        if verdict != "passed":
            _log.info("upload refused by the bot check: %s", verdict)
            return HTMLResponse(pages.bot_check_failed(), status_code=403)
        token = _token(request.cookies.get(COOKIE))
        try:
            identifier = conversions.start(upload.source, upload.file_name, token, client_ip.of(request))
        except AlreadyConverting as converting:
            return HTMLResponse(pages.already_converting(converting.identifier), status_code=409)
        except QueueFull:
            return HTMLResponse(pages.queue_full(), status_code=503)
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
        text = pages.status(conversion, conversions.place(identifier))
        return JSONResponse({"state": conversion.state, "text": text, "ongoing": conversion.ongoing})

    @app.post("/conversions/{identifier}/cancel")
    async def cancel(request: Request, identifier: str) -> RedirectResponse:
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
        disposition = _attachment(conversion.file_name, SUFFIXES[found])
        return Response(conversion.outputs[found], media_type=_MEDIA_TYPES[found], headers={"Content-Disposition": disposition})

    return app


def main(argv: list[str] | None = None) -> int:
    """Serve the web app for local development: conversions run in subprocesses, the cookie is
    not Secure, so that it works over plain HTTP, and the bot check uses Cloudflare's test keys."""
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc-web",
        description="เปิดเว็บแปลงไฟล์บนเครื่องนี้ สำหรับพัฒนา: แต่ละการแปลงรันใน process ของตัวเอง โดยไม่มี sandbox",
    )
    parser.add_argument("--host", default="127.0.0.1", help="ที่อยู่ที่รับการเชื่อมต่อ (ค่าเริ่มต้น: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="พอร์ต (ค่าเริ่มต้น: 8000)")
    args = parser.parse_args(argv)
    # The access log would record visitors' IP addresses and conversion links.
    app = create_app(LocalSandbox(), Settings(secure_cookies=False, bot_check_test_mode=True))
    # The app reads the client's address itself, from the trusted proxy alone: uvicorn would
    # otherwise take X-Forwarded-For from any local connection.
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, proxy_headers=False)
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
