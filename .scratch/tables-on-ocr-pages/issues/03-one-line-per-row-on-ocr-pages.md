# 03: One line per row on OCR pages

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** On an OCR page, a printed line whose parts are set apart by a wide gap stays a line of its own, as it does on text pages. That covers:
- each label beside its value;
- each row of a table with no rules;
- tab-stop lists;
- signature lines.

Today such rows run together into one paragraph, and on a cover sheet a label was glued to the next value ("ออนไลน์หัวหน้าโครงการ").

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/ocr-tables`

**The rule**
- [x] An OCR row is set out in columns (`in_columns`) when two neighbouring boxes on its line are set apart by a gap wider than two font sizes. That is the rule text pages follow when they rejoin pieces of a line.
- [x] Such a row is never joined into a paragraph, and is never taken for a list item or a bold heading, as on text pages.
- [x] **Body text is never flagged.** During grilling, 381 OCR rows were measured. Only these rows were flagged:
  - table rows;
  - label–value pairs;
  - tab-stop lists;
  - signature lines;
  - junk.

**Check what changed**
- [x] Run the harness on `corpus/synthetic` and `corpus/degraded`, with and without the change. List every page whose output changes, with a line on why, in Comments.
  - Expected: the two-column cover sheet improves (CER 0.0194 to 0.0039 when grilled).
  - On one sideways page, a "1" misread as "-" now shows, marked uncertain. Before, it was hidden as a list bullet.
- [x] Pages set in two columns still read column by column (ticket 18 of the converter).

**Tests**
- [x] Fast tests with `FakeEngine`:
  - a label–value list on an OCR page gives one line per pair;
  - the rows of a table with no rules come out one line each;
  - a body line with ordinary spaces stays in its paragraph;
  - a line the detector boxed in two at a wide gap stays a line of its own.
- [x] Checked by breaking the code on purpose: the tests fail without the flag.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, implemented on branch `feat/ocr-tables`**

- **What changed:** `ocr._row` sets `in_columns` when two neighbouring boxes on a printed line are more than `layout.COLUMN_GAP` (2) font sizes apart. That is the constant text pages use, now shared.
- **Pages that changed with real PaddleOCR.** Every other page read as before, and so did all five pages of `corpus/degraded`.

  | Page | CER before | CER now | Why |
  | --- | --- | --- | --- |
  | `two-column-scans` page 3, the cover sheet | 0.0194 | 0.0039 | each label–value pair is now a line of its own, where a label had been glued to the next value |
  | `sideways-scans` page 1 | 0.0084 | 0.0168, uncertain 3 → 4 | the price schedule's rows are now one per line |

  - **Why the sideways page's CER rose:** OCR reads the first row's "1" as "-". That row used to be taken for a bulleted list item, so the "-" was dropped and the "1" was missing with no warning. Now the "-" stays, marked uncertain, so a reader is told to check.
  - **Also on that page:** a junk "Q" stands on a line of its own, which ticket 07 takes up.
- **Tests in `test_ocr_pages.py`:**
  - four layouts set out in columns each give one paragraph per row: a table with no rules, values at a tab stop, long labels with short values, and a form;
  - a body line that the detector cut at an ordinary space stays in its paragraph.
  - The two-column tests are unchanged and pass.
- **Checked by breaking the code on purpose:**
  - never setting the flag fails the four layout tests;
  - setting it at every gap fails the body-line test.
- **Run:** pytest, mypy, `pytest -m ocr` and the harness, on Windows and in the Linux container.
  - pytest: 574 passed and 1 skipped on Windows (a Linux-only test), and 575 passed on Linux.
  - `pytest -m ocr`: 17 passed on each.
  - The harness gave the same CERs on both.

**2026-10-26, after code review (two axes, tickets 01–03 together)**

- **Spec:** implemented as asked.
- **Standards:** `GLOSSARY.md` says a table's columns, and labels set apart from their values, are not columns. The new docstring and test names had said "set out in columns", so they now say parts "set apart" by a gap as wide as a tab stop's. The docstring also now gives the evidence: only such rows, signature lines and junk had a gap that wide on the corpus's scans. The flag keeps its old name, `in_columns`, as ticket 18 left it.
