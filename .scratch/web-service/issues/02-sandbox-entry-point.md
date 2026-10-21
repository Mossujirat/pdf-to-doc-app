# 02: The sandbox entry point

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A command that converts one source file inside a container with no network. It reads the file's bytes from stdin, writes both outputs to stdout and reports events on stderr. This is what the launcher will run in every sandbox (ADR 0004). It can be tried by hand: pipe a corpus PDF into the image, run with no network and a read-only file system, and both outputs come back. OCR's thread count can be set, so that a 4-CPU sandbox is not three times slower.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/web-core`

**Protocol**
- [x] It reads the source file's bytes from stdin and takes no file name, path or password. Its only setting is the OCR thread count.
- [x] It writes each output to stdout as a part named by its format, with its length.
- [x] It writes events to stderr, one JSON object per line:
  - **opened:** the source type and the page count
  - **progress:** stage, current and total
  - **the summary,** as structured data: each page's kind and engine, whether its text layer was untrusted, and its placeholders by kind. The uncertain count joins it when converter ticket 11 lands.
  - **a refusal:** its kind, matching the intake error types, with the size and the limit when a file is too large
- [x] Nothing else reaches stdout or stderr, Paddle's own output included. No event carries file content.
- [x] Exit codes match the CLI's. An unexpected error gets an exit code of its own and an event that names only the error's type.
- [x] A PDF that needs a password is refused as password required.

**OCR threads**
- [x] The default OCR engine uses a configured number of CPU threads. Without the setting, it behaves as today.
- [x] In the image, measure an OCR page at a 4-CPU limit, with the setting at 4 and without it. Record both numbers in this ticket's comments. The setting should bring the time back near the unrestricted one; on 2026-10-21 it was 3.3 seconds instead of 8.8.

**Tests**
- [x] Fast tests run the entry point in process, with stdin and stdout replaced and the fake OCR engine, as the CLI's tests inject one. They cover:
  - the parts for a mixed PDF and for a DOCX
  - the events, in order
  - a refusal, with its exit code
- [x] A test under the `ocr` marker runs it in a fresh process with real PaddleOCR, as the privacy tests do. It checks:
  - no network call
  - nothing left behind
  - no fragment of the document in its stderr beyond the events
- [x] CI runs it once in the image with no network, beside the CLI's run.

## Comments

**2026-10-21, the protocol as built**

The command is `pdf-to-doc-sandbox`, in `src/pdf_to_doc/sandbox.py`. The launcher (ticket 09) checks what it writes against this.

**stdout:** one part per output, Markdown first.
- Each part is a line holding the format and the length in bytes, such as `markdown 495`, then exactly that many bytes.
- A DOCX source gives the Markdown part only.
- A refusal or failure writes nothing to stdout.

**stderr:** one JSON object per line, in ASCII, with Thai escaped. Every object has an `event`:

| Event | Fields |
|---|---|
| `opened` | `source_type` (`pdf` or `docx`), `pages` |
| `progress` | `stage` (`reading`, `ocr` or `writing`), `current`, `total`. Only `ocr` has a count; the other stages have `null` for both. A DOCX has no `reading` (ticket 01). |
| `summary` | `pages`: for each page, `number`, `kind` (`text` or `ocr`), `engine` (or `null`), `untrusted_text_layer`, `placeholders`, `uncertain` |
| `refusal` | `kind`: the intake error's type name, such as `TooLarge` or `PasswordRequired` |
| `failure` | `error`: the error's type name only, as its message could quote the document |

More about some of these fields:
- **`placeholders`** is the list of each placeholder's kind, in reading order, such as `["signature", "stamp"]`. Counts by kind follow from it.
- **A summary line** grows with the page count: about 120 bytes a page, so about 18 KB at 150 pages. The launcher's cap on line length must allow for that.
- **A refusal** carries more than the ticket asked, so that ticket 06 can tell every refusal apart:
  - `UnsupportedFormat` adds `found`: `doc`, `locked office` or `null`.
  - `TooLarge` adds `unit` (`bytes`, `pages` or `unpacked bytes`), `size` and `limit`.

**Exit codes** are the CLI's, now kept in `exit_codes.py` for both:

| Code | Meaning |
|---|---|
| 0 | done |
| 3–8 | a refusal |
| 9 | the OCR models are missing |
| 10 | any other error, reported by a `failure` event |
| 1 | a crash that could not be reported, as Python itself exits. It has no event. |

**Keeping other output out.** `main()` copies the standard streams for the parts and events, then points them at the null device. Whatever else is written to them, including Paddle's C++ output, logging and warnings, goes nowhere.
- This is tested in a fresh process under the `ocr` marker, and by CI. The fast tests call `run()` with replaced streams, so they don't cover it.
- Taking the redirect out made the `ocr` test fail on a line that was not JSON.

**The OCR thread count** is the environment variable `PDF_TO_DOC_OCR_THREADS`, read by the default engine, as `PDF_TO_DOC_MODELS` is.
- Ticket 09's container gets no other environment.
- The CLI honours it too, and the README tells Docker users to set it with `--cpus`.
- Unset, PaddleOCR keeps its default of 10 threads.

**2026-10-21, OCR page timing in the image**

Measured with Docker Desktop on the development machine (16 CPUs), not on `gmt`:
- the page: `corpus/synthetic/scanned-page.pdf`
- the method: one warm-up read, then the median of 3 reads

| Container | Seconds per page |
|---|---|
| no CPU limit, setting unset | 0.43 |
| `--cpus 4`, setting unset (10 threads) | 1.60 |
| `--cpus 4`, `PDF_TO_DOC_OCR_THREADS=4` | 0.61 |

Without the setting, a page took 2.6 times as long, as on `gmt` (8.8 seconds against 3.3). With it, the time came back near the unrestricted one. The synthetic page is smaller than a real contract's, so the absolute times are lower.

**2026-10-21, after code review**
- **Fixed:** the unexpected-error exit code was 1, Python's own, so a reported failure looked like a crash. It is now 10.
- **Fixed:** the exit codes moved out of `cli.py` into `exit_codes.py`, so the sandbox no longer imports the CLI.
- **Fixed:** a refusal's exit code is looked up before its event is sent.
- **Kept:** `PDF_TO_DOC_OCR_THREADS` is not checked before the first OCR page. The launcher sets it, and a bad value ends as a `failure` event naming `ValueError`.
