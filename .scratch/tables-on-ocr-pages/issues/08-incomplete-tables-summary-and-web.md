# 08: Incomplete tables, the summary and the web

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** Sometimes a table on an OCR page can be seen, but its text cannot be placed in cells with certainty. Such a table comes out as an **incomplete table**: the label `[ตารางอาจไม่สมบูรณ์]`, then its rows, each printed line on its own. The reader knows to check its structure, and gets no cells that look right but hold the wrong text. The summary at the top of each output says how many tables on OCR pages came out as tables, and how many may be incomplete, with their pages. The web results page shows the same per page.

**Blocked by:** 03, 04, 06

**Status:** done

**Branch:** `feat/ocr-tables`

**When a table is incomplete**
- [x] **Rules seen, but not a whole grid.** For example, a boxed header row of two or more cells, with rows under it set out in columns that line up with its column rules. The incomplete table takes the header row and those rows.
- [x] **A box that crosses a rule through its middle,** so that its text would belong to two cells. Its table becomes incomplete.
- [x] **A table with no rules at all is never an incomplete table.** It comes out one line per row with no label (ticket 03), as unruled tables on text pages do.

**Document model and outputs**
- [x] **A new block, the incomplete table,** holds its printed rows, each a line with its uncertain text, and records its source page.
  - The `incomplete_table` placeholder kind is removed: in `GLOSSARY.md` an incomplete table is not a placeholder.
  - The accessor for uncertain text covers its rows.
- [x] **Markdown:** the label as a paragraph of its own, then each row as a paragraph, with `<mark>` where uncertain.
- [x] **DOCX:** the label, then each row as a paragraph, highlighted where uncertain.

**Summary**
- [x] It counts, per page:
  - the tables on OCR pages that came out as tables;
  - the incomplete tables.

  Tables on text pages are not counted.
- [x] **The headline** says both counts, with the pages of the incomplete tables. It says this apart from the list of what was not transcribed.
- [x] **The Thai wording** is shown to the user and approved before it is committed.

**Web**
- [x] **The results page's notes** for each page list incomplete tables apart from placeholders. A page with an incomplete table is tagged to check ("ตรวจ"), as one with uncertain text is.
- [x] **The page "ข้างในทำอะไรกับไฟล์ของคุณ"** adds the rest of the rule:
  - tables whose rules are incomplete are labelled;
  - tables with no rules come out one line per row.

  The user approves the Thai.

**Documents**
- [x] `corpus/README.md` describes `[ตารางอาจไม่สมบูรณ์]` as the label of an incomplete table, before its rows, not as a placeholder.
- [x] The converter spec's lines on scanned table structure and its list of placeholder kinds are brought up to date. They pointed to PP-StructureV3 and an "incomplete table" placeholder.

**Corpus**
- [x] **A synthetic scan with a table whose only boxed row is its header,** and its reference text with the label and the rows one per line.
- [x] **A scan with tables with no rules,** whose reference gives the rows one per line with no label.

**Tests**
- [x] Fast tests:
  - a header-only table becomes an incomplete table, with its label and rows, in both outputs, counted in the summary;
  - a box crossing a rule makes its table incomplete;
  - a table with no rules gets no label;
  - the headline with tables made and incomplete;
  - uncertain text in an incomplete table's rows.
- [x] Web tests:
  - a page's notes and "ตรวจ" tag for an incomplete table;
  - the new text of the explanation page.
- [x] Checked by breaking the code on purpose: each case of an incomplete table, and the summary's counts.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **Two kinds of grid make no table today, and are read as lines with no label.** This ticket decides whether either is an incomplete table:
  - a grid of one row, such as a boxed header row alone. The user chose rows for ticket 04 and left the rest to this ticket. `test_a_ruled_row_with_no_ruled_rows_under_it_is_read_as_lines` pins it.
  - a grid whose rules close off a space that is no rectangle, where part of a rule is missing (`grids._grid` returns None). `test_rules_that_leave_a_space_no_cell_could_be_make_no_table` pins it.
