# Tables on OCR pages

Status: ready-for-agent

## Problem Statement

People convert contracts and their attachments to paste into an AI chat or edit in Word. Many of the tables that matter most sit on OCR pages: budgets, payment schedules, price schedules, work plans, researcher profiles, and tables that share out intellectual property. On these pages the converter loses the tables:

- **Rows run together.** OCR rows are joined into paragraphs, so a whole table becomes one or two long paragraphs.
- **Cells are mixed.** When a cell's text wraps onto a second line, that line lands in the next row. In a payment schedule, the amount landed in the middle of the description's sentence. Two-row tables of dates came out as one line each.
- **Nothing warns the reader.** Every word may be right, so nothing is marked as uncertain text. Yet the content is wrong: an amount reads as belonging to the wrong item. An AI chat given such text answers wrongly, with confidence.

This happens on every kind of OCR page:
- scans;
- sideways pages, once they are turned upright;
- pages whose text layer cannot be trusted, such as a contract's budget pages, where "การ" reads "กำร";
- pages whose text is drawn as shapes, as some PDF printers write them.

In the local samples:
- **The 110-page contract:** about 25 scanned pages had their tables flattened or their cells interleaved, and its budget tables on pages 69–72 came out one row per line or run on.
- **A 34-page scanned supplement:** seven pages had their tables flattened.
- **A five-page agreement with its text drawn as shapes:** its ruled tables were flattened too.
- **Sideways pages:** most of the twelve in the samples hold tables.

Two more faults surfaced while measuring:
- **Whole lines vanish on OCR pages that are not scans.** On a crisp page rendered from the PDF, the OCR detector finds some lines and throws them away. The output simply lacks them, and nothing warns the reader.
- **Stacked items in one ruled cell are glued together,** text pages included. Some tables put several printed sub-rows in one ruled cell. Joining a cell's lines turns "ค่าวัสดุสำนักงาน", "ค่าถ่ายเอกสาร" and "ค่าไปรษณีย์" into one word, and puts their three amounts together in the next cell, apart from their items.

## Solution

Tables on OCR pages come out as tables in both outputs, wherever the converter can see the table's rules. Where it cannot be sure, it says so instead of guessing:

- **A ruled table** comes out as a table. Merged cells are kept, every cell holds its own text, and Thai inside cells is intact. This works the same on:
  - scans;
  - sideways pages once turned;
  - pages whose text layer cannot be trusted;
  - pages whose text is drawn as shapes.
- **A table seen but not fully ruled,** such as one with only its header boxed, is an **incomplete table**. The output gives it row by row, each printed line on its own, after the label `[ตารางอาจไม่สมบูรณ์]`.
- **A table with no rules at all** comes out one line per row, with no label, as unruled tables on text pages do. The converter cannot tell such a table from a form or a list of labels and their values, so it does not guess.
- **A cell holding several printed lines:**
  - lines that line up across two or more cells become sub-rows;
  - otherwise a line that fills its cell carries on into the next, as a wrapped sentence does;
  - a short line ends its item, and the line break is kept inside the cell.

  This applies to every table, text pages included.
- **Uncertain text inside cells** is marked as it is anywhere else: `<mark>` in Markdown, yellow in DOCX, and counted in the summary.
- **The summary** tells about tables on OCR pages apart from placeholders: how many came out as tables, and how many are incomplete, with their pages.
- **No line is lost** on OCR pages that are not scans.
- **Stray boxes of upper marks are gone.** The detector sometimes boxes a line's vowels and tone marks apart from the line, though the line's own reading already holds them.

No new model is added. Finding a table's rules takes about 0.2 seconds per OCR page, and memory does not grow. For the structure of tables with no rules, Accurate mode (Typhoon) is the way, since it reads tables itself.

## User Stories

