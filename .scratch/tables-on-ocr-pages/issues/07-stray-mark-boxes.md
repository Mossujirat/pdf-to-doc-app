# 07: Stray mark boxes are dropped

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** On every OCR page, the detector sometimes boxes a line's upper vowels and tone marks apart from the line, as a small box just above it. The line's own reading already holds those marks, so the small box is a copy. It reads as junk such as "ญ ญ", "ว ญ 9" or "e A", marked uncertain. Inside a table it lands at the start of a cell ("ญ ญส่งรายงานความก้าวหน้า…"). Those copies are dropped, and no real text goes with them.

**Blocked by:** 04

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**The filter**
- [ ] A box is dropped only when all of these hold:
  - it is much shorter than the page's usual box;
  - it sits just above a taller box that spans it;
  - that taller box's text holds upper vowels or tone marks at that place;
  - no rule of a table lies between the two.
- [ ] Measured during grilling: 14 of 15 junk boxes on the synthetic table pages were such copies.
- [ ] **These must stay:**
  - a lone "-" in a cell (a looser filter tried during grilling dropped one);
  - a "-" on a line of its own;
  - short real text such as a footnote number.

**Check what changed**
- [ ] Run the harness on `corpus/synthetic`, `corpus/degraded` and this feature's table documents, with and without the filter. List every page whose output changes in Comments.
  - No real text may be lost.
  - Uncertain stretches made of junk should drop.

**Tests**
- [ ] `FakeEngine` can box a line's upper marks apart from the line, as PaddleOCR does.
- [ ] Fast tests:
  - a copy of the marks above a line is dropped, in a paragraph and in a cell;
  - a "-" alone in a cell stays;
  - a "-" on a line of its own stays;
  - a box over a line with no upper marks at that place stays;
  - a box separated by a rule stays.
- [ ] Checked by breaking the code on purpose: each guard has a test that fails without it.
- [ ] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments
