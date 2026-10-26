# 04: Ruled tables on scans

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A ruled table on a scan comes out as a table in both outputs, sideways pages once turned upright included. Each cell holds the text printed in it, merged cells are kept, and a wrapped cell keeps both its lines. A scanned budget, payment schedule or price schedule can then be read, and pasted into an AI chat, as a table. Today it comes out as paragraphs with its cells mixed.

**Blocked by:** 01, 02

**Status:** done

**Branch:** `feat/ocr-tables`

**Finding the grid**
- [x] **Where:** where OCR pages are read, through the `OcrEngine` interface, as tickets 18 and 21 of the converter work. It comes after any sideways turn, and uses only the page image and the engine's boxes.
- [x] **The rules:** long horizontal and vertical rules are found in the page image. Cells are built from them, with row and column spans for merged cells.
- [x] **The frame:** the grid lies in the same frame as the engine's boxes, which are straightened by the page's slant.
- [x] **Not rules:** pieces thicker than about max(8 px, 0.15 of a box's height). A dark photo made an empty table without this.
- [x] **Not tables:**
  - a single ruled frame around text;
  - a grid wholly inside the page's edge bands, which is read as rows, so ruled headers and footers stay page furniture;
  - a grid inside another grid.
- [x] **No table from** stamps, underlines, photos or page edges, on the corpus's scans and the damaged scans.
- [x] **OpenCV** may be used, as a direct, pinned dependency; it is already installed with PaddleOCR, under Apache-2.0. Numpy alone is also fine.

**Placing text**
- [x] Each of the engine's boxes goes to the cell that holds its centre. Boxes outside every cell stay as rows.
- [x] A cell's lines follow ticket 02's rule, and its text gets the same Thai repair as tables on text pages.
- [x] **Reading order:** the table is placed by its top. A paragraph never runs across it, as on text pages.

**Time**
- [x] An OCR page takes at most about 0.3 s longer. Record the ms per page in Comments. During grilling, the grid took 198 ms per 300-dpi page at the median, and 257 ms at most.

**Web**
- [x] The page "ข้างในทำอะไรกับไฟล์ของคุณ" says today that OCR pages do not yet get headings or tables. Change it to say that ruled tables on OCR pages become tables. The user approves the Thai.

**Corpus**
- [x] **A synthetic document of ruled tables on scans,** with reference text:
  - a payment schedule with wrapped cells;
  - a budget with merged cells;
  - a two-row table of dates;
  - a coarse table with sub-rows.

  Wrapped text fills its cell before it wraps.
- [x] **A sideways ruled table,** turned each way.
- [x] Record the harness's cells column for them in Comments.

**Tests**
- [x] `FakeEngine` returns a ruled table's cell text as boxes where the PDF builder draws it. The page image comes from the real PDF, so its rules are really there.
- [x] Fast tests through the conversion function. These come out as tables:
  - a ruled table on a scan, with wrapped cells and merged cells;
  - a two-row table;
  - a sideways table, both ways.

  These do not:
  - a frame around a paragraph;
  - a ruled box in the edge band;
  - a stamp, an underline or a dark photo.

  And a paragraph before and after the table stays in order.
- [x] Real-OCR tests (`pytest -m ocr`): a ruled scanned table and a sideways ruled table come out as tables with PaddleOCR.
- [x] Measure where the grid breaks on rebuilt pages: 150 dpi, 3° skew, heavier grain. During grilling it held at 150 dpi and 3°, and broke at 100 dpi with heavy grain.
- [x] Checked by breaking the code on purpose. Each part has a test that fails without it:
  - the frame;
  - thick pieces;
  - the single frame;
  - the edge band;
  - the nested grid;
  - placing by centre;
  - the reading order.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, implemented on branch `feat/ocr-tables`**

- **Where:** a new module, `grids.py`, finds the grids in the page image. `ocr._ocr_page` places each box in the cell that holds its centre, and the page's rows carry the tables, as a text page's do. It runs on the image read last, after any sideways turn.
  - **It runs on every OCR page.** The user chose this over gating it to scans: pages with an untrusted text layer and pages drawn as shapes get tables too, and ticket 05 tests them.
- **Finding the grid:**
  - **Ink:** at half the image's resolution, each pixel the darkest of its four so that thin rules stay dark, a pixel darker than grey 160 is ink.
  - **The frame:** the page's slant is that of its horizontal pieces at least two box heights long, thickened 5 px down the page so that a rule 3° askew still runs along a row of pixels; the longest count most. The grey image is turned back by that slant about its centre, as PaddleOCR turns its boxes, before the rules are found. A page with no such piece has no table, and the search stops there.
  - **Rules:** pieces at least a box height long, across or down the page. A piece thicker than max(8 px, 0.15 box height) on average is left out.
  - **Cells:** the spaces the rules close off. Edges within half a box height of each other lie on one grid line, and a cell's spans are counted along the lines.
- **Not tables:**
  - **A grid of one row.** This covers a single frame around text, and a boxed header row with no ruled rows under it. The user chose rows for the header-only case, until ticket 08 decides when it is an incomplete table.
  - A grid wholly in the top or bottom edge band.
  - A grid inside another grid: its text goes to the cell around it, as on text pages.
  - **A grid whose rules close off a space that is no cell:** one that covers the same place as another, as an L where part of a rule is missing, or one too narrow to make a row or column. Its text is read as lines; ticket 08 may make such a grid an incomplete table.
- **Placing text:** a cell's printed lines are measured within their boxes, less 0.3 of a font size at each end. A detector pads its boxes: PaddleOCR's reached 3 to 7 pt past text 16 pt tall in the synthetic scans' cells, over the rule beside it. Without this, ticket 02's "fills its cell" rule took amounts beside stacked items for wrapped lines, and glued short items into one word.
- **Web:** "ข้างในทำอะไรกับไฟล์ของคุณ" now reads "ตารางใน DOCX และตารางที่มีเส้นตารางใน PDF ยังเป็นตาราง รวมทั้งในหน้าที่อ่านด้วย OCR แต่หน้าที่อ่านด้วย OCR ยังไม่แยกหัวข้อ". The user approved the Thai.
- **Test support:**
  - `pdf_builder`: `laid_out_grid` says where a `Grid` draws its cells and text; a `Grid` can sit at its own `x`; a new picture, a dark photo, is a building at night with rows of lit windows.
  - `FakeEngine` reads a `Grid`'s cells as boxes where they are drawn, padded 0.3 font sizes past the text, over the rule beside it, as a detector pads them. An `Askew` page gives the boxes as an engine that straightens them reads them on a scan turned askew and shrunk to fit its page.
  - A mottled dark photo made no table even without the thick-piece filter: its light patches closed off spaces that overlapped, so the grid was dropped. The lit windows make a neat grid, an empty table without the filter, as the grilling saw.
- **Corpus:** `ruled-table-scans` holds the four tables on scans, one a page, with text around each. The sideways ruled table is the price schedule that `sideways-scans` has held, turned each way, since ticket 21. The four tables and their reference text are kept in `generate.py` (`RULED_TABLE_PAGES`) for ticket 05's untrusted and drawn pages.
- **The harness's cells column, PaddleOCR, the same on Windows and in the Linux image:**

  | Page | Cells | CER |
  | --- | --- | --- |
  | `ruled-table-scans` 1, payment schedule | 8/12 | 0.0230 |
  | `ruled-table-scans` 2, budget | 11/13 | 0.0337 |
  | `ruled-table-scans` 3, dates | 5/6 | 0.0075 |
  | `ruled-table-scans` 4, coarse table | 14/16 | 0.0157 |
  | `sideways-scans` 1 | 17/20 | 0.0168 |
  | `sideways-scans` 2 | 19/20 | 0.0042 |

  - In total, 74/87 on OCR pages, where `sideways-scans` had 0/40 before. Text pages hold 46/46, unchanged.
  - **Every table's structure is right:** merged cells, wrapped cells joined, sub-rows split. The cells out of place are misreads: lost tone marks ("งวดที", "เริม"), stray mark boxes in cells ("ญ", "ะ", "e"; ticket 07), a lone "-" the detector did not box, and "3" read for "๓".
  - Without the grid, the four table pages' CER was 0.112; with it, 0.026, as each cell's text now reads in its own place.
- **No false table:** every OCR page of `corpus/synthetic` and `corpus/degraded` was converted with PaddleOCR. Tables came out only on the six pages whose reference holds one.
- **Time,** finding the grid on the page image the engine reads, OpenCV on 4 threads:
  - on this machine: 139 to 149 ms on a page with a table, and 31 to 44 ms on a scan with no rules, where the search stops early;
  - in the Linux image: 73 to 143 ms on a page with a table, and 41 ms at the median over the corpus's OCR pages.
- **Where the grid breaks:** the four table pages rebuilt at each level, scored with PaddleOCR.

  | Scan | Cells | CER |
  | --- | --- | --- |
  | 200 dpi, grain 6, 0.4° | 37/47 | 0.026 |
  | 150 dpi, grain 6, 0.4° | 38/47 | 0.020 |
  | 150 dpi, grain 18, 0.8° | 39/47 | 0.027 |
  | 200 dpi, grain 6, 3° | 39/47 | 0.016 |
  | 150 dpi, grain 18, 3° | 38/47 | 0.029 |
  | 110 dpi, grain 28, 1.2° | 0/47 | 0.176 |
  | 100 dpi, grain 6, 0.4° | 0/47 | 0.235 |
  | 100 dpi, grain 28, 1.2° | 0/47 | 0.195 |
  | 75 dpi, grain 45, 1.8° | 0/47 | 0.268 |

  - It holds at 150 dpi, at 3°, and with heavier grain.
  - At 110 dpi and below, a 0.5-pt rule scans lighter than grey 160. Pieces of it are lost, and cells merge into false spans. Their text then reads in a worse order than with no grid at all: CER 0.18 to 0.24, against 0.10 to 0.11 without one. At 75 dpi no grid is found.
  - Counting a lighter grey as ink, or comparing each pixel with the paper around it, held the grid at 100 dpi. But either lost a table, or its header row, where the header is shaded 30% grey.
  - **The user chose to keep grey 160 and record the limit:** the samples' scans are 300 dpi, and ticket 09 checks them.
- **Tests:**
  - `test_ocr_tables.py`, 16 fast tests through the conversion function. These come out as tables:
    - a table between two paragraphs, which stay in order;
    - a payment schedule with wrapped cells, and a budget with merged cells;
    - the coarse table, with its sub-rows, kept breaks and joined sentence;
    - a table of two rows;
    - a table scanned 3° askew, each way;
    - a sideways table, each way.

    These do not: a frame around a paragraph, a boxed header row alone, a dark photo, a stamp, an underline, a grid inside a cell of another, rules that close off an L, and a ruled box repeated in the top edge band.
  - `test_paddle.py` (`-m ocr`): a payment schedule and a budget on a scan, and the timeline printed sideways each way, come out as tables with at least 60% of their cells in place and a CER under 0.05.
  - `test_corpus.py` (`-m ocr`): at least 80% of the cells of tables on the corpus's OCR pages are in place.
  - `test_web_home.py`: the new sentence.
- **Checked by breaking the code on purpose,** with `test_ocr_tables.py` and `test_ocr_pages.py`:

  | Broken | Tests that fail |
  | --- | --- |
  | the frame: no straightening | 2, the askew tables |
  | thick pieces kept | 1, the dark photo |
  | a one-row grid made a table | 2, the frame and the boxed header |
  | no edge band | 1, the ruled header box |
  | the nested grid kept | 1 |
  | boxes placed by their top-left corner | 9 |
  | boxes placed only when wholly inside a cell | 9 |
  | the table placed at the top of the page | 7 |
  | the table placed at the foot of the page | 9 |
  | no padding taken off a cell's lines | 1, the coarse table |
  | cells that cover the same place kept | 1, the L |

  - A filter that left out spaces smaller than half a box height failed no test, and changed no grid at any level of damage above. It was taken out. (The review below found what it had guarded.)
- **Run:** pytest, mypy, `pytest -m ocr` (21 passed) and the harness, on Windows and in the Linux image with the working copy mounted. In the image, pytest passed 597.

**2026-10-26, after code review (two axes)**

- **Spec found a real fault: a double rule lost the whole table.**
  - The thin space between the two rules, as above a budget's total, has both edges on one grid line. It spans no row, and the whole grid was dropped.
  - The filter taken out above had hidden this, and no test had a double rule.
  - **The fix:** a space too narrow to make a row or column is no cell; the rest of the grid stands. A space that covers another cell's place still drops the grid.
  - **New test:** a double rule above a total reads as one rule. `pdf_builder`'s `Grid` gained `heights`, so a row of empty cells 3 points tall draws the second rule. It failed before the fix, and fails again when a narrow space drops the grid.
- **Spec also found:**
  - **No test read an OCR table back from DOCX.** A new test reads the coarse table on a scan back from the DOCX: its merged cells, sub-rows and a kept break.
  - **Misread words in cells are no longer marked uncertain,** as table text no longer goes through rows. That is ticket 06's work; its Comments now say the branch must not be merged without it.
  - **Rules that close off an L are read as lines with no label,** which ticket 08 may change. Its Comments now list both kinds of grid that make no table.
- **Standards: no written rule broken. Fixed:**
  - `grids.py`'s constants now say where their numbers come from: grey 160 against a shaded header, the thick-piece filter from grilling. The half box height for one grid line is named, `_SAME_LINE`.
  - Boxes are kept by their `GridCell`, not a (grid, cell) number pair, and `_thin`'s side is named `along`.
  - `FakeEngine`'s padding is `DETECTOR_PADDING`, so it no longer shares a name with `pdf_builder.CELL_PADDING`. The box it draws is shaped in one place.
  - The tests use `generate.scanned` and the tables' references from `generate.py`, which now holds `PAYMENT_SCHEDULE_REFERENCE`, `BUDGET_REFERENCE` and `DATES_REFERENCE`. The corpus's reference files came out the same.
- **Standards, left as they are:**
  - a point-in-box test and the nested and edge-band rules that `pdf_text.py` also has: they work on that module's own types;
  - `_table` working out which places no cell covers, which `_grid` has also worked out;
  - a third `Box` alias.
- **Checked by breaking the code again:**
  - cells that cover the same place kept: the L test fails;
  - a narrow space dropping the grid: the double-rule test fails;
  - boxes placed by their corner, or only when wholly inside: 11 tests fail each.
- **Run again:**
  - pytest: 598 passed and 1 skipped on Windows (a Linux-only test), and 599 passed in the Linux image;
  - mypy, `pytest -m ocr` (21 passed) and the harness, with the same cells and CER as above;
  - the grid took 70 to 76 ms on a page with a table in the image this time, and 28 ms at the median over the corpus's OCR pages.
