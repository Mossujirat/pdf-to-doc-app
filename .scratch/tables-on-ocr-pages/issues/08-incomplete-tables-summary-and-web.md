# 08: Incomplete tables, the summary and the web

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** Sometimes a table on an OCR page can be seen, but its text cannot be placed in cells with certainty. Such a table comes out as an **incomplete table**: the label `[ตารางอาจไม่สมบูรณ์]`, then its rows, each printed line on its own. The reader knows to check its structure, and gets no cells that look right but hold the wrong text. The summary at the top of each output says how many tables on OCR pages came out as tables, and how many may be incomplete, with their pages. The web results page shows the same per page.

**Blocked by:** 03, 04, 06

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**When a table is incomplete**
- [ ] **Rules seen, but not a whole grid.** For example, a boxed header row of two or more cells, with rows under it set out in columns that line up with its column rules. The incomplete table takes the header row and those rows.
- [ ] **A box that crosses a rule through its middle,** so that its text would belong to two cells. Its table becomes incomplete.
- [ ] **A table with no rules at all is never an incomplete table.** It comes out one line per row with no label (ticket 03), as unruled tables on text pages do.

**Document model and outputs**
- [ ] **A new block, the incomplete table,** holds its printed rows, each a line with its uncertain text, and records its source page.
  - The `incomplete_table` placeholder kind is removed: in `GLOSSARY.md` an incomplete table is not a placeholder.
  - The accessor for uncertain text covers its rows.
- [ ] **Markdown:** the label as a paragraph of its own, then each row as a paragraph, with `<mark>` where uncertain.
- [ ] **DOCX:** the label, then each row as a paragraph, highlighted where uncertain.

**Summary**
- [ ] It counts, per page:
  - the tables on OCR pages that came out as tables;
  - the incomplete tables.

  Tables on text pages are not counted.
- [ ] **The headline** says both counts, with the pages of the incomplete tables. It says this apart from the list of what was not transcribed.
- [ ] **The Thai wording** is shown to the user and approved before it is committed.

**Web**
- [ ] **The results page's notes** for each page list incomplete tables apart from placeholders. A page with an incomplete table is tagged to check ("ตรวจ"), as one with uncertain text is.
- [ ] **The page "ข้างในทำอะไรกับไฟล์ของคุณ"** adds the rest of the rule:
  - tables whose rules are incomplete are labelled;
  - tables with no rules come out one line per row.

  The user approves the Thai.

**Documents**
- [ ] `corpus/README.md` describes `[ตารางอาจไม่สมบูรณ์]` as the label of an incomplete table, before its rows, not as a placeholder.
- [ ] The converter spec's lines on scanned table structure and its list of placeholder kinds are brought up to date. They pointed to PP-StructureV3 and an "incomplete table" placeholder.

**Corpus**
- [ ] **A synthetic scan with a table whose only boxed row is its header,** and its reference text with the label and the rows one per line.
- [ ] **A scan with tables with no rules,** whose reference gives the rows one per line with no label.

**Tests**
- [ ] Fast tests:
  - a header-only table becomes an incomplete table, with its label and rows, in both outputs, counted in the summary;
  - a box crossing a rule makes its table incomplete;
  - a table with no rules gets no label;
  - the headline with tables made and incomplete;
  - uncertain text in an incomplete table's rows.
- [ ] Web tests:
  - a page's notes and "ตรวจ" tag for an incomplete table;
  - the new text of the explanation page.
- [ ] Checked by breaking the code on purpose: each case of an incomplete table, and the summary's counts.
- [ ] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **Two kinds of grid make no table today, and are read as lines with no label.** This ticket decides whether either is an incomplete table:
  - a grid of one row, such as a boxed header row alone. The user chose rows for ticket 04 and left the rest to this ticket. `test_a_ruled_row_with_no_ruled_rows_under_it_is_read_as_lines` pins it.
  - a grid whose rules close off a space that is no rectangle, where part of a rule is missing (`grids._grid` returns None). `test_rules_that_leave_a_space_no_cell_could_be_make_no_table` pins it.
- **Not caught:** on scans of 110 dpi and below, lost pieces of rule give false spans. The cells are still rectangles, so the grid is taken as whole; ticket 04's Comments have the numbers.
