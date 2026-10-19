# 02: Quality harness + synthetic corpus v0

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A maintainer runs one CLI command over a corpus folder and gets a report showing how much broken text each page has against its reference text. The harness converts each source file through the conversion function, and works on the committed corpus or on any local folder, such as the confidential reference pages kept outside git. This ticket also adds the first version of the synthetic corpus generator, so fixtures come with exact reference text.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/text-pages`

**Corpus format**
- [x] Each source file has per-page reference text. The format is documented in the repo and is compatible with the hand-corrected `.reference.md` pages the user is preparing: Markdown text with HTML tables, Thai placeholders, and headers, footers and page numbers already removed.

**Comparison**
- [x] Both sides are normalised the same way: whitespace collapsed and NFC applied. NFKC is never applied.

**Report**
- [x] For each page and in total:
  - CER, overall and Thai-only
  - broken text by category: orphan marks, spaces inside words, Private Use Area characters, decomposed sara am, missing text (originally "missing lines"; see Comments)
  - page kind
  - OCR engine
  - uncertain-text count
- [x] Output as JSON and as a readable table.
- [x] Exit non-zero when a configured threshold is exceeded, so CI can use it as a gate.

**Synthetic generator v0**
- [x] Produces text-layer PDFs from known Thai and English text in at least two fonts. The cases include justified paragraphs and Thai–English line wraps.
- [x] The generator is reproducible: the same inputs give the same files.
- [x] Running the harness on the committed corpus shows zero broken text for the cases ticket 01 handles.

## Comments

**2026-10-17, implementation notes**

- **"Missing lines" became "missing text".** It counts runs of 10 or more reference characters that the output lacks altogether.
  - The first version scored each reference line, so the result depended on how the reference was wrapped.
  - It also missed repeated lines, and counted the same fault twice when spaces were inserted.
  - The new measure matches the glossary's "text that is missing altogether".
- **How spaces inside words are found.**
  - Letters are aligned with spaces removed, and each output space is placed between the two reference letters it falls between.
  - A plain character alignment chose arbitrarily between equal-cost options and missed a space that had moved ("ภาษาไ ทย" for "ภาษา ไทย").
- **CER totals.**
  - The corpus total is all edits over all reference characters.
  - A page with an empty reference still counts its output as error.
- **Visible text.**
  - Inline tags (`<mark>` for uncertain text) vanish without leaving a gap.
  - `<5`-style text is not mistaken for a tag.
  - Entities are decoded, and a byte order mark is ignored.
- **The harness fails instead of passing on an empty or badly laid-out corpus** (exit 2). The cases are: no folder, no reference text, a badly named reference file, or a reference for a page that does not exist.
- **Engine and uncertain counts are placeholders.** The `engine` and `uncertain` columns read `-` and 0 until tickets 08 and 11 put them in the conversion summary.
- **Second test font:** Niramit (OFL), beside Sarabun. The PDF builder and fonts moved from `tests/` to `corpus/`.
- **Escapes in source.** In this environment, the file-writing tools turn backslash-u escapes into literal characters, and the shell collapses double backslashes. The workaround is noted in CLAUDE.md.
