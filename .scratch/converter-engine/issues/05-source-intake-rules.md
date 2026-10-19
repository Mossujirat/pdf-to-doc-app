# 05: Source intake rules

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** When a user gives a file the converter cannot or will not convert, they get a clear message and a distinct exit code, never a crash or an empty output. The conversion function raises typed errors, and the CLI maps each one to a Thai message and its own exit code.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/text-pages`

**Type detection**
- [x] The source type comes from the file content, not the extension. A PDF renamed to `.docx` is still read as a PDF.
- [x] A legacy `.doc` (Word 97–2003) is refused with a message telling the user to save it as `.docx` first. DOCX sources are accepted by intake; converting them is ticket 13.

**Limits**
- [x] A file over 50 MB or 150 pages is refused, and the message states the limit.

**Protected PDFs**
- [x] A PDF that needs a password to open:
  - without a password: a "password required" error
  - with the correct password: converts
  - with a wrong password: a "wrong password" error
- [x] A PDF whose permissions forbid copying text is refused, with a message explaining why.

**Tests**
- [x] Each error case is covered through the conversion function and through the CLI's exit code, using small generated fixtures.

## Comments

**2026-10-19, implementation notes**

- **Errors.** `convert` raises a subclass of `IntakeError`. The CLI prints a Thai message to stderr, writes no output file, and exits with that error's code. `pdf-to-doc --help` lists the codes.

  | Error | Exit code | When |
  |---|---|---|
  | `UnsupportedFormat` | 3 | `found` is `"doc"` (legacy Word), `"docx"` (not convertible yet), or `None` (anything else) |
  | `TooLarge` | 4 | `unit` is `"bytes"` or `"pages"`; it carries the size and the limit |
  | `PasswordRequired` | 5 | the PDF needs a password and none was given |
  | `WrongPassword` | 6 | the password does not open it |
  | `CopyRestricted` | 7 | the permissions forbid copying text |
  | `DamagedFile` | 8 | it looks like a PDF or DOCX but cannot be opened |

  Codes 1 and 2 are left to Python crashes and argparse. Error messages never quote the file's content.
- **Type detection**, from content only:
  - A ZIP archive holding `word/document.xml` is a DOCX. Any other ZIP is unsupported.
  - A compound file (the Office 97–2003 container) whose directory names a `WordDocument` stream is a legacy `.doc`. Other compound files, such as `.xls`, are unsupported.
  - Anything with `%PDF-` in its first 1 KB is a PDF; readers accept that much junk before the header.
- **DOCX is recognised and then refused** with `UnsupportedFormat("docx")`, because reading DOCX is ticket 13. Ticket 13 removes that refusal. Until then, the `.doc` message ("save it as .docx") points the user to a format this branch cannot convert yet.
- **Order of checks:** type, size, opening (damaged), password, copy permission, pages. Type comes before size, so a large `.doc` is told to become a `.docx`. A protected PDF has its pages counted only after it opens.
- **Limits.**
  - 50 MB means 50 MiB (52,428,800 bytes), which is how Windows reports file sizes.
  - Size is checked before the PDF is opened. Type detection runs first, but it only reads a ZIP's file list or scans a compound file's bytes.
  - A file just over the limit shows its size rounded up ("50.1 MB"), never as the limit itself.
- **Passwords.**
  - The owner password also opens a locked PDF.
  - Thai passwords work with AES-256 encryption; the tests use one.
  - A password given for a PDF that does not need one is ignored.
- **Copy restriction.**
  - PyMuPDF extracts text whatever the permissions say, so intake enforces them itself.
  - It reads the permissions the file declares, from its encryption dictionary. After the owner password opens a PDF, PyMuPDF reports every permission as granted, but the owner password still does not lift a copy restriction. The spec puts converting copy-forbidden PDFs out of scope.
- **PDF header.** A file with `%PDF-` in its first 1 KB that MuPDF cannot open is reported as damaged, even if it is really a text file that mentions a PDF header. MuPDF does open real PDFs with bytes before the header ("garbage bytes before version marker"), so the 1 KB window stays.
- **Added beyond the ticket: damaged files.** A truncated PDF or DOCX crashed the CLI with a traceback. It is now `DamagedFile`. MuPDF repairs many damaged PDFs silently, and only those it cannot open are refused. A PDF cut in half still opens, and converts with text missing.
- **Fixtures**, all generated in the tests:
  - `corpus/word_builder.py` writes a minimal DOCX and a `.doc` container. Both were checked once with `olefile` (strict mode) and `python-docx`. Neither library is a dependency.
  - `pdf_builder.protected` encrypts a PDF with AES-256. Its bytes differ on every run.
  - `pdf_builder.grown_to` pads a PDF to an exact size with a stream that nothing draws. Building a 50 MB file takes about 0.1 s.
- **Real contracts, checked locally.** Neither file is encrypted or copy-restricted, and both convert as before.
- **Left open:**
  - The CLI reads the whole file before `convert` refuses it for size. That is fine at 50 MB, but a file of several GB would be read into memory first. The web service will need its own upload cap.
  - DOCX questions are passed to ticket 13 (see its comments): removing the DOCX refusal, a page limit for DOCX, and password-protected DOCX.
  - The quality harness does not catch intake errors. A refused file in a corpus stops the evaluation with a traceback.

**2026-10-19, changes after code review**

- **The owner password no longer lifts a copy restriction.** Before, it did when the PDF also needed a password to open, but not when it opened freely. Both cases are now refused, and a test covers each.
- **A source path the CLI cannot read** (missing, or a folder) gives argparse's error with exit code 2 and a Thai message, instead of a traceback.
- **Tidying.**
  - `source_type` is renamed `admit`, because it also enforces the size limit.
  - The ZIP signature is written as hex, like the compound-file one.
  - The compound-file builder has one directory-entry layout, and produces the same bytes as before.
  - Duplicated test fixtures became helpers.
  - The PDF builder's docstring now says which builders give different bytes on each run.
- **Not changed:**
  - `UnsupportedFormat` and `TooLarge` keep a field for their sub-kinds rather than a class each. The spec lists them as one error type each, with one exit code.
  - The exit codes stay in three places in `cli.py`: the constants, the help text built from them, and the message mapping.
  - "Intake" and "refusal" are not added to `GLOSSARY.md`. Users never see them; they name code, not domain concepts.
