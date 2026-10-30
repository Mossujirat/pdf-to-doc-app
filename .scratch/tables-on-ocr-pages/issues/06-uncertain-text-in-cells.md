# 06: Uncertain text in table cells

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A word that OCR may have misread inside a table cell is marked as uncertain text, as it is in a paragraph: `<mark>` in Markdown, yellow in DOCX, and counted in the summary and on the web results page. A reader then knows which cells to check against the original.

**Blocked by:** 04

**Status:** done

**Branch:** `feat/ocr-tables`

**Marking**
- [x] A cell's uncertain text is found as a paragraph's is, from the pieces it was read from. The two signals are:
  - a Thai word that the word list does not hold;
  - a box read with a confidence below 0.85.

  Neighbouring uncertain words merge into one stretch.
- [x] Text a cell takes from a text layer is never uncertain.
- [x] The document model's single accessor for a block's uncertain text covers table cells. The summary counts them through it, and the web results page shows the count per page.

**Outputs**
- [x] **Markdown:** uncertain text inside a cell is wrapped in `<mark>`, in GFM and HTML tables alike. `|` is still escaped, and a `<br>` inside a cell still works.
- [x] **DOCX:** uncertain text inside a cell is highlighted yellow, with the Thai font settings unchanged.

**Tests**
- [x] Fast tests with `FakeEngine` and `Unsure` boxes:
  - a marked word in a cell, in both outputs;
  - two neighbouring words merged into one stretch;
  - the summary's count;
  - a text-layer note in a cell that is not marked.
- [x] Checked by breaking the code on purpose: the accessor, and each renderer's marking.
- [x] Run pytest, mypy, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **Until this ticket, misread words in OCR tables go unmarked.** Before ticket 04, a table's text on an OCR page came out in rows, whose pieces marked it, and the summary counted it. Now it goes into cells, and `layout.CellLine` holds the text alone, with no pieces. So a misread word in a cell is neither marked nor counted. The branch must not be merged without this ticket.
- **Where the pieces are:** `ocr._cell_line` builds a cell's printed line from the engine's boxes, which carry each box's text and confidence, as `ocr._row` builds a row's `pieces`.

**2026-10-28, implemented on branch `feat/ocr-tables`**

- **The model:** a `TableCell` holds its uncertain text as stretches, as a paragraph does. The one accessor, `model.uncertain_text`, now takes a block or a cell; a table's text is in its cells.
- **Finding it:** a cell's printed lines carry the pieces they were read from (`layout.CellLine.pieces`), and `uncertain.uncertain_spans` finds the cell's stretches from them, as for a paragraph. A text-layer row in a cell, such as a typed note, gives pieces with no confidence, which are never uncertain. On text pages a cell's lines carry no pieces, so its text is never marked.
- **A line break kept in a cell parts stretches.** Stretches a space apart merge, as before; stretches either side of a kept line break stay two, as the break parts two items. Paragraphs hold no line breaks, so they are unchanged.
- **Markdown** wraps uncertain text in `<mark>` inside GFM and HTML cells. Each stretch is escaped first, then wrapped, and a kept break is a `<br>`. Paragraphs and list items use the same function, `markdown._marked`.
- **DOCX** highlights uncertain text in a cell yellow, through the same `_add_text` that paragraphs use, so the Thai font settings stay as they are.
- **The summary** counts the stretches of every paragraph, list item and cell through the accessor. The web results page reads that count per page, so it needed no change.
- **`FakeEngine`:** `Unsure` can wrap a `Grid`, whose every box it then reads with low confidence.
- **Tests** (`test_ocr_tables.py`, through the conversion function):
  - a misread word in a cell is marked, in Markdown;
  - two neighbouring misread words in an HTML table are one stretch;
  - a mark beside an escaped `|` and a kept `<br>`;
  - cells read with low confidence are marked whole;
  - each item kept on a line of its own is marked apart, and counted apart;
  - the summary counts a cell's stretch with a paragraph's;
  - a word highlighted yellow in the Word table, in the same Thai font as the rest;
  - a typed note in a cell, with a surname the word list does not hold, is never marked.
- **Checked by breaking the code on purpose,** with `test_ocr_tables.py`, `test_uncertain_text.py`, `test_docx_output.py` and `test_tables.py`:

  | Broken | Tests that fail |
  | --- | --- |
  | the accessor leaves cells out | 7 |
  | Markdown marks no cell | 4 |
  | DOCX highlights no cell | 1 |
  | the summary counts no cell | 2 |
  | a text-layer row in a cell read as OCR | 1, the typed note |
  | stretches merged across a kept line break | 1 |

- **The harness, PaddleOCR, on `corpus/synthetic`:** CER and cells are unchanged. Uncertain stretches on OCR pages went from 7 to 35, as the words misread in cells are now marked: the share of edits left unmarked fell from 0.93 to 0.71.

**2026-10-28, after code review (two axes)**

- **Spec found a real fault:** two items kept on lines of their own merged into one stretch when the first ended and the second started with uncertain text, as the line break between them counted as a space. A cell's items read at low confidence were then one mark across the `<br>`, and counted once. Fixed as above; the new test failed before.
- **Spec also found:**
  - **Two functions for uncertain text:** a counting function had been added beside the accessor. It is gone: the summary counts through the accessor, over a table's cells.
  - **The DOCX test now checks the Thai font** of the highlighted word too.
  - The web results page has no test of its own: it shows the summary's count, which the summary test covers.
- **Standards: no written rule broken. Fixed:**
  - the accessor's argument is named `part`, not `text`;
  - Markdown's cell marking is `_marked` with an escape, not a copy of it;
  - `CellLine.pieces` now says it is empty on a text page.
- **Left:** one more `isinstance(box, _LayerRow)` in `ocr._cell_line`, beside the others there.
- **Checked by breaking the code again:** stretches merged across a kept line break fail the new test; a summary that counts no cell fails 2 tests; an accessor that leaves cells out fails 7.
- **Run:** pytest (615 passed and 1 skipped on Windows, 616 passed in the Linux image), mypy, `pytest -m ocr` (23 passed in the image), and the harness in the image, with the same numbers as above: 35 uncertain stretches on OCR pages, 0.71 left unmarked, cells 152/181.
