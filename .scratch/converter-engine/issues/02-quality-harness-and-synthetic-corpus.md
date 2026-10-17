# 02: Quality harness + synthetic corpus v0

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A maintainer runs one CLI command over a corpus folder and gets a report showing how much broken text each page has against its reference text. The harness converts each source file through the conversion function, and works on the committed corpus or on any local folder, such as the confidential reference pages kept outside git. This ticket also adds the first version of the synthetic corpus generator, so fixtures come with exact reference text.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/text-pages`

**Corpus format**
- [ ] Each source file has per-page reference text. The format is documented in the repo and is compatible with the hand-corrected `.reference.md` pages the user is preparing: Markdown text with HTML tables, Thai placeholders, and headers, footers and page numbers already removed.

**Comparison**
- [ ] Both sides are normalised the same way: whitespace collapsed and NFC applied. NFKC is never applied.

**Report**
- [ ] For each page and in total:
  - CER, overall and Thai-only
  - broken text by category: orphan marks, spaces inside words, Private Use Area characters, decomposed sara am, missing lines
  - page kind
  - OCR engine
  - uncertain-text count
- [ ] Output as JSON and as a readable table.
- [ ] Exit non-zero when a configured threshold is exceeded, so CI can use it as a gate.

**Synthetic generator v0**
- [ ] Produces text-layer PDFs from known Thai and English text in at least two fonts. The cases include justified paragraphs and Thai–English line wraps.
- [ ] The generator is reproducible: the same inputs give the same files.
- [ ] Running the harness on the committed corpus shows zero broken text for the cases ticket 01 handles.
