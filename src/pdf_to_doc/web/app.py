"""The web app: a browser uploads a source file, follows its conversion, and takes the outputs.

Every request about a conversion needs both its link and the token, in a cookie, of the
browser that started it. Anything else gets the same "not found" page. The routes are
all async, so that they read a conversion on the event loop that changes it.
"""

import argparse
import secrets
import string
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from typing import get_args
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from pdf_to_doc.conversion import SUFFIXES, OutputFormat
from pdf_to_doc.web import pages
from pdf_to_doc.web.conversions import AlreadyConverting, Conversion, Conversions, QueueFull
from pdf_to_doc.web.sandboxes import LocalSandbox, Sandbox
from pdf_to_doc.web.settings import Settings
from pdf_to_doc.web.upload import NotAnUpload, UploadTooLarge, read_upload

COOKIE = "browser"
_DAY = 24 * 60 * 60
_TOKEN_BYTES = 32
_TOKEN_LENGTH = len(secrets.token_urlsafe(_TOKEN_BYTES))
_TOKEN_CHARACTERS = frozenset(string.ascii_letters + string.digits + "-_")  # URL-safe base64
_STATIC = Path(__file__).parent / "static"
_MEDIA_TYPES: dict[OutputFormat, str] = {
    "markdown": "text/markdown; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def create_app(sandbox: Sandbox, settings: Settings = Settings()) -> FastAPI:
    """The web app, converting in `sandbox`."""
    conversions = Conversions(sandbox, max_running=settings.max_running, max_waiting=settings.max_waiting)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await conversions.stop()

    # There is no API for programs, so no API documentation either.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")

    @app.exception_handler(404)
    async def not_found(request: Request, error: Exception) -> HTMLResponse:
        return HTMLResponse(pages.not_found(), status_code=404)

    def conversion_or_404(request: Request, identifier: str) -> Conversion:
        conversion = conversions.get(identifier, request.cookies.get(COOKIE))
        if conversion is None:
            raise HTTPException(404)
        return conversion

    @app.get("/")
    async def home() -> HTMLResponse:
        return HTMLResponse(pages.home())

    @app.post("/conversions")
    async def start(request: Request) -> Response:
        try:
            upload = await read_upload(request)
        except UploadTooLarge:
            return HTMLResponse(pages.too_large(), status_code=413)
        except NotAnUpload:
            return HTMLResponse(pages.not_an_upload(), status_code=400)
        token = _token(request.cookies.get(COOKIE))
        try:
            identifier = conversions.start(upload.source, upload.file_name, token)
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
        return HTMLResponse(pages.conversion_page(identifier, conversion, conversions.place(identifier)))

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
    """Serve the web app for local development: conversions run in subprocesses, and the cookie
    is not Secure, so that it works over plain HTTP."""
    parser = argparse.ArgumentParser(
        prog="pdf-to-doc-web",
        description="เปิดเว็บแปลงไฟล์บนเครื่องนี้ สำหรับพัฒนา: แต่ละการแปลงรันใน process ของตัวเอง โดยไม่มี sandbox",
    )
    parser.add_argument("--host", default="127.0.0.1", help="ที่อยู่ที่รับการเชื่อมต่อ (ค่าเริ่มต้น: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="พอร์ต (ค่าเริ่มต้น: 8000)")
    args = parser.parse_args(argv)
    # The access log would record visitors' IP addresses and conversion links.
    app = create_app(LocalSandbox(), Settings(secure_cookies=False))
    uvicorn.run(app, host=args.host, port=args.port, access_log=False)
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
