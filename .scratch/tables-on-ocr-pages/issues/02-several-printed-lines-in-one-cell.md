# 02: Several printed lines in one cell

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A table cell holding several printed lines comes out the way a reader takes it, in both outputs. Today every line of a cell is joined by the Thai line rules. That glues stacked items into one word ("ค่าวัสดุสำนักงานค่าถ่ายเอกสาร"), and puts their amounts together in the next cell, apart from their items. This ticket sets the rule on text pages, where character positions are exact. Ticket 04 reuses it on OCR pages.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**The rule**
- [ ] **Sub-rows.** A ruled row splits into sub-rows when two or more of its cells hold the same number of lines, more than one, and those lines line up: their centres lie within about a third of a line height.
  - The row's other cells span the sub-rows, as merged cells.
- [ ] **Otherwise, within a cell:**
  - a line that fills its cell carries on into the next line, joined by the Thai line rules;
  - a short line ends its item, and the line break is kept.

  "Fills" follows the same idea as a line that stops short in a paragraph. Its threshold is the implementer's.
- [ ] **Two cells that both wrap to the same number of full lines** are wrapped sentences. They are not split into sub-rows.
- [ ] **Every character still comes out exactly once,** as ticket 04 of the converter requires.

**Outputs**
- [ ] The document model's cell text may hold line breaks.
- [ ] **Markdown:** a break inside a cell is `<br>`, in GFM and HTML tables alike. `|` is still escaped.
- [ ] **DOCX:** a break inside a cell is a line break in the cell's paragraph, with the Thai font settings unchanged. Check once in real Word that the break shows and the Thai renders right.

**Corpus**
- [ ] **The `tables` document is rebuilt.** Its cell "ส่งรายงานความก้าว / หน้าฉบับที่หนึ่ง" breaks mid-word in a cell that is not full. It must fill its cell before it wraps, as Word wraps it. Update its reference and regenerate the corpus.
- [ ] **A new synthetic text-page document**, with reference text, holds a coarse ruled table:
  - stacked items beside their amounts, which become sub-rows;
  - a cell listing short items beside a single total, which keeps its breaks;
  - a wrapped description, which joins.
- [ ] The text-page gate holds: zero broken text on text pages.

**Tests**
- [ ] Fast tests through the conversion function, reading the Markdown tables and the DOCX back:
  - sub-rows that line up;
  - stacked short items keep their breaks;
  - a wrapped sentence is joined;
  - two cells wrapping to the same number of full lines are not split;
  - merged cells around sub-rows.
- [ ] Checked by breaking the code on purpose. Each part has a test that fails without it:
  - the sub-row split;
  - the line-up test;
  - "fills its cell";
  - keeping the break.
- [ ] Run pytest, mypy, the harness, and the checks in the Linux container.

## Comments
