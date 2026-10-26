# 03: One line per row on OCR pages

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** On an OCR page, a printed line whose parts are set apart by a wide gap stays a line of its own, as it does on text pages. That covers:
- each label beside its value;
- each row of a table with no rules;
- tab-stop lists;
- signature lines.

Today such rows run together into one paragraph, and on a cover sheet a label was glued to the next value ("ออนไลน์หัวหน้าโครงการ").

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**The rule**
- [ ] An OCR row is set out in columns (`in_columns`) when two neighbouring boxes on its line are set apart by a gap wider than two font sizes. That is the rule text pages follow when they rejoin pieces of a line.
- [ ] Such a row is never joined into a paragraph, and is never taken for a list item or a bold heading, as on text pages.
- [ ] **Body text is never flagged.** During grilling, 381 OCR rows were measured. Only these rows were flagged:
  - table rows;
  - label–value pairs;
  - tab-stop lists;
  - signature lines;
  - junk.

**Check what changed**
- [ ] Run the harness on `corpus/synthetic` and `corpus/degraded`, with and without the change. List every page whose output changes, with a line on why, in Comments.
  - Expected: the two-column cover sheet improves (CER 0.0194 to 0.0039 when grilled).
  - On one sideways page, a "1" misread as "-" now shows, marked uncertain. Before, it was hidden as a list bullet.
- [ ] Pages set in two columns still read column by column (ticket 18 of the converter).

**Tests**
- [ ] Fast tests with `FakeEngine`:
  - a label–value list on an OCR page gives one line per pair;
  - the rows of a table with no rules come out one line each;
  - a body line with ordinary spaces stays in its paragraph;
  - a line the detector boxed in two at a wide gap stays a line of its own.
- [ ] Checked by breaking the code on purpose: the tests fail without the flag.
- [ ] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments
