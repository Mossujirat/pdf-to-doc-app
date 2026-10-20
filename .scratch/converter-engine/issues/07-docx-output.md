# 07: DOCX output

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user can choose DOCX as the output format and get an editable Word file with the same text and structure as the Markdown output. It is rendered from the same document model (ADR 0003). The DOCX keeps the original's structure, not its exact page layout.

**Blocked by:** 03, 04

**Status:** done

**Branch:** `feat/docx`

**Choosing DOCX**
- [x] The conversion function and the CLI accept DOCX as the output format.

**Fonts**
- [x] Thai text uses TH Sarabun New, set in the complex-script font slot together with the complex-script size. python-docx's plain font name does not set that slot.
- [x] English text uses a sensible default font. (TH Sarabun New too, at the user's choice; see the comments.)

**Structure**
- [x] Headings use Word's built-in heading styles at the right levels.
- [x] Lists use Word list formatting.
- [x] Tables are real Word tables, with merged cells where the document model has spans.
- [x] The summary appears on the first page.

**Tests**
- [x] Read DOCX outputs back and check the text against the reference text, the complex-script font and size, heading styles and merged cells.
- [x] Open one DOCX from the corpus in real Word and confirm that Thai renders correctly. Note the result in the ticket's comments.

## Comments

**2026-10-20, implementation notes**

- **Choices made with the user:**
  - Each page of the original starts a new page in Word. The page's first paragraph is set to break the page before it, or, for a page that starts with a table, the table's first paragraph. An empty page becomes one empty paragraph. While each page of the original fits on one Word page, page numbers match the original; a longer page pushes the rest back.
  - Items that had a bullet use Word's List Bullet. Items that keep their own number or letter ("1.", "(ก)") go in a Word list that shows nothing before them, so the number is not doubled by a bullet. The document model's list items now record whether they had a bullet (`ListItem.bulleted`), so the renderer does not guess.
  - English text is set in TH Sarabun New too, at the same size, so lines that mix Thai and English keep one size. This follows the report-writing kit and Thai official documents.
- **Thai in Word** (learned from the report-writing kit):
  - Word breaks Thai lines between words only in runs marked complex script (`<w:cs/>`). Without the mark it breaks only at spaces, so words split mid-word. Every run that holds Thai has the mark.
  - The mark also makes Word proof the whole run as Thai, so English words get runs of their own without it. Numbers alone stay with the Thai around them.
  - The document defaults name TH Sarabun New in all four font slots, with 16 pt in both size slots and Thai as the complex-script language.
  - python-docx's template has two problems in its heading styles. They name theme fonts, and a theme font wins over a font name set at the same level. Heading 1 is also 14 pt, smaller than the body. The styles now name TH Sarabun New, bold in both slots (`b` and `bCs`), black and upright: Heading 1 20 pt, Heading 2 18 pt, deeper levels 16 pt.
  - Thai bold needs `bCs` as well as `b`. The summary's label has both.
- **Layout.**
  - A4 with 2.54 cm margins. The template was US Letter.
  - Tables use Table Grid, with columns of equal width and real merged cells.
  - A paragraph after a table gets 10 pt of space above it, the space the template leaves between paragraphs. A heading has space above it already.
  - Two tables in a row get an empty paragraph between them, because Word joins tables that touch.
- **The summary** is the first paragraph, its label "สรุปการแปลง" in bold, as in the Markdown.
- **CLI.** `--to markdown` or `--to docx`. Without `--to`, an `--output` ending in `.docx` chooses DOCX and anything else chooses Markdown, so a `.docx` name gets a DOCX unless `--to` says otherwise. The default output name ends in `.md` or `.docx` to match.
- **Privacy.** The DOCX is written to memory. `tests/test_privacy.py` gains a fast test that converts a text page to DOCX in a fresh process: no network call, no file left in the temp area, and no document text in the log. `fresh_process` takes the output format, and returns the output as bytes.
- **Tests** (`tests/test_docx_output.py`, with `tests/docx_reader.py`):
  - The reader works out each run's fonts and sizes the way Word does: from the run, then the paragraph style and the styles it is based on, then the document defaults. A theme font at any level shows as a theme font, so the test fails if one is left.
  - It reads merged cells back from `gridSpan` and `vMerge` into rows of the cells that start in them, as the document model holds them.
  - A corpus test converts every committed source file to DOCX and requires each text page to match its reference text exactly: CER 0 and no broken text.
- **Each new test that passed at once was seen to fail on a deliberate break, which was then removed:**
  - The corpus test, with cell text dropped (CER 0.67 on page 1 of `tables`), and with page breaks dropped (the page count no longer matched).
  - The DOCX privacy test, with a temporary file written (left behind), and with each run logged at DEBUG (59 fragments found).
- **Checked in real Word** (Microsoft Word 16.0.20430 on Windows 11, TH Sarabun New installed), with the report-writing kit's `word_check.ps1`. The files were `page-structure.pdf` and `tables.pdf` from the corpus, plus a long paragraph mixing Thai and English made for the check.
  - Thai renders correctly in TH Sarabun New. Marks sit on their consonants (ผู้, ก้าว, สมบูรณ์), sara am is whole (จำนวน, ดำเนิน), and Thai digits show.
  - Word breaks Thai lines between words: "ฉบับที่ / หนึ่ง" in a table cell, "เศรษฐกิจ / ฐานชีวภาพ" and "ลง / นาม" in the paragraph. No line breaks inside a word.
  - The 4-page source gives 4 pages.
  - Word flags no spelling: no English word proofed as Thai, and no other flag.
  - Headings, both kinds of list item, and both tables, merged cells included, look right.
  - The first pass found the text after a table sitting on the table's bottom border. That was fixed as above and checked again.
- **Checked in the Linux image** (no network, read-only, `/tmp` in memory), after the review changes: mypy, the fast suite, `pytest -m ocr`, the harness gate, and a mounted conversion to DOCX all pass.
- **Left open:**
  - TH Sarabun New must be installed for Word to show it. It ships with neither Windows nor macOS, and without it Word substitutes another font. Embedding the font in the DOCX was not considered.
  - Column widths are equal, because the document model does not keep the original's widths.
  - The DOCX cannot hold a character that XML does not allow, such as a C0 control character, and building it would fail. None reaches the document model from a PDF: a text layer whose glyph maps to U+0003, U+001B, U+001F or U+007F fails validation and the page is read with OCR, and U+0008, U+000B and U+000C are dropped or become spaces. A new source of text, such as DOCX sources (ticket 13), must not pass them on either.
  - A glyph that maps to U+000B leaves a space inside a Thai word, and a short page still passes validation, because it has too few words for the dictionary check. That belongs to text-layer validation, not to this ticket.

**2026-10-20, changes after code review**

- **A new page no longer starts with a paragraph of its own.** The first version put each page break in an empty paragraph. In real Word, when the page before was full, that paragraph fell onto the next page and broke there, leaving a blank page. With 19 short paragraphs on page 1, the second page's text landed on page 3. The page's first paragraph now carries the break, as described above. Rechecked in real Word: 19 paragraphs give 2 pages; 20 or more give 3, because page 1 then really runs over; a page that starts with a table and an empty page each start a new page; the corpus files give the same pages as before.
- **The spec no longer says page numbers always match.** They match only while each page of the original fits on one Word page.
- **Control characters were checked, not handled:** see "Left open".
- **Tidying:** the deepest heading level lives in the document model, shared by layout and the renderer. The renderer's constants are private. The CLI reads the format from an output name through the same table it takes the default name from. `ListItem.bulleted` has no default. The test reader walks the style chain in one place. `README.md` says it is reading DOCX files that is not built yet.
- **Not changed:**
  - The CLI still chooses DOCX from a `.docx` output name. The reviewer counted it as unasked for; it keeps Markdown out of a file named `.docx`.
  - A4 and the heading sizes stay. The template's US Letter and its 14 pt Heading 1, smaller than the 16 pt body, would both have shown in Word.
  - The corpus test still repeats the corpus layout that `evaluate` reads, as the Markdown corpus test does through `evaluate`.
