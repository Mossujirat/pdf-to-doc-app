# 13: DOCX source → Markdown

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user can convert a DOCX into Markdown for an AI chat with its headings, lists and tables intact, and with images shown as placeholders. A DOCX reader turns the Word structure straight into the document model, and the existing Markdown renderer produces the output. DOCX-to-DOCX is not offered.

**Blocked by:** 03, 04, 09

**Status:** ready-for-agent

**Branch:** `feat/docx`

**Reading the DOCX**
- [ ] Headings are detected from Word heading styles and rendered at the matching levels.
- [ ] Word lists, both numbered and bulleted, become Markdown lists.
- [ ] Tables, including merged cells, become document-model tables. Markdown then renders them as GFM or HTML tables, as for PDFs.
- [ ] Images become `[รูปภาพ]` placeholders.

**Text and output format**
- [ ] DOCX text passes through the character-level Thai repair: sara am recomposition and mark ordering. Line joining is not needed.
- [ ] Requesting DOCX output for a DOCX source gives a clear "not supported" message.

**Tests**
- [ ] Synthetic DOCX fixtures cover headings, lists, a merged-cell table, an image and Thai text. The harness shows zero broken text on them.

## Comments

**2026-10-19, handed over from ticket 05 (source intake)**

- **Intake already recognises DOCX** (a ZIP holding `word/document.xml`) and applies the 50 MB limit. `convert` then refuses it with `UnsupportedFormat("docx")`, and the CLI says DOCX cannot be converted yet. This ticket should remove that refusal, its CLI message and its test (`test_a_docx_is_recognised_but_not_converted_yet`).
- **The 150-page limit does not cover DOCX.** A DOCX has no pages until it is laid out. The page count Word saves in `docProps/app.xml` can be stale or missing. Decide whether DOCX needs a limit of its own, such as on paragraphs or file size alone.
- **A password-protected DOCX** is not a ZIP but an encrypted compound file, so intake reports it as "not a PDF or DOCX". Decide whether to recognise it and give a clearer message. Opening it would need a decryption library.
- `corpus/word_builder.py` has a minimal `docx()` builder that this ticket can extend or replace.
