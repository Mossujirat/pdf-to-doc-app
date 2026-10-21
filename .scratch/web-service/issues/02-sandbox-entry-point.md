# 02: The sandbox entry point

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A command that converts one source file inside a container with no network. It reads the file's bytes from stdin, writes both outputs to stdout and reports events on stderr. This is what the launcher will run in every sandbox (ADR 0004). It can be tried by hand: pipe a corpus PDF into the image, run with no network and a read-only file system, and both outputs come back. OCR's thread count can be set, so that a 4-CPU sandbox is not three times slower.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Protocol**
- [ ] It reads the source file's bytes from stdin and takes no file name, path or password. Its only setting is the OCR thread count.
- [ ] It writes each output to stdout as a part named by its format, with its length.
- [ ] It writes events to stderr, one JSON object per line:
  - **opened:** the source type and the page count
  - **progress:** stage, current and total
  - **the summary,** as structured data: each page's kind and engine, whether its text layer was untrusted, and its placeholders by kind. The uncertain count joins it when converter ticket 11 lands.
  - **a refusal:** its kind, matching the intake error types, with the size and the limit when a file is too large
- [ ] Nothing else reaches stdout or stderr, Paddle's own output included. No event carries file content.
- [ ] Exit codes match the CLI's. An unexpected error gets an exit code of its own and an event that names only the error's type.
- [ ] A PDF that needs a password is refused as password required.

**OCR threads**
- [ ] The default OCR engine uses a configured number of CPU threads. Without the setting, it behaves as today.
- [ ] In the image, measure an OCR page at a 4-CPU limit, with the setting at 4 and without it. Record both numbers in this ticket's comments. The setting should bring the time back near the unrestricted one; on 2026-10-21 it was 3.3 seconds instead of 8.8.

**Tests**
- [ ] Fast tests run the entry point in process, with stdin and stdout replaced and the fake OCR engine, as the CLI's tests inject one. They cover:
  - the parts for a mixed PDF and for a DOCX
  - the events, in order
  - a refusal, with its exit code
- [ ] A test under the `ocr` marker runs it in a fresh process with real PaddleOCR, as the privacy tests do. It checks:
  - no network call
  - nothing left behind
  - no fragment of the document in its stderr beyond the events
- [ ] CI runs it once in the image with no network, beside the CLI's run.
