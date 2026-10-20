# 13: DOCX source → Markdown

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user can convert a DOCX into Markdown for an AI chat with its headings, lists and tables intact, and with images shown as placeholders. A DOCX reader turns the Word structure straight into the document model, and the existing Markdown renderer produces the output. DOCX-to-DOCX is not offered.

**Blocked by:** 03, 04, 09

**Status:** done

**Branch:** `feat/docx`

**Reading the DOCX**
- [x] Headings are detected from Word heading styles and rendered at the matching levels.
- [x] Word lists, both numbered and bulleted, become Markdown lists.
- [x] Tables, including merged cells, become document-model tables. Markdown then renders them as GFM or HTML tables, as for PDFs.
- [x] Images become `[รูปภาพ]` placeholders.

**Text and output format**
- [x] DOCX text passes through the character-level Thai repair: sara am recomposition and mark ordering. Line joining is not needed.
- [x] Requesting DOCX output for a DOCX source gives a clear "not supported" message.

**Tests**
- [x] Synthetic DOCX fixtures cover headings, lists, a merged-cell table, an image and Thai text. The harness shows zero broken text on them.

## Comments

**2026-10-19, handed over from ticket 05 (source intake)**

- **Intake already recognises DOCX** (a ZIP holding `word/document.xml`) and applies the 50 MB limit. `convert` then refuses it with `UnsupportedFormat("docx")`, and the CLI says DOCX cannot be converted yet. This ticket should remove that refusal, its CLI message and its test (`test_a_docx_is_recognised_but_not_converted_yet`).
- **The 150-page limit does not cover DOCX.** A DOCX has no pages until it is laid out. The page count Word saves in `docProps/app.xml` can be stale or missing. Decide whether DOCX needs a limit of its own, such as on paragraphs or file size alone.
- **A password-protected DOCX** is not a ZIP but an encrypted compound file, so intake reports it as "not a PDF or DOCX". Decide whether to recognise it and give a clearer message. Opening it would need a decryption library.
- `corpus/word_builder.py` has a minimal `docx()` builder that this ticket can extend or replace.

**2026-10-20, implementation notes**

- **Choices made with the user:**
  - **Pages are where Word last laid them out.** Word records, on saving, each place its layout began a new page (`w:lastRenderedPageBreak`). When a file holds those records, they alone start pages; a file without them, as other programs write, starts a page at each typed page break, and at a paragraph set to break the page before it unless a page has just begun.
  - **Limits:** the 150-page limit counts those pages, and a DOCX whose archive unpacks to more than 200 MB is refused as a zip bomb (`TooLarge` with unit "unpacked bytes", exit code 4). Reading a part of a zip never gives more than the size the archive lists for it, so the listed sizes are enough to check.
  - **A password-locked DOCX** (a compound file holding an `EncryptedPackage` stream) is recognised and refused: `UnsupportedFormat("locked office")`, exit code 3. A locked XLSX or PPTX looks the same until decrypted, so the Thai message says an Office file is locked, and tells a Word user to save it again without a password.
  - **List numbers are worked out as Word draws them** and kept as text, as on a text page: "1.", "๑.", "(ก)", "1.2", "IV.". A bullet is dropped, and Markdown's own "- " stands in. A list within a list is indented two spaces a level; list items now carry their level in the document model (`ListItem.level`, 0 on text pages, which tell no depth).
- **Word's own counting, checked in real Word.** A DOCX of 35 list paragraphs was numbered by Word (`ListFormat.ListString`, over COM) and by the reader; all 35 matched:
  - Thai letters skip the obsolete ฃ and ฅ (ก ข ค ง จ ฉ ช), and Thai digits run ๑ to ๑๒.
  - Counters belong to the abstract definition: a second instance of one definition counts on from the first, and only a start override restarts it, as Word's "Restart at 1" writes.
  - Numbering a level restarts the levels below it, unless the level says otherwise; legal numbering draws Arabic digits; a definition that only links to a list style is followed to the style's numbering.
- **Page records, checked in real Word.** Word saved a file with a typed break, long paragraphs and a 60-row table. It recorded a page start right after the typed break as well, so counting both would double it; its own records alone gave 6 pages, as Word counted. Two records fell inside paragraphs, and two inside the table.
  - A paragraph broken across pages becomes two paragraphs, one on each page.
  - A table sits on the page it starts on, or on the next one when Word began it on a new page. The pages it runs onto come out empty, so that later page numbers still match.
- **Text.**
  - Typed line breaks and tabs become spaces, and runs of spaces become one. A typed line break sets lines apart on purpose, such as a name above a title, and a GFM cell holds one line.
  - Text deleted with tracked changes on is left out; inserted text, links and the results of fields (such as page numbers) are kept, field codes are not.
  - Content controls are read through; headers and footers are page furniture and are not read.
  - A text box's text is kept, as paragraphs where the box sits, not as a picture; so is every box's in a group. A drawn shape with nothing in it gives nothing.
  - Text formatted as hidden, which Word neither shows nor prints, is left out.
