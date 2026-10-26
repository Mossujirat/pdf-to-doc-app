# 06: Uncertain text in table cells

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A word that OCR may have misread inside a table cell is marked as uncertain text, as it is in a paragraph: `<mark>` in Markdown, yellow in DOCX, and counted in the summary and on the web results page. A reader then knows which cells to check against the original.

**Blocked by:** 04

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**Marking**
- [ ] A cell's uncertain text is found as a paragraph's is, from the pieces it was read from. The two signals are:
  - a Thai word that the word list does not hold;
  - a box read with a confidence below 0.85.

  Neighbouring uncertain words merge into one stretch.
- [ ] Text a cell takes from a text layer is never uncertain.
- [ ] The document model's single accessor for a block's uncertain text covers table cells. The summary counts them through it, and the web results page shows the count per page.

**Outputs**
- [ ] **Markdown:** uncertain text inside a cell is wrapped in `<mark>`, in GFM and HTML tables alike. `|` is still escaped, and a `<br>` inside a cell still works.
- [ ] **DOCX:** uncertain text inside a cell is highlighted yellow, with the Thai font settings unchanged.

**Tests**
- [ ] Fast tests with `FakeEngine` and `Unsure` boxes:
  - a marked word in a cell, in both outputs;
  - two neighbouring words merged into one stretch;
  - the summary's count;
  - a text-layer note in a cell that is not marked.
- [ ] Checked by breaking the code on purpose: the accessor, and each renderer's marking.
- [ ] Run pytest, mypy, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **Until this ticket, misread words in OCR tables go unmarked.** Before ticket 04, a table's text on an OCR page came out in rows, whose pieces marked it, and the summary counted it. Now it goes into cells, and `layout.CellLine` holds the text alone, with no pieces. So a misread word in a cell is neither marked nor counted. The branch must not be merged without this ticket.
- **Where the pieces are:** `ocr._cell_line` builds a cell's printed line from the engine's boxes, which carry each box's text and confidence, as `ocr._row` builds a row's `pieces`.
