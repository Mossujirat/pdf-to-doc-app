# 04: Tables on text pages

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Tables on text pages come out as tables. Every Thai vowel and tone mark inside each cell is intact, and merged cells are preserved. The document model gains a table block with row and column spans. The Markdown renderer outputs a GFM table, or an HTML table when any cell is merged.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/text-pages`

**Extraction**
- [x] Cell grids come from PyMuPDF's table finder. Words are assigned to the cell that contains the word's centre.
- [x] Text is never clipped to a cell box. In the benchmark, clipping turned "งวดที่" into "งวดท".
- [x] Merged cells become row and column spans in the document model.

**Markdown output**
- [x] A GFM table when no cell is merged; an HTML table with `rowspan`/`colspan` otherwise.
- [x] Multi-line cell text is joined with the same Thai line-joining rules as paragraphs.
- [x] Lines that sit in columns but have no ruling are not turned into fake tables. MarkItDown produced 78 such tables in the benchmark.

**Tests**
- [x] Synthetic fixtures cover a ruled table with Thai text in cells, a table with merged cells, and a column-aligned list that is not a table. The harness shows zero broken text on them.

## Comments

**2026-10-19, findings from ticket 03 on the real contract**

- **Wrapped cells split their row.** On page 2, the appendix list is laid out with tab stops. When a cell's text wraps onto a second line, PyMuPDF orders that row as: column 1, column 2 line 1, column 2 line 2, then columns 3–4 in a later block. Ticket 03 rejoins only consecutive pieces on one baseline, so that row comes out as three paragraphs.
- **Budget table (pp. 69–72): every cell is its own paragraph.** A cell holding only "-" renders as an empty bullet in Markdown viewers, though the dash is still in the raw text. Keep such cells inside table blocks.

**2026-10-19, implementation notes**

- **Finding tables.**
  - Tables come from PyMuPDF's `find_tables`, ruled lines strategy only, so column-aligned text without ruling never becomes a table.
  - Pages that draw no lines or boxes skip the search. A ruled table needs them, and this saved about 2 s on the 110-page contract.
  - PyMuPDF's hint to install `pymupdf_layout` is switched off, because it printed into CLI output. That package is AGPL as well, and is not needed.
- **Merged cells.** PyMuPDF reports a merged cell as its full box at the first position and `None` where it covers. Row and column spans are counted from the grid lines.
- **Cell text.**
  - Each character is assigned to the cell holding its centre and is never clipped.
  - A character goes to one cell only. On page 69 of the contract, PyMuPDF reported 2 pairs of overlapping cells, and their text came out twice before this rule. There is no synthetic fixture for this, because the builder cannot make PyMuPDF report overlapping cells; it was verified on the contract instead.
  - Character centres are computed once per page. Scanning every character for every cell made the contract take 18.7 s instead of 5.8 s.
- **Markdown.**
  - A GFM table with the first row as header.
  - An HTML table when any cell is merged.
  - `|` inside cells is escaped.
  - Text wrapped inside a cell is rejoined with the Thai line rules.
- **Real contract, compared locally with the ticket 03 output.**
  - Exactly the same characters: none lost, none duplicated.
  - Ruled tables were found on pp. 69–72 only.
- **Still rough: the budget tables on pp. 69–72 are only partly ruled.**
  - PyMuPDF's grid there is coarse. Several printed sub-rows land in one cell, and some rows are empty. The text is intact but the cell structure is not faithful.
  - Unruled parts stay as one paragraph per row (ticket 03).
  - Improving this would need another detection strategy, such as text alignment, which risks fake tables. Revisit when ticket 17 measures real documents.

**2026-10-19, changes after code review**

- **Every character comes out exactly once.**
  - Characters are grouped into words: a word breaks at a space or at a gap wider than half a character.
  - A word goes whole to the cell holding its centre, or else to the cell it starts in, as when the last column's text runs past the table's edge.
  - Words in no cell stay in the page's rows, so text inside the table's area but outside every box is kept.
  - This fixed text lost at a table's right edge, a word split across a rule, orphaned marks from "ที่" sitting across a rule, and a line duplicated when it ran into a cell.
- **Cells.**
  - A position with no box, and no merged cell over it, becomes an empty cell, so columns stay aligned.
  - A cell's words keep their own order.
  - Words set apart by a wide gap, as a tab stop does, are joined with a space ("นาย สมชาย ใจดี"). Gaps under half a character still join with no space, because there they cannot be told apart from stretched justified Thai.
- **Table detection.**
  - A table lying wholly within the 10% edge band is read as rows, so ruled header and footer boxes are removed as page furniture again. This was a ticket 03 regression.
  - A table inside another table is dropped. The inner text stays in the outer cell, and no empty table is output.
  - A paragraph never runs across a table that starts between two of its rows. The reviewer's thin-table probe now comes out in order.
- **Thai repair** of cell text moved to `layout.py`. `pdf_text.py` now passes each cell's printed lines on unchanged.
- **Deferred:** a cell that wraps inside an *unruled*, tab-stop layout still splits that row (p. 2 of the contract). Unruled tables are out of scope here, and the decision is left to ticket 17's measurements.
- **Real contract, rerun locally.**
  - The same characters as the ticket 03 output: none lost, none duplicated.
  - 16 ruled tables.
  - 7.8 s for 110 pages.

**2026-10-25, from grilling ticket 14 (scanned tables)**

- **The coarse grid will be handled for text pages too.** That is the grid where printed sub-rows share one ruled cell. The user decided that ticket 14's rule for a cell holding several printed lines applies to every table, text pages included:
  - lines that line up across two or more cells become sub-rows;
  - otherwise a line that fills its cell carries on into the next;
  - a short line ends its item, and the break is kept inside the cell.
- **Why:** joining every line by the Thai line rules glues stacked items into one word ("ค่าวัสดุสำนักงานค่าถ่ายเอกสาร"), and parts their amounts from them.
- **The `tables` corpus fixture changes.** Its cell "ส่งรายงานความก้าว / หน้าฉบับที่หนึ่ง" breaks mid-word in a cell that is not full. Ticket 14 rebuilds it to wrap the way Word does.