- **Tables.** Merged cells come from `gridSpan` and `vMerge`; a row's `gridBefore` gives empty cells, so columns stay aligned. Rows and cells held in content controls, as Word's repeating sections hold them, are read too. A cell's paragraphs, and those of a table inside it, join with a space. A list paragraph in a cell counts in its list, as Word counts it. A picture in a cell is placed right after the table, as ticket 09 decided for PDFs.
- **Pictures.** A drawing holding a bitmap, a chart or a diagram, and a VML image, become `[รูปภาพ]` where they sit; a paragraph with text around a picture is cut there. Word writes some drawings twice, as themselves and as a fallback for older readers; only the first is read. Signatures and stamps are not told apart in a DOCX.
- **Refusals.** DOCX output for a DOCX source raises `DocxToDocx` (exit code 3). A DOCX that python-docx cannot open, such as one whose document XML is cut short, raises `DamagedFile`. The old "DOCX cannot be converted yet" refusal, its message and its test are gone.
- **Harness.** `evaluate` reads `<name>.docx` sources beside `<name>.pdf` ones. The corpus gains `word-structure.docx`, two pages: headings, a sara am stored as two characters, a numbered list, bullets, a merged-cell table, a picture, a Thai-English line and a Thai-letter list. Both pages score CER 0 with no broken text.
- **Fixtures.** `word_builder.document` builds DOCX files with python-docx and Word's own XML where python-docx has no call for it (numbering definitions, page records, tracked changes, fields, links); zip entries are dated alike so the bytes stay the same. `locked_docx` and `docx_unpacking_to` make the refused files.
- **Also checked in real Word:**
  - Word re-saved the corpus DOCX; its conversion gave the same text. Word laid it out on one page and recorded no page starts, so it came out as one page.
  - A DOCX made entirely by Word, with Word's heading style, its default numbering and bullets, and a table merged in Word, converted to the expected Markdown.
- **Privacy.** A DOCX source converts in memory: a fast test converts one in a fresh process, with no network call, no file left in the temp area and no document text in the log. It was seen to fail when the reader wrote a temporary copy.
- **Left open:**
  - Footnotes, endnotes and comments are not read.
  - Section breaks start no page in a file without Word's page records; Word's records cover them in files it saved.
  - A symbol inserted from a symbol font (`w:sym`) is left out.
  - Thai counting numbers (`thaiCounting`, Thai number words) and other rare formats are drawn in Arabic digits.
  - A list within a list keeps its depth in Markdown only. The DOCX renderer writes every list item at the outer level; it only renders PDFs, whose list items have no depth.

**2026-10-20, changes after code review**

The reviewer probed real Word XML shapes and checked several against Word over COM. Fixed:
- **A deeper level counted on under a new item above it.** The restart test ran the wrong way: for items at levels 0, 1, 2, 0, 2, Word draws "2.1.1." and the reader drew "2.1.2.". Rechecked: the 35-paragraph list file still matches Word line for line.
- **A level redrawn in a list instance's override was ignored.** An instance's `w:lvlOverride/w:lvl` now replaces the definition's level for that instance.
- **A heading style that names the list but not its level.** Checked in real Word: when a level of the list names another style, as a heading list's first level names Heading 1, a paragraph that the style alone puts at that level shows no number and does not count. The reader now does the same; Word's own heading lists name the level in each style, and number "1", "1.1", "1.2", "2" as before.
- **Text was lost or added:** rows and cells in content controls were dropped, only the first text box of a group was read, and hidden text came out. All three are fixed.
- **Two typed page breaks in a row made one new page;** Word counts the empty page between them. Pages are now counted as Word counts them: each typed break or layout record starts a page, and a paragraph set to break the page before it starts one unless a page has just begun.
- **The locked check named Word for any locked Office file;** see the choice above.
- **Nested bullets lost their nesting;** see the list choice above.
- A test now checks a tone mark stored before its vowel in a DOCX.

Tidying: `DocxToDocx` lives with the conversion function, not in intake, since it refuses an output; the CLI rounds megabytes in one place; page and text marks are one `_Mark` enum and reading gives `_Item`s, with no stand-in paragraph for "text was here"; element paths are made in one place; the list-style links are read once; the builder's numbered lists say how they begin with one field.

**Checked in the Linux image** (no network, read-only, `/tmp` in memory): mypy, the fast suite, `pytest -m ocr`, the harness gate, and mounted conversions of a PDF to Markdown, a PDF to DOCX and a DOCX to Markdown all pass. The first run found that `word-structure.docx` generated on Linux differed from the one generated on Windows in 18 bytes: Python records in each zip entry the system that made it. `word_builder` now records the same system everywhere; the committed file kept its bytes.

Not changed: footnotes, endnotes and symbol-font characters, as in "Left open"; the builder's table placement repeats the renderer's, since fixtures do not reach into the renderer; the page limit is checked for PDFs in intake and for DOCX after reading, since a DOCX's pages are only known then.
