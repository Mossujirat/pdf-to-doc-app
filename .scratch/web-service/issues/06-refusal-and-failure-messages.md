# 06: Refusal and failure messages

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** Every source file the converter refuses gets a clear Thai message on the web page, in the same words as the CLI, from one shared table. The web adds messages of its own:
- **password-protected PDFs:** not supported yet; remove the password and send the file again
- **a conversion stopped by the time limit**
- **a conversion that failed**

The sandbox's own text is never shown. The web maps each refusal kind to its own message.

**Blocked by:** 03

**Status:** done

**Branch:** `feat/web-core`

**Messages**
- [x] The refusal messages move into one table that both the CLI and the web use. The CLI's output does not change, and its tests still pass.
- [x] The web shows a message for every intake refusal:
  - a legacy .doc
  - an Office file locked with a password
  - a file that is neither PDF nor DOCX
  - a DOCX that unpacks to more than 200 MB
  - a file over 50 MB
  - a file over 150 pages
  - a PDF that forbids copying
  - a damaged file
- [x] A PDF that needs a password gets the web's own message.
- [x] A failed conversion, and one stopped by the time limit, each get a message that tells the visitor to try again. Neither shows any detail from the sandbox.

**Tests**
- [x] HTTP tests with the fake sandbox running the real conversion function. They cover every refusal, using the corpus and test builders' files: legacy .doc, locked Office, password-protected and copy-protected PDFs, oversized files, damaged files.
- [x] A scripted sandbox covers failure and the time limit.

## Comments

**2026-10-21, how it works**

**The table** is `refusal_message(error)` in `src/pdf_to_doc/refusals.py`.
- It holds every message the CLI and the web share, word for word as the CLI had them. A script over the AST checked that each Thai string of the old `cli.py` is unchanged.
- It has no message for two refusals whose advice is about where the file was sent:
  - **a PDF that needs a password:** the CLI says to use `--password`. The web says it cannot convert password-protected PDFs yet, and to remove the password and send the file again.
  - **a DOCX asked to become a DOCX:** the CLI says to use `--to markdown`. The web never meets it, as it always asks for both outputs. If a sandbox sent it anyway, the page says only that the file cannot be converted.

**On the web, the message is drawn from the refusal's kind.**
- The page rebuilds the intake error from the validated refusal event and looks it up in the same table.
- The sandbox's text never reaches the page. Only its kind does, plus, for a file too large, a size that the schema bounds.
- The schema requires that a too-large refusal's limit equals the service's own, and that its size is above that limit.

**A file over 50 MB** never reaches the sandbox: the upload is refused first. Its message, `too_large_unmeasured`, also lives in the table. It keeps the CLI's phrasing without a size, because reading stops at the limit, before the whole file has come.

**The time limit** is the launcher's (ticket 09).
- The sandbox interface's `Ended` has `timed_out`, for the launcher to set.
- A conversion stopped that way is "failed", as the spec's states table says. Its page says it took too long and was stopped, and to try again.
- Any other failure says only to try again. The error a sandbox names is logged by type, never shown.

**For ticket 08:** the conversion page asserts that a refused conversion has its refusal event. If the allowance stop ends a conversion as refused, it needs a message of its own there.

**2026-10-21, after code review**
- **Fixed:** a too-large refusal could carry a number hundreds of digits long. The conversion read as refused, and its page then failed with an error each time it loaded. The schema now bounds the size and requires the service's own limit, so such an event fails the conversion.
- **Fixed:** the 50 MB message was written in `pages.py`. It now lives in the table.
- **Fixed:** the refusal kinds that carry nothing else are one `Literal`, and the table that rebuilds their errors is keyed by it. A test sends every such kind through a scripted sandbox and expects a message.
- **Fixed:** `RefusalEvent.error()` became `intake_error()`, as `FailureEvent.error` is a type name.
