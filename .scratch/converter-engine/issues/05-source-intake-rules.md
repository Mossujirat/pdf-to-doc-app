# 05: Source intake rules

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** When a user gives a file the converter cannot or will not convert, they get a clear message and a distinct exit code, never a crash or an empty output. The conversion function raises typed errors, and the CLI maps each one to a Thai message and its own exit code.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/text-pages`

**Type detection**
- [ ] The source type comes from the file content, not the extension. A PDF renamed to `.docx` is still read as a PDF.
- [ ] A legacy `.doc` (Word 97–2003) is refused with a message telling the user to save it as `.docx` first. DOCX sources are accepted by intake; converting them is ticket 13.

**Limits**
- [ ] A file over 50 MB or 150 pages is refused, and the message states the limit.

**Protected PDFs**
- [ ] A PDF that needs a password to open:
  - without a password: a "password required" error
  - with the correct password: converts
  - with a wrong password: a "wrong password" error
- [ ] A PDF whose permissions forbid copying text is refused, with a message explaining why.

**Tests**
- [ ] Each error case is covered through the conversion function and through the CLI's exit code, using small generated fixtures.