1. As a document user, I want a ruled table on a scanned page to come out as a table, so that a budget or a schedule stays readable.
2. As a document user, I want each cell of such a table to hold exactly the text printed in it, so that an amount stays with its item.
3. As a document user, I want a cell whose text wraps onto a second line to keep both lines in that cell, so that the second line does not land in the next row.
4. As a document user, I want merged cells on scanned tables preserved, so that a heading spanning two columns still spans them, in Markdown as an HTML table and in DOCX as real merged cells.
5. As a document user, I want a two-row table, such as a start date beside an end date, to come out as a table, so that each date stays under its heading.
6. As a document user, I want a table printed sideways to come out as a table once the page is turned upright, so that price schedules and work plans printed across the page stay usable.
7. As a document user, I want tables on pages whose text layer cannot be trusted to come out as tables, so that a contract's budget pages keep their structure, not only their text.
8. As a document user, I want tables on pages whose text is drawn as shapes to come out as tables, so that an agreement printed that way keeps its payment schedule.
9. As a document user, I want every Thai vowel and tone mark inside a cell intact, so that cell text reads like the original.
10. As a document user, I want no spaces inside Thai words in cells, so that a wrapped cell reads as one sentence.
11. As a document user, I want stacked items in one ruled cell, each with its own amount beside it, to become sub-rows, so that each item stays with its amount.
12. As a document user, I want a cell listing several short items to keep each item on its own line, so that the items are not glued into one word.
13. As a document user, I want a sentence that wraps inside a cell joined back without a break, so that it reads as one sentence.
14. As a document user, I want the same rules for several lines in a cell on text pages, so that a coarse ruled table in a PDF's text layer is not glued either.
15. As a document user, I want a table whose rules are incomplete marked `[ตารางอาจไม่สมบูรณ์]`, with its rows one per line, so that I know to check its structure against the original.
16. As a document user, I want a table with no rules to come out one line per row, so that its rows do not run together into a paragraph.
17. As a document user, I want no table structure guessed for a table with no rules, so that I never get cells that look right but hold the wrong text.
18. As a document user, I want a form or a list of labels and values on a scan kept one pair per line, so that each label stays with its value.
19. As a document user, I want misread words inside a table cell marked as uncertain text, so that I know which cells to check.
20. As a document user, I want uncertain text in cells highlighted yellow in DOCX, so that I can find it in Word.
21. As a document user, I want the summary to tell me how many tables on OCR pages came out as tables and how many may be incomplete, and on which pages, so that I know how far to trust them.
22. As a document user, I want an incomplete table counted apart from placeholders, so that the summary does not call transcribed text "not transcribed".
23. As a document user, I want no line of text to vanish from an OCR page that is not a scan, so that nothing is missing without warning.
24. As a document user, I want stray marks that OCR boxed apart from their line left out, so that cells and paragraphs do not start with junk such as "ญ ญ".
25. As a document user, I want a lone "-" in a cell kept, so that an empty amount still shows as the original shows it.
26. As a document user, I want a box drawn around a note or a paragraph left as text, so that a boxed notice does not become a one-cell table.
27. As a document user, I want ruled boxes in a scan's header or footer treated as page furniture, as on text pages, so that a ruled letterhead does not become a table on every page.
28. As a document user, I want stamps, underlines and photos on a scan never turned into tables, so that no empty or false tables appear.
29. As a document user, I want a table on a page set in two columns kept whole, so that splitting the page into columns does not cut through it.
30. As a document user, I want a table placed in reading order, where it sits on the page, so that the text before and after it stays in order.
31. As a document user, I want a note typed over a scanned table to land in the cell it sits in, so that it stays with what it annotates.
32. As a document user, I want conversion to take about the same time as before, so that a 110-page contract still converts within about 15 minutes.
33. As a document user of the web service, I want a file with many scanned tables to convert within the service's limits, so that it is not refused or cut off.
34. As a document user of the web service, I want the results page to note incomplete tables on each page apart from placeholders, so that I know which pages to check.
35. As a document user of the web service, I want the page that explains how a conversion works to say what happens to tables on OCR pages, so that its description stays true.
36. As a document user who keeps images, I want kept scans unchanged, so that choosing kept images still shows each scan as it is.
37. As a document user who keeps images, I want tables on pages that are still read with OCR, such as pages with an untrusted text layer, to come out as tables too, so that kept images do not lose them.
38. As a document user, I want Accurate mode to remain the way to get the structure of tables with no rules, so that I have a choice when such a table matters.
39. As a maintainer, I want the quality harness to report how many cells land in the right place on pages whose reference holds tables, so that table structure is measured, not only characters.
40. As a maintainer, I want synthetic corpus documents with tables on every kind of OCR page, ruled, partly ruled and unruled, with reference text, so that the harness measures each case.
41. As a maintainer, I want a synthetic document with OCR pages that are not scans, holding a line that used to be lost, so that the lost-line fault cannot return unnoticed.
42. As a maintainer, I want the synthetic table fixture to wrap cell text the way Word does, so that the corpus does not reward breaking a word in a cell that is not full.
43. As a maintainer, I want the table method to work through the OCR engine interface, so that any engine that gives text boxes, and the fake engine, get tables.
44. As a maintainer, I want no new OCR model or large dependency, so that the Docker image and the sandbox's memory stay as they are.
45. As a maintainer, I want each new mechanism covered by a test that fails without it, so that a later change cannot remove it silently.

