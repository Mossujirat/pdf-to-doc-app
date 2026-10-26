# 01: The harness measures cells placed right

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A maintainer runs the quality harness on a corpus and sees, for every page whose reference text holds tables, how many of the reference's cells the output holds in the right place. Today the harness strips table markup before comparing pages, so a table flattened into paragraphs scores almost as well as a table kept whole. The later tickets of this feature use this measure to show that their tables are right.

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/ocr-tables`

**The measure**
- [x] The tables are read from the reference and the output alike:
  - GFM pipe tables and HTML tables;
  - merged cells expanded by their `rowspan` and `colspan`;
  - `<mark>` dropped;
  - a `<br>` in a cell treated the same on both sides.
- [x] A reference cell counts as right when the output's matching table has a cell at the same row and column holding the same text.
  - Text is compared after NFC and collapsing whitespace. NFKC is never applied.
  - Each reference table is matched to the output table that shares most of its text.
  - A missing table counts all its cells as missed.
- [x] Reported per page and in total, in the readable table and in the JSON report:
  - for example, "38/44";
  - "-" on a page whose reference holds no table.
- [x] Today's measures (CER, broken text, uncertain text, unmarked edits) and the gate on text pages are unchanged.
- [x] `corpus/README.md` explains the new column.

**Tests**
- [x] Harness tests cover:
  - a table that is all right;
  - a cell moved to the wrong row;
  - merged cells;
  - a table flattened into paragraphs;
  - a missing table;
  - a page with no table;
  - `<mark>` inside a cell.
- [x] Run pytest, mypy and the harness on `corpus/synthetic`. Record the cells column for the existing table pages in Comments.

## Comments

**2026-10-26, implemented on branch `feat/ocr-tables`**

- **Where:** `score_page` counts the cells along with its other measures, so each page's `PageScore` holds `cells` and `cells_right`. `Report` sums them, and the command adds a `cells` column and two JSON fields to each page and to each total.
- **Matching:** a reference table is matched with the output table that shares the most cell texts with it.
- **Line breaks:** a `<br>` inside a cell reads as a space, so a cell that kept its break matches a reference that kept it, and a cell that glued its lines does not.
- **Tests:** `test_score_page.py` has nine more tests:
  - a table all right;
  - amounts swapped between rows, with CER still 0;
  - a table flattened into a paragraph, again with CER 0;
  - merged cells, 5 of 7 in place without the merges;
  - a table the output lacks;
  - an extra table in the output before the matching one;
  - a page with no table;
  - `<mark>` and an escaped `|` inside cells;
  - a kept `<br>` against a glued one.

  `test_evaluate.py` checks the column, `-` on a page with no table, the total and the JSON fields.
- **Checked by breaking the code on purpose:**
  - without the skip past merged cells, the merged-cell test fails;
  - matching the first table instead of the one that shares most text failed nothing at first. The test with an extra table was added for it.
- **The corpus today:**

  | Page | Kind | Cells |
  | --- | --- | --- |
  | `tables` page 1 | text | 19/19 |
  | `word-structure` page 2 | text | 7/7 |
  | `rotated-text-pages` page 1 | text | 4/4 |
  | `sideways-scans` page 1 | OCR | 0/20 |
  | `sideways-scans` page 2 | OCR | 0/20 |

  In total, 30/70: 30/30 on text pages, and 0/40 on OCR pages, which get no tables until ticket 04.

**2026-10-26, after code review (two axes, tickets 01–03 together)**

- **Spec found a gap: a missing table was not always missed.**
  - The first output table was taken as the match even when it shared no text with the reference's.
  - Its empty cells and dashes could then count as in place.
- **The fix:** a table matches only if it shares a cell holding a letter or a digit. Empty cells and dashes don't count. A new test, a table sharing only an empty cell and a dash, failed before the fix.
- **The JSON report** gives `cells: 0` and `cells_right: 0` on a page with no table, where the readable table shows `-`. Numbers suit JSON, so this was kept.
- **Standards (no rule broken), fixed:**
  - parsed cells are `model.TableCell`, not tuples;
  - the GFM separator row is one pattern, shared with the markup that `visible_text` strips;
  - `_placed` returns `placed`, so `cells` always means a count.
- **Run again:** pytest on Windows (579) and in the Linux container (580), mypy, and the harness, with the same totals: 46/46 cells on text pages, 0/40 on OCR pages.