- **Not caught:** on scans of 110 dpi and below, lost pieces of rule give false spans. The cells are still rectangles, so the grid is taken as whole; ticket 04's Comments have the numbers.

**2026-10-29, implemented on branch `feat/ocr-tables`**

- **The user decided:**
  - a boxed row of two or more cells with no row set out under it stays lines with no label, as forms' boxes do;
  - rules that close off a space that is no rectangle make an incomplete table;
  - the Thai: the label `[ตารางอาจไม่สมบูรณ์]`; the headline's "ตารางในหน้าที่อ่านด้วย OCR: เป็นตาราง N ตาราง, อาจไม่สมบูรณ์ N ตาราง ในหน้า … ควรตรวจโครงสร้างกับต้นฉบับ", a count of zero left out; the results page's notes "ตาราง N" and "ตารางอาจไม่สมบูรณ์ N"; and on "ข้างในทำอะไรกับไฟล์ของคุณ", "ในหน้าเหล่านี้ ตารางที่เส้นไม่ครบจะออกเป็นข้อความทีละบรรทัด ตามหลังป้าย [ตารางอาจไม่สมบูรณ์] ส่วนตารางที่ไม่มีเส้นเลยออกเป็นแถวละบรรทัด".
- **Finding the rules (`grids.ruled_tables`):** whole grids as before, and **part rules**: a grid of one row of two or more cells, or a grid whose spaces overlap. A frame of one cell is neither, as before. Rules inside other rules, of either kind, are part of them.
- **When a table is incomplete (`ocr._ocr_page`):**
  - **A box that runs through a rule of its cell,** more than half a font size inside both its ends, makes its whole grid incomplete. Detector padding reaches past a rule by 0.44 of the font size at most (ticket 04), and across, a box reaches about 0.4 font sizes above and below its letters' body, so the rule must cut the letters.
  - **Part rules** take the boxes within them, and the printed lines that follow under them, within their width: each less than a box height below the last, none of its boxes running through a column's rule. The first line must be set out in two or more of the columns, as a row is; later ones may lie in one, as a cell's wrapped line does. A boxed row of one ruled row with no such line under it is no table.
  - Copies of upper marks are dropped first, as in cells and rows (ticket 07).
- **The model:** `IncompleteTable`, a block of its printed rows, each a `Paragraph` with its uncertain text, so the one accessor covers them; the summary counts their stretches. The `incomplete_table` placeholder kind is gone.
- **Outputs:** Markdown and DOCX give the label as a paragraph, then each row as one, marked or highlighted where uncertain. The table takes its place in reading order as a table does.
- **Summary:** each page counts its tables that came out as tables, on OCR pages only, and its incomplete tables. The web protocol carries both; the results page notes both apart from placeholders, and tags a page with an incomplete table "ตรวจ", counting it among the pages to check.
- **Corpus:**
  - `boxed-header-table-scans`: the payment schedule with wrapped cells, and a price list, each with only its header boxed;
  - `unruled-table-scans`: the price list and the dates with no rules.
  - With PaddleOCR, both boxed-header pages get the label and every line, CER 0.0091 and 0.0119; the unruled page gets no label, CER 0.0142.
- **The harness, PaddleOCR, against d16f415:** only the two new boxed-header pages changed (CER 0.073 → 0.009 and 0.137 → 0.012, the label now in place). Every other page of `corpus/synthetic` and `corpus/degraded` scored the same: no false label anywhere. Cells 157/181 on OCR pages and 46/46 on text pages, unchanged.
- **Tests:**
  - `test_ocr_tables.py`: a boxed header with rows under it, the paragraph after it apart; a wrapped line under a boxed header kept in the table; a gap wider than a line ending the table; a boxed row with a sentence or a one-column note under it read as lines; rules closing off an L (the test that pinned lines now pins the label); a box through a rule, and one out through the frame; a boxed-header table in a column, the column beside it left alone; the DOCX with its highlights; uncertain text marked and counted; the summary's counts, text pages left out; the headline with each kind.
  - `test_web.py`: the results page's notes and its "ตรวจ" tag; `test_web_home.py`: the new sentence.
  - `test_corpus.py` (`-m ocr`): the boxed-header document labelled, the unruled one not.