## Implementation Decisions

**Delivery order.** Ticket 33 (lost lines) comes first, then ticket 14's work. The order of the whole effort is 33, 14, 16, 17, 15.

### Lost lines on OCR pages that are not scans (ticket 33)

- **Cause, measured.** PaddleOCR's detector scores each region by its mean probability over the region's smallest enclosing rectangle, and drops regions under `box_thresh` (0.6).
  - On a crisp render, thin spurs where upper marks join a line (ผู้, นี้) stretch that rectangle to about twice the text's height. The lost line then scored 0.54–0.58.
  - Softened before the detector shrinks it to 1280 px, the same line scored:
    - 0.64–0.78 with a Gaussian blur of sigma 1 px;
    - 0.61–0.77 when shrunk with area averaging;
    - 0.64–0.75 when rendered at 200 dpi.
- **Scope.** Only OCR pages that are not scans: pages whose text layer cannot be trusted, and pages whose text is drawn as shapes.
  - Scans keep today's image, unless the real samples show that their 300-dpi scans lose lines the same way.
  - Blurring the corpus's scans raised their CER from 0.0072 to 0.0082.
- **Where.** The code that renders a page for OCR, which knows whether the page is a scan.
  - Today the scan test runs only when images are kept. It is cheap, and now runs for every OCR page.
  - Which softening to use is the implementer's choice, made with the harness. Lowering `box_thresh` is the alternative; measure the junk boxes it adds.
  - Any engine may receive the softened image.

### Reading a table on an OCR page (ticket 14)

All of this happens where OCR pages are read, through the `OcrEngine` interface, as tickets 18 and 21 work. It comes after any sideways turn, so a turned page gets tables too, and it uses only the page image and the engine's boxes.

- **Stray mark boxes** are dropped first, on every OCR page. A stray mark box is a box of upper marks that the detector boxed apart from the line below, whose reading already holds them.
  - A box goes only when it is much shorter than the page's usual box, and sits just above a taller box that spans it.
  - It also goes only when that taller box holds upper vowels or tone marks at that place, and never across a rule.
  - A lone "-" in a cell, or a "-" on a line of its own, must stay. A looser filter tried during grilling lost one.
