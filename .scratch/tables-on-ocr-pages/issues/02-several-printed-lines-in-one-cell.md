# 02: Several printed lines in one cell

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A table cell holding several printed lines comes out the way a reader takes it, in both outputs. Today every line of a cell is joined by the Thai line rules. That glues stacked items into one word ("ค่าวัสดุสำนักงานค่าถ่ายเอกสาร"), and puts their amounts together in the next cell, apart from their items. This ticket sets the rule on text pages, where character positions are exact. Ticket 04 reuses it on OCR pages.

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/ocr-tables`

**The rule**
- [x] **Sub-rows.** A ruled row splits into sub-rows when two or more of its cells hold the same number of lines, more than one, and those lines line up: their centres lie within about a third of a line height.
  - The row's other cells span the sub-rows, as merged cells.
- [x] **Otherwise, within a cell:**
  - a line that fills its cell carries on into the next line, joined by the Thai line rules;
  - a short line ends its item, and the line break is kept.

  "Fills" follows the same idea as a line that stops short in a paragraph. Its threshold is the implementer's.
- [x] **Two cells that both wrap to the same number of full lines** are wrapped sentences. They are not split into sub-rows.
- [x] **Every character still comes out exactly once,** as ticket 04 of the converter requires.

**Outputs**
- [x] The document model's cell text may hold line breaks.
- [x] **Markdown:** a break inside a cell is `<br>`, in GFM and HTML tables alike. `|` is still escaped.
- [x] **DOCX:** a break inside a cell is a line break in the cell's paragraph, with the Thai font settings unchanged. Check once in real Word that the break shows and the Thai renders right.

**Corpus**
- [x] **The `tables` document is rebuilt.** Its cell "ส่งรายงานความก้าว / หน้าฉบับที่หนึ่ง" breaks mid-word in a cell that is not full. It must fill its cell before it wraps, as Word wraps it. Update its reference and regenerate the corpus.
- [x] **A new synthetic text-page document**, with reference text, holds a coarse ruled table:
  - stacked items beside their amounts, which become sub-rows;
  - a cell listing short items beside a single total, which keeps its breaks;
  - a wrapped description, which joins.
- [x] The text-page gate holds: zero broken text on text pages.

**Tests**
- [x] Fast tests through the conversion function, reading the Markdown tables and the DOCX back:
  - sub-rows that line up;
  - stacked short items keep their breaks;
  - a wrapped sentence is joined;
  - two cells wrapping to the same number of full lines are not split;
  - merged cells around sub-rows.
- [x] Checked by breaking the code on purpose. Each part has a test that fails without it:
  - the sub-row split;
  - the line-up test;
  - "fills its cell";
  - keeping the break.
- [x] Run pytest, mypy, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, implemented on branch `feat/ocr-tables`**

- **"Fills its cell" is Word's own rule.** A line wraps into the next when the next line's first word would not have fitted in the room left after it. (Changed after code review to work by widths; see below.)
  - **The room** ended as far in from the cell's right edge as the text starts from its left.
  - **The first word** is cut by the word list's tokenizer for Thai, and up to a space otherwise. Its width is its share of the line's letters, with marks above and below left out.
  - **Why not a fixed gap:** in a cell set flush left, a long Thai word can stop a wrapped line several letters short of the edge. A fixed gap would have kept such a break inside a sentence.
  - **When the estimate errs,** it errs toward keeping a break, which is harmless. Joining two items into one word is what the rule must avoid.
- **Sub-rows**
  - Only cells with no merge down, whose lines are all items (none wraps), take part.
  - Lines line up when their middles are within 0.4 of the font size.
  - The row's other cells, and cells above that reach into the row, get their row span stretched over the new sub-rows.
- **The data:** a table cell's printed lines now carry where they sit (`layout.CellLine`), and each cell carries its ruled box, so the same rule will serve OCR pages (ticket 04).
- **Outputs:**
  - The model's cell text holds `\n` for a kept break.
  - Markdown writes it as `<br>`.
  - python-docx turns it into a line break in the cell's paragraph by itself.
- **Real Word,** the `coarse-table` page opened through COM and exported:
  - the sub-rows are merged under one category;
  - the two items stand on two lines in one cell;
  - the wrapped description is one sentence, which Word wraps to its own column width;
  - the Thai renders right.
- **Corpus:**
  - `tables` now wraps "ส่งรายงานความก้าวหน้าฉบับ / ที่หนึ่ง" in its 200-pt cell, as Word would.
  - The new `coarse-table` holds 16 cells, all in place, with CER 0.
  - Text pages hold 46/46 cells in place in total.
- **Tests:**
  - `test_tables.py`: the wrapped-cell test now wraps as Word does, and five tests are new: sub-rows, short items beside one total, two wrapped sentences side by side, items that do not line up, and a merged cell above a row of sub-rows.
  - `test_docx_output.py` reads the merged sub-rows and a kept break back from the DOCX.
- **Checked by breaking the code on purpose.** Every mechanism has a test that fails without it:
  - no sub-row split: 3 tests fail;
  - lines need not line up: 1;
  - every line wraps: 5;
  - no line wraps: 2.
- **Run:** pytest (569), mypy and the harness. The checks in the Linux container ran with ticket 03.

**2026-10-26, after code review (two axes, tickets 01–03 together)**

- **Spec found a real fault:** "fills its cell" assumed text set flush left.
  - It measured the room from the line's right end, as far in from the right edge as the text starts from the left.
  - So amounts set flush right (`12,000 / 3,500 / 1,200`) counted as wrapping. They were joined into one cell, and the row never split into sub-rows.
  - Short items centred in a cell were glued into one word.
  - Every fixture drew its text flush left, so no test caught it. Ticket 04 needs the rule on OCR pages, where amounts are often set flush right.
- **The fix:** a line wraps when its width and the next line's first word would not fit across the cell together.
  - The cell's padding is the least room its text leaves at either edge, at most half a font size.
  - Flush left, it decides exactly as before.
  - `pdf_builder.Cell` gained `align`.
  - New tests: amounts set flush right become sub-rows; short items keep their breaks and a wrapped sentence joins, set flush left, flush right or centred. Before the fix, the flush-right and centred cases failed.
- **Standards (no rule broken), fixed:**
  - clearer names: `itemised` and `lined_up` instead of one `stacked` for two sets, `row_index` and `cell_index`;
  - `_SAME_SUB_ROW` now says where 0.4 comes from;
  - `RawCell` is built with keywords again;
  - a cell that holds lines asserts that it has a box, where a branch that could not run had stood;
  - `first_word`'s docstring now says it cuts other text at punctuation too.
- **Run again:** pytest on Windows (579) and in the Linux container (580), mypy, and the harness, with text pages still at 46/46 cells.
