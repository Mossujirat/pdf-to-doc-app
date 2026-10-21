# 03: Tracer bullet: convert a file on the web page

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A visitor opens the home page and picks or drops a PDF or DOCX. They land on the conversion's own page, which shows progress until the result appears:
- the summary
- a button that copies the Markdown
- downloads of the Markdown and the DOCX, named after the source file

A DOCX source gives Markdown only. Only the browser that sent the file can open its page.

The pages are plain for now; ticket 11 designs them. The web app reaches conversions through a sandbox interface that has two implementations here:
- **a fake, for tests,** which runs the real conversion function in process
- **a local sandbox, for development,** which runs the sandbox entry point as a subprocess

The launcher (ticket 09) becomes the production implementation.

**Blocked by:** 02

**Status:** done

**Branch:** `feat/web-core`

**Web app**
- [x] A FastAPI app in the package, served by uvicorn as one role of the same image. New dependencies are pinned and AGPL-compatible.
- [x] The home page takes one file, picked or dropped. The upload is multipart, and is refused past 50 MB: from `Content-Length` when it is sent, otherwise while reading.
- [x] Access to a conversion:
  - Each conversion gets an identifier of at least 128 random bits, in its link.
  - The browser gets a random token in a cookie: HttpOnly, SameSite=Strict, lasting one day, and Secure everywhere but local development.
  - Every request about a conversion needs both the link and the token that created it. Anything else gets one plain "not found" page.
- [x] The conversion page asks for its state every 2 seconds, and shows the stage and the OCR page as current of total.
- [x] The result shows:
  - the summary: pages, OCR pages, untrusted text layers, placeholders
  - a button that copies the Markdown
  - downloads of the Markdown and the DOCX
- [x] Downloads are named after the source file, and Thai names come through correctly.
- [x] The source file's bytes are released when the conversion ends. Its name is kept in memory only, to name the downloads.

**Sandbox interface**
- [x] The web app knows conversions only through the sandbox interface, which offers two operations:
  - run a source file, which streams back events and outputs
  - cancel
- [x] What comes back from a sandbox is untrusted, so the web app validates every event.
- [x] The web app never parses a source file itself.
- [x] The local sandbox runs the entry point in a subprocess, so the service works on a developer's machine without Docker.

**Tests**
- [x] HTTP tests through the app, with a fake sandbox running the real conversion function and the fake OCR engine:
  - a mixed PDF: upload, progress, result, and both downloads read back with the Markdown and DOCX test readers
  - a DOCX gives Markdown only
  - another browser's token, and an unknown link, both get "not found"
  - a Thai file name names the downloads
- [x] The web tests run in CI inside the image, with the other tests.

## Comments

**2026-10-21, how it is built**

**Dependencies.** Each version below was at least two weeks old when added, and every licence is MIT, BSD-3-Clause or Apache-2.0:

| Package | Version |
|---|---|
| fastapi | 0.142.4 (2026-10-07). 0.156.4 came out the day before. |
| uvicorn | 0.54.0 |
| python-multipart | 0.0.32 |
| pydantic | 2.14.1 |
| starlette | 1.7.0 (in the lock only, as the code imports through `fastapi`) |
| httpx | 0.28.1 (dev, for the test client) |

pydantic and httpx were already in the lock through PaddleX. FastAPI has depended on `opentelemetry-api` since 0.142. That API does nothing unless an SDK is installed, and none is.

**The code** is in `src/pdf_to_doc/web/`:
- `app.py`: the routes and `pdf-to-doc-web`
- `conversions.py`: state in memory
- `protocol.py`: validates what a sandbox sends, with pydantic in strict mode, unknown fields refused
- `sandboxes.py`: the interface and the local sandbox
- `upload.py`
- `pages.py`
- `static/app.js`

**Routes:**

| Route | What it does |
|---|---|
| `GET /` | the home page |
| `POST /conversions` | the upload; redirects to the conversion's page |
| `GET /conversions/{id}` | the conversion's page |
| `GET /conversions/{id}/state` | the JSON the page asks for every 2 seconds: the state and its text |
| `GET /conversions/{id}/markdown`, `GET /conversions/{id}/docx` | the downloads |

The page shows the state when it loads. `app.js` then polls and reloads the page once the conversion has ended. There is no inline script.

**The sandbox interface:**
- `Sandbox.convert(source)` is an async generator. It yields each event line as it comes, then `Ended(exit_code, stdout)`.
- Cancelling means closing it. That happens when the task that reads it is cancelled, or with `aclose()`. The local sandbox then kills its process.
- Ticket 04 will need a handle from each conversion to its task, to cancel it; `Conversions` keeps only an anonymous set for now.
- The fake sandbox for tests runs the real entry point in a thread, which cannot be stopped. Ticket 04's scripted sandbox covers cancelling.

**What comes back from a sandbox:**
- A conversion is finished only with a summary, exit code 0 and well-framed parts that include Markdown.
- It is refused only with a refusal event and a non-zero exit.
- Anything else fails: an unknown field, a line that is not JSON, an event after the last one, or a part shorter than it says.
- Names that reach the page, such as the OCR engine's, must be short ASCII names, so a sandbox cannot put document text on the page.

**Upload:** read with python-multipart's streaming parser and held in memory, never in a temp file. Starlette's own form parser writes files over 1 MB to disk.
- A declared `Content-Length` over 50 MB plus 64 KB of form framing is refused without reading the body. An ASGI-level test checks that the body is never asked for.
- Without a length, reading stops at the same point. By hand, against the real server, a chunked 300 MB upload got 413, and the server process peaked at 185 MB of memory.
- uvicorn reads and discards the rest of such a body, so the client still sends it all.

**The cookie token** is 32 random bytes. A cookie that does not look like one this app made is replaced.

**Local development:** `uv run pdf-to-doc-web` serves at 127.0.0.1:8000.
- It uses the local sandbox, a cookie without Secure, and no access log.
- By hand, a corpus PDF with an OCR page went through it with real PaddleOCR: the page showed each stage, the result, and a Thai download name.

**2026-10-21, after code review**

**Fixed:**
- The test that another browser gets "not found" opened a second app, so it would have passed without the token check. It now uses the same app, and fails when the token check is taken out.
- The test of a refused `Content-Length` never reached that check. A test now speaks ASGI to the app, and fails when the check is taken out.
- An OCR engine's name from the sandbox reached the page as any string. It must now be a short ASCII name.
- The routes are async, so they read a conversion on the event loop that changes it. Before, they ran in a thread pool, which could race once outputs are deleted (ticket 05).
- The code imported Starlette directly, which is not pinned in `pyproject.toml`. It now imports through FastAPI.
- A cookie the app did not make was taken as a token.
- The literals repeated in `protocol.py` now come from the converter's own types:
  - `Stage` in `progress.py`
  - `Unconverted` and `SizeUnit` in `intake.py`
  - `SUFFIXES` in `conversion.py`, shared with the CLI

**Not done:**
- **The JavaScript has not been run in a browser:** polling, reloading, copying and dropping a file. Ticket 11 checks it in mobile browsers. Until then, try `pdf-to-doc-web` by hand.
- **The web process imports the converter's modules** (PyMuPDF, python-docx), because `protocol.py` and `pages.py` use their types and limits. It never parses a source file with them. Moving those types and limits into light modules would trim the web process's memory, about 96 MB idle when measured.
