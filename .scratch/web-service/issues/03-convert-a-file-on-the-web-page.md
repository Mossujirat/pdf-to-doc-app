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

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Web app**
- [ ] A FastAPI app in the package, served by uvicorn as one role of the same image. New dependencies are pinned and AGPL-compatible.
- [ ] The home page takes one file, picked or dropped. The upload is multipart, and is refused past 50 MB: from `Content-Length` when it is sent, otherwise while reading.
- [ ] Access to a conversion:
  - Each conversion gets an identifier of at least 128 random bits, in its link.
  - The browser gets a random token in a cookie: HttpOnly, SameSite=Strict, lasting one day, and Secure everywhere but local development.
  - Every request about a conversion needs both the link and the token that created it. Anything else gets one plain "not found" page.
- [ ] The conversion page asks for its state every 2 seconds, and shows the stage and the OCR page as current of total.
- [ ] The result shows:
  - the summary: pages, OCR pages, untrusted text layers, placeholders
  - a button that copies the Markdown
  - downloads of the Markdown and the DOCX
- [ ] Downloads are named after the source file, and Thai names come through correctly.
- [ ] The source file's bytes are released when the conversion ends. Its name is kept in memory only, to name the downloads.

**Sandbox interface**
- [ ] The web app knows conversions only through the sandbox interface, which offers two operations:
  - run a source file, which streams back events and outputs
  - cancel
- [ ] What comes back from a sandbox is untrusted, so the web app validates every event.
- [ ] The web app never parses a source file itself.
- [ ] The local sandbox runs the entry point in a subprocess, so the service works on a developer's machine without Docker.

**Tests**
- [ ] HTTP tests through the app, with a fake sandbox running the real conversion function and the fake OCR engine:
  - a mixed PDF: upload, progress, result, and both downloads read back with the Markdown and DOCX test readers
  - a DOCX gives Markdown only
  - another browser's token, and an unknown link, both get "not found"
  - a Thai file name names the downloads
- [ ] The web tests run in CI inside the image, with the other tests.
