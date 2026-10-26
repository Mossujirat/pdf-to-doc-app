# 01: The harness measures cells placed right

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A maintainer runs the quality harness on a corpus and sees, for every page whose reference text holds tables, how many of the reference's cells the output holds in the right place. Today the harness strips table markup before comparing pages, so a table flattened into paragraphs scores almost as well as a table kept whole. The later tickets of this feature use this measure to show that their tables are right.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**The measure**
- [ ] The tables are read from the reference and the output alike:
  - GFM pipe tables and HTML tables;
  - merged cells expanded by their `rowspan` and `colspan`;
  - `<mark>` dropped;
  - a `<br>` in a cell treated the same on both sides.
- [ ] A reference cell counts as right when the output's matching table has a cell at the same row and column holding the same text.
  - Text is compared after NFC and collapsing whitespace. NFKC is never applied.
  - Each reference table is matched to the output table that shares most of its text.
  - A missing table counts all its cells as missed.
- [ ] Reported per page and in total, in the readable table and in the JSON report:
  - for example, "38/44";
  - "-" on a page whose reference holds no table.
- [ ] Today's measures (CER, broken text, uncertain text, unmarked edits) and the gate on text pages are unchanged.
- [ ] `corpus/README.md` explains the new column.

**Tests**
- [ ] Harness tests cover:
  - a table that is all right;
  - a cell moved to the wrong row;
  - merged cells;
  - a table flattened into paragraphs;
  - a missing table;
  - a page with no table;
  - `<mark>` inside a cell.
- [ ] Run pytest, mypy and the harness on `corpus/synthetic`. Record the cells column for the existing table pages in Comments.

## Comments