- **Finding the grid.** Long horizontal and vertical rules are found in the page image, and cells are built from them, with row and column spans for merged cells.
  - **The frame:** the engine's boxes are straightened by the page's slant. The grid must lie in that same frame, by straightening the image or the rules the same way.
  - **Thick pieces are not rules.** A piece thicker than about max(8 px, 0.15 of a box's height) is left out. Without this, a dark photo became an empty table.
  - **Not tables:**
    - a single ruled frame around text is boxed text;
    - a grid lying wholly in the page's edge bands is read as rows, so ruled headers and footers stay page furniture, as on text pages;
    - a grid inside another grid is dropped, as on text pages.
  - **Measured on synthetic pages, the grid held:**
    - at 150 dpi;
    - at 3° of skew;
    - with heavy grain.

    It broke at 100 dpi with heavy grain, where lost pieces of rule gave false spans.
  - **No false grid** came from stamps, underlines or page edges on the corpus's scans.
  - **OpenCV** may be used. It is already installed with PaddleOCR, under Apache-2.0, and becomes a direct, pinned dependency. Numpy alone is also fine.
- **Placing text in cells.** Each of the engine's boxes goes to the cell that holds its centre, and boxes outside every cell stay as rows.
  - Boxes reach over rules only by the detector's padding. No box crossed a rule through its middle on the test pages.
  - A text-layer row over a scan that falls inside a grid goes into its cell, as a box does.
- **An incomplete table.** A table whose text cannot be placed with certainty is output row by row, each printed line on its own, after the label. Two cases:
  - **Rules seen but not a whole grid,** such as a boxed header row with rows under it set out in columns that line up with its column rules. The incomplete table takes the header row and those rows.
  - **A box that crosses a rule through its middle,** whose text would belong to two cells.

  A table with no rules at all is never an incomplete table: it gets no label.
- **One line per row outside tables.** On every OCR page, an OCR row whose neighbouring boxes are set apart by a gap wider than two font sizes is set out in columns (`in_columns`), as on text pages. It stays a line of its own.
  - On 381 OCR rows measured, only table rows, label–value pairs, tab-stop lists, signature lines and junk were flagged, and no body text.
  - The two-column cover sheet's CER fell from 0.0194 to 0.0039.
- **Columns and reading order.**
  - A table's boxes are taken out before the page is cut into columns (ticket 18), so a table is never split across columns.
  - The table is placed in reading order by its top, as tables on text pages are.
  - The page's parsed rows carry its tables, as a text page's do.

### Several printed lines in one cell (every table)

This rule applies wherever tables are built, on text pages and on OCR pages alike:
- **Sub-rows.** A ruled row splits into sub-rows when two or more of its cells hold the same number of lines (more than one), and those lines line up: their centres lie within about a third of a line height. The other cells of the row span the sub-rows.
  - It gave 13/15 cells, with the structure right, on a coarse table.
  - It did not trigger on wrapped description cells.
- **Otherwise, within a cell:**
  - a line that fills its cell carries on into the next, joined by the Thai line rules;
  - a short line ends its item, and the break is kept.

  "Fills" follows the same idea as a line that stops short in a paragraph. Its threshold is the implementer's.
- **The risk** is two cells that both wrap to the same number of full lines. They line up, but they are wrapped sentences, not sub-rows. The "fills its cell" test guards it: sub-rows are short lines.

### Document model

- **A table cell's text may hold line breaks,** and carries its uncertain text as stretches, as paragraphs do.
- **The incomplete table is a block of its own.** It holds its printed rows, each a line with its uncertain text.
  - The `incomplete_table` placeholder kind is removed: in the glossary, an incomplete table is not a placeholder.
  - Every block still records its source page.
- **The one accessor for a block's uncertain text** also covers table cells and an incomplete table's rows. Renderers and the summary keep reading uncertain text through it.

### Renderers

- **Markdown:**
  - A line break inside a cell is `<br>`, in GFM and in HTML tables alike.
  - Uncertain text inside a cell is wrapped in `<mark>`.
  - An incomplete table is the label `[ตารางอาจไม่สมบูรณ์]` as a paragraph of its own, then each row as a paragraph.
- **DOCX:**
  - A line break inside a cell is a line break in the cell's paragraph.
  - Uncertain text inside a cell is highlighted yellow.
  - An incomplete table is the label, then each row as a paragraph.
  - Merged cells and the Thai font settings are kept as they are.

### Summary and web

- **The summary** gains, per page, the number of tables on OCR pages that came out as tables, and the number of incomplete tables.
  - **Its headline** says both counts, with the pages of the incomplete ones. It says this apart from the list of what was not transcribed. Tables on text pages are not counted.
  - **The Thai wording** is approved by the user at /implement.
- **The web results page** lists incomplete tables in each page's notes, apart from placeholders. A page with an incomplete table is tagged to check, as one with uncertain text is.
- **The web page "ข้างในทำอะไรกับไฟล์ของคุณ"** says today that OCR pages do not yet get headings or tables. That sentence changes in this work, as the converter spec requires. The new text says:
  - ruled tables on OCR pages become tables;
  - tables with incomplete rules are labelled;
  - tables without rules come out one line per row.

### Quality harness

- **A new measure.** On a page whose reference text holds tables, the harness reports how many reference cells the output holds in the same place.
  - A cell counts when it sits at the same row and column, with merged cells expanded, and holds the same text.
  - The tables are those of the reference and output Markdown: GFM and HTML tables, with `<mark>` dropped.
  - It is reported per page and in total, in JSON and in the readable table.
- **Today's measures stay as they are.** Cell breaks (`<br>`) count as spaces when pages are compared, like other tags.

### Corpus

- **A synthetic document of OCR pages that are not scans,** one with a wrong ToUnicode map and one with text drawn as shapes. Each holds a line that is lost today: a line with upper marks over its first and last words, as "ผู้…นี้".
- **Synthetic documents with tables on OCR pages:**
  - ruled tables on a scan, on an untrusted page and on a page drawn as shapes: a payment schedule with wrapped cells, a budget with merged cells, a two-row table of dates, and a coarse table with sub-rows;
  - a sideways ruled table, both ways;
  - a table with only its header boxed;
  - tables with no rules.
- **Wrapped cell text fills its cell** before it wraps, as Word wraps it. The existing table fixture breaks "ความก้าว|หน้า" in a cell that is not full. It is rebuilt.
- **A coarse table on a text page,** so that the sub-row rule is gated there too.
- **Expected results.** References give tables as HTML where cells are merged, and `<br>` where a cell keeps a break. The text-page gate (zero broken text on text pages) still holds.

### Budgets

- **Time.** An OCR page takes at most about 0.3 s longer. The grid took 198 ms at the median per 300-dpi page on 4 threads, and 257 ms at most.
  - Ticket 08's target, a 110-page mixed document in about 15 minutes, still holds.
  - So does the sandbox's 30 minutes for 150 pages on 4 CPUs.
- **Memory.** No model is added, so the conversion's peak stays where it is: 1.34–1.57 GiB in the 2 GiB sandbox. Only one working copy of a page image is held at a time.

### Engines and other settings

- **Any engine that gives text boxes** gets the method, including `FakeEngine`.
- **Accurate mode keeps Typhoon's own HTML tables** (ticket 15). Typhoon gives no boxes, so the grid is not used there.
- **Kept images is unchanged.** A kept scan is not read, so it gets no table. Pages still read with OCR when images are kept get tables in both settings: pages with an untrusted text layer, and pages drawn as shapes.

### Rejected

**PaddleOCR's table models, PP-StructureV3 included.** They were measured on the same synthetic pages:

| Method | Cells right on ruled pages | Cells right on unruled pages | Peak memory | s per page | Image grows by |
| --- | --- | --- | --- | --- | --- |
| rules from the image, as decided | 82/132, and 36/40 sideways | 2/29 | 1.35 GiB, no change | +0.2 | nothing |
| PP-StructureV3 | 81/132, and 36/40 | 12/29 | 3.06 GiB | 19 | about 1 GB, and 25 packages |
| layout L + SLANet_plus | 82/132, and 36/40 | 12/29 | 2.13 GiB | 5.5 | about 130 MB |

- On ruled tables they were no better.
- On unruled tables PP-StructureV3 was unreliable. It put intro lines into a cell, dropped the closing paragraph from a page, and missed a table.
- Both large routes exceed the sandbox's memory, and PP-StructureV3 would take about 48 minutes for 150 pages.

**The PDF's own vectors as the grid.** They worked on pages with an untrusted text layer. On pages drawn as shapes, PyMuPDF's table finder throws away a table with no text, and glyph paths cut its grid, so it would need two workarounds inside PyMuPDF. The image method gives the same grids on both kinds of page.

## Testing Decisions

- **A good test calls the conversion function with a real source file,** built by the corpus's PDF builder. It asserts only on what a user sees:
  - the Markdown, with its tables parsed back into cells;
  - the DOCX read back;
  - the summary.

  It never asserts on the grid, the boxes or which helper ran.
- **Seams: only the existing ones,** confirmed with the user:
  - the conversion function;
  - the `OcrEngine` interface, with `FakeEngine` in fast tests and real PaddleOCR in `pytest -m ocr`;
  - the outer pieces that already have tests: the harness and the web pages.

  No new seam is added.
- **`FakeEngine` grows as ticket 21 grew it.** It must:
  - return the text of a ruled table's cells as boxes where the PDF builder draws them;
  - box a line's upper marks apart from the line, as PaddleOCR sometimes does.

  The page image comes from the real PDF, so the rules are really there.
- **Fast tests, with `FakeEngine`.** These must come out as tables:
  - a ruled table on a scan, on a page with an untrusted text layer, and on a page drawn as shapes, each with wrapped cells and merged cells;
  - a two-row table;
  - a sideways table, both ways.

  And these cases:
  - **Several lines in a cell:** sub-rows that line up; stacked short items keeping their breaks; a wrapped sentence joined. The same on a text page.
  - **Labels:** a table with only its header boxed is an incomplete table, with its label and its rows one per line, and the summary counts it. A table with no rules comes out one line per row, with no label.
  - **Not tables:** a frame around a paragraph; a ruled box in the edge band; a stamp, an underline or a dark photo.
  - **Uncertain:** a box crossing a rule through its middle makes the table incomplete.
  - **A note typed over a scanned table** lands in its cell.
  - **Uncertain text inside cells** is marked in Markdown and DOCX, and counted.
  - **Stray mark boxes** are dropped, while a lone "-" in a cell and a "-" on a line of its own stay.
  - **One line per row:** a label–value list on an OCR page gives one line per pair, and body text is not split.
  - **Pages in two columns** still read column by column, and a table on such a page stays whole.
  - **DOCX:** merged cells, breaks inside cells, and highlights inside cells.
- **Real-OCR tests (`pytest -m ocr`):**
  - ticket 33's lost line is read on a page with an untrusted text layer and on a page drawn as shapes;
  - a ruled scanned table and a sideways ruled table come out as tables with PaddleOCR.
- **Harness and corpus.** `test_evaluate` covers the new cells measure. The corpus test scores the new table documents with PaddleOCR, as the two-column and sideways documents are scored today.
- **Web tests:** the results page's notes for an incomplete table, and the new text of the explanation page.
- **Checked by breaking the code on purpose,** as in tickets 18 and 21. Each mechanism has a test that fails without it:
  - the softening;
  - the scan test;
  - the mark filter and its guards;
  - thick pieces left out;
  - the frame, the edge band and the nested grid;
  - placing boxes by centre;
  - the crossing box;
  - the partial rules;
  - the column flag;
  - taking tables out of the column cut;
  - sub-rows;
  - "fills its cell".
- **Prior art:**
  - the OCR page tests: `FakeEngine`, sideways pages, two-column pages;
  - the text-page table tests: grids, spans, every character exactly once;
  - the uncertain-text tests;
  - the PaddleOCR tests;
  - the corpus test;
  - the harness tests;
  - the web results tests.
- **Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.**
- **The local samples are checked at /implement only,** with the user's permission asked then. The terms are those of tickets 18 and 21:
  - converted on this machine, never by a sub-agent;
  - nothing committed or sent;
  - counts only in tickets;
  - the outputs deleted after.

  What to check:
  - **Lines lost** on pages 69–72 of the contract and on the agreement's five pages, before and after ticket 33, and whether the samples' scans lose lines.
  - **Every page with a table,** checked against its image:
    - the contract's scanned and sideways table pages and pages 69–72;
    - the agreement's tables;
    - the supplement's table pages.
  - **Every other OCR page** reads as before, apart from one line per row.
  - **How long each page takes.**
  - **If a real table's content comes out wrong,** stop and ask the user.

## Out of Scope

- **The structure of tables with no rules** in default mode. Accurate mode is the way.
- **PaddleOCR's table and layout models.**
- **Sideways column headers inside upright tables** (ticket 29). Once read right, their text lands in its header cell through this work.
- **Ticks in table cells** (ticket 26). A cell whose tick is lost comes out empty.
- **Upside-down scans** (ticket 30), and headings on OCR pages.
- **Typhoon's tables** (ticket 15).
- **Tables on kept pages,** which are not read.
- **A table that runs on across pages.** Each page's part is a table of its own.
- **Deploying.** Production stays on its current commit until the user asks.

## Further Notes

- **Where the decisions came from.** They were made while grilling ticket 14 with the user on 2026-10-25. The measurements behind them, all on synthetic pages, are in ticket 14's comment of that date and in ticket 33.
- **Glossary.** This spec uses the terms of `GLOSSARY.md`. **Incomplete table** was added during the grilling: its text is transcribed, so it is not a placeholder.
- **The converter spec's OCR adapter section** said to try PP-StructureV3, and otherwise output tables as lines under a placeholder. This spec replaces that line. Its list of placeholder kinds loses "incomplete table".
- **Tickets and branch.** Ticket 33 is ready on its own. Ticket 14's work is cut into tickets by /to-tickets, and the branch and PR split are decided then.
