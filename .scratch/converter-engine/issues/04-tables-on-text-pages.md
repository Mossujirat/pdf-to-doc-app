# 04: Tables on text pages

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Tables on text pages come out as tables. Every Thai vowel and tone mark inside each cell is intact, and merged cells are preserved. The document model gains a table block with row and column spans. The Markdown renderer outputs a GFM table, or an HTML table when any cell is merged.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/text-pages`

**Extraction**
- [ ] Cell grids come from PyMuPDF's table finder. Words are assigned to the cell that contains the word's centre.
- [ ] Text is never clipped to a cell box. In the benchmark, clipping turned "งวดที่" into "งวดท".
- [ ] Merged cells become row and column spans in the document model.

**Markdown output**
- [ ] A GFM table when no cell is merged; an HTML table with `rowspan`/`colspan` otherwise.
- [ ] Multi-line cell text is joined with the same Thai line-joining rules as paragraphs.
- [ ] Lines that sit in columns but have no ruling are not turned into fake tables. MarkItDown produced 78 such tables in the benchmark.

**Tests**
- [ ] Synthetic fixtures cover a ruled table with Thai text in cells, a table with merged cells, and a column-aligned list that is not a table. The harness shows zero broken text on them.

## Comments

**2026-10-19, findings from ticket 03 on the real contract**

- **Wrapped cells split their row.** On page 2, the appendix list is laid out with tab stops. When a cell's text wraps onto a second line, PyMuPDF orders that row as: column 1, column 2 line 1, column 2 line 2, then columns 3–4 in a later block. Ticket 03 rejoins only consecutive pieces on one baseline, so that row comes out as three paragraphs.
- **Budget table (pp. 69–72): every cell is its own paragraph.** A cell holding only "-" renders as an empty bullet in Markdown viewers, though the dash is still in the raw text. Keep such cells inside table blocks.
