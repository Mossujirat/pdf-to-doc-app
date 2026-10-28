# 07: Stray mark boxes are dropped

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** On every OCR page, the detector sometimes boxes a line's upper vowels and tone marks apart from the line, as a small box just above it. The line's own reading already holds those marks, so the small box is a copy. It reads as junk such as "ญ ญ", "ว ญ 9" or "e A", marked uncertain. Inside a table it lands at the start of a cell ("ญ ญส่งรายงานความก้าวหน้า…"). Those copies are dropped, and no real text goes with them.

**Blocked by:** 04

**Status:** done

**Branch:** `feat/ocr-tables`

**The filter**
- [x] A box is dropped only when all of these hold:
  - it is much shorter than the page's usual box;
  - it sits just above a taller box that spans it;
  - that taller box's text holds upper vowels or tone marks at that place;
  - no rule of a table lies between the two.
- [x] Measured during grilling: 14 of 15 junk boxes on the synthetic table pages were such copies.
- [x] **These must stay:**
  - a lone "-" in a cell (a looser filter tried during grilling dropped one);
  - a "-" on a line of its own;
  - short real text such as a footnote number.

**Check what changed**
- [x] Run the harness on `corpus/synthetic`, `corpus/degraded` and this feature's table documents, with and without the filter. List every page whose output changes in Comments.
  - No real text may be lost.
  - Uncertain stretches made of junk should drop.

**Tests**
- [x] `FakeEngine` can box a line's upper marks apart from the line, as PaddleOCR does.
- [x] Fast tests:
  - a copy of the marks above a line is dropped, in a paragraph and in a cell;
  - a "-" alone in a cell stays;
  - a "-" on a line of its own stays;
  - a box over a line with no upper marks at that place stays;
  - a box separated by a rule stays.
- [x] Checked by breaking the code on purpose: each guard has a test that fails without it.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-10-28, implemented on branch `feat/ocr-tables`**

- **Measured first, with PaddleOCR, on every OCR page of `corpus/synthetic` and `corpus/degraded`:**
  - every short box under a taller one was a copy of marks: "ญ", "บ", "ะ", "e", "9", "2";
  - they were 13 to 40 px tall, against a usual box of 74 to 93 px: 0.45 of it at most;
  - each overlapped the taller box that spans it, by 6 to 86 px;
  - that box's text held an upper vowel or tone mark within 3 characters of the copy's place.
- **The filter** (`ocr._without_stray_marks`) drops a box only when all of these hold:
  - it is less than half the page's usual box tall;
  - another box spans it across the page;
  - it lies over that box's top half: it overlaps the box, and its middle is above the box's;
  - that box's text holds an upper vowel, sara am, or a tone mark within 3 characters of the share of its characters where the copy lies (`thai.UPPER_MARK`);
  - no rule lies between them: a cell's boxes are filtered apart from the rest, and from every other cell's.
- **Text-layer rows** go through the filter too, but they are never short, so they are never dropped.
- **`FakeEngine`:** `Boxed` is a box placed by hand, and `marks_over` places a copy of a line's marks where PaddleOCR draws one.
- **What changed, PaddleOCR, with the filter against without it:**

  | Page | CER | Uncertain | Cells |
  | --- | --- | --- | --- |
  | `ruled-table-scans` 1 | 0.0230 → 0.0164 | 4 → 3 | 8 → 9 of 12 |
  | `ruled-table-scans` 2 | 0.0337 → 0.0240 | 4 → 3 | 11 → 11 of 13 |
  | `ruled-table-scans` 4 | 0.0157 → 0.0078 | 2 → 2 | 14 → 15 of 16 |
  | `ruled-tables-drawn-as-shapes` 1 | 0.0230 → 0.0098 | 4 → 3 | 8 → 9 of 12 |
  | `ruled-tables-wrong-unicode-map` 1 | 0.0295 → 0.0164 | 5 → 4 | 6 → 7 of 12 |
  | `sideways-scans` 1 | 0.0168 → 0.0084 | 4 → 3 | 17 → 18 of 20 |

  - Every other page of `corpus/synthetic`, and every page of `corpus/degraded`, came out the same.
  - **No real text was lost:** no page's CER rose, and no text is missing.
  - On OCR pages in total: CER 0.0103 → 0.0079, uncertain stretches 35 → 30, cells 152 → 157 of 181.
  - The share of edits left unmarked rose from 0.71 to 0.79: the stretches dropped were junk, all of it wrong and all of it marked.
- **Left as junk:** on `ruled-table-scans` page 2, a "ญ" over the lower half of "ค่าตอบแทนผู้วิจัย", a copy of a mark under the line. The filter takes marks above the letters only, so that a dash boxed apart within a line stays.
- **Known limits:**
  - A footnote's number raised within a line, short and over a marked word, would be dropped as a copy.
  - The usual box height counts the copies too: a page holding fewer lines than copies would drop none.
- **Tests:**
  - `test_ocr_pages.py`: a copy dropped from a paragraph; a dash on a line of its own, a dash boxed apart in the middle of a line, a footnote's number raised before its line, a short box over a line with no upper marks there, and a note squeezed in over a line, all kept.
  - `test_ocr_tables.py`: a copy dropped in a cell; a dash alone in a cell, and a dash at the foot of a cell over the box of the marked line in the cell below, both kept.
- **Checked by breaking the code on purpose,** with `test_ocr_pages.py` and `test_ocr_tables.py`:

  | Broken | Tests that fail |
  | --- | --- |
  | no filter | 2, the copies |
  | not only short boxes | 8 |
  | not only boxes another spans | 1, the footnote's number before its line |
  | not only boxes overlapping another | 3 |
  | not only boxes on another's top half | 2, the dashes |
  | marks not looked at | 1, the box over unmarked text |
  | copies taken across a rule | 1, the dash at the foot of a cell |

**2026-10-28, after code review (two axes)**

- **Spec:**
  - **"Sits just above a taller box":** the code had asked only that the box overlap the taller one, so a short box on a line's lower half, such as a dash boxed apart within it, would have gone. A copy must now lie over the other box's top half. A new test, a dash boxed apart mid-line, failed before.
  - **Sara am** holds its ring above the letters, and is now among the upper marks.
  - **Guards with no test, taken out:** that the other box is taller, and that a text-layer row is never dropped. Both were already given by the other rules.
  - **The rule guard's test** was rebuilt: once a copy must lie on the top half, a box under a rule no longer reached the line above. A rule matters the other way round: a dash at the foot of a cell, over the top of a marked line in the cell below whose box reaches over the rule, as PaddleOCR's do.
  - The share-of-characters window and the usual box height are recorded above, as known limits.
- **Standards: no written rule broken. Fixed:**
  - `_MARKS_NEAR` says where its 3 comes from;
  - the upper marks are `thai.UPPER_MARK`, beside `MARK`;
  - the box under a copy is named `under`, not `line`, which in `ocr.py` means a printed line;
  - `_ocr_page`'s docstring names the step;
  - `FakeEngine`'s `Stray` is `Boxed`, as tests place real text with it too;
  - the tests say where their boxes lie.
- **Run:** pytest (624 passed and 1 skipped on Windows, 625 passed in the Linux image), mypy, `pytest -m ocr` (23 passed in the image), and the harness in the image: cells 157/181 on OCR pages and 46/46 on text pages.
