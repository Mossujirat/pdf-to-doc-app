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