- **Checked by breaking the code on purpose,** with `test_ocr_tables.py`, `test_ocr_pages.py`, `test_web.py`, `test_web_home.py` and `test_uncertain_text.py`:

  | Broken | Tests that fail |
  | --- | --- |
  | a one-row grid makes no part rules | 6 |
  | a broken grid makes no part rules | 1, the L |
  | rules inside others kept | 1, the grid in a cell |
  | no crossing check | 1 |
  | a box through a rule by its padding counted | 32 |
  | no gap under part rules | 1 |
  | the first line under them may lie in one column | 1, the one-column note |
  | every line under them must span two columns | 1, the wrapped line |
  | a line through a column rule taken | 1 |
  | boxes beside the rules' width looked at (after the review) | 1, the table in a column |
  | a cell's right rule not looked at (after the review) | 2, through a rule and through the frame |
  | a boxed row with nothing under it taken | 1 |
  | text pages' tables counted | 4 |
  | incomplete tables not counted | 2 |
  | their rows' uncertain text not counted | 1 |
  | no label in Markdown | 5 |
  | no label in DOCX | 1 |
  | an incomplete table's page not tagged | 1 |

  Three guards failed no test and changed no page of the harness, so they were taken out: a crossing past the table's frame not counted, lines under part rules kept within its columns, and a paragraph stopped at an incomplete table (it is at least two lines tall, more than a paragraph's gap).
- **Code review (two axes):**
  - **Spec:** with the columns guard gone, a table in one column of a two-column page was read across the page. When the other column's text lay level with the table's rows, it was taken into them. When it lay between the header and the first row, it broke the table off, so the table got no label. Now only boxes whose centres lie across the rules' width are looked at; `test_an_incomplete_table_in_a_column_takes_none_of_the_column_beside_it` pins this.
  - **Spec:** a box that runs out through the table's frame makes the table incomplete. The user chose to keep it so: what lies outside would otherwise go into the cell unseen. `test_a_box_that_runs_out_through_the_frame_of_a_table_makes_it_incomplete` pins this.
  - **Spec:** "a table with no rules gets no label" has no new fast test. `test_rows_whose_parts_are_set_apart_on_an_ocr_page_stay_lines_of_their_own` in `test_ocr_pages.py` already pins its exact output.
  - **Standards:** no hard violations. The centre of a box across the page, written out four times, is now `_centre_across`. The label stays written out on the explanation page, as `[ลายเซ็น]` is there. "Part rules" is a term of the code, not yet in `GLOSSARY.md`.
- **Run:** pytest (636 passed and 1 skipped on Windows, 637 passed in the Linux image), mypy, `pytest -m ocr` (25 passed in the image), `pytest -m slow`, and the harness, the same on Windows and in the image. After the review's fixes: pytest 638 passed and 1 skipped on Windows, 639 passed in the image, mypy, `-m ocr` and `-m slow` again, and the harness's report of `corpus/synthetic` and `corpus/degraded` the same as before them, page by page.
- **Known limits:**
  - A short paragraph one blank line under an incomplete table, within its columns, is taken as its lines: a blank line between 22-point lines leaves less than a box height.
  - A table with no rules is never labelled, as decided; nor is a boxed row alone.

**2026-10-29, from ticket 09 (the samples)**

- **A regression of this ticket:** `grids._grid` read its frame before checking that any space was closed off. Rules that meet but close off none, as an L does, made the 110-page contract fail to convert. Fixed in ticket 09.
- **Changed on the samples' evidence, as the user chose:**
  - a box crosses a rule only when the rule lies 1.0 font size inside both its ends, not 0.5;
  - text within a grid's frame that no cell holds makes the table incomplete;
  - a grid with no text in any cell is no table.

  Ticket 09's comments have the numbers.
