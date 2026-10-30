# 05: Tables on untrusted and drawn pages

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** OCR pages that are not scans get their ruled tables too:
- pages whose text layer cannot be trusted, such as a contract's budget pages, where "การ" reads "กำร";
- pages whose text is drawn as shapes, such as an agreement printed that way.

Tables also keep working beside the other things OCR pages hold:
- a note typed over a scanned table lands in its cell;
- a table on a page set in two columns stays whole;
- with kept images chosen, these pages still get their tables.

**Blocked by:** 04, converter-engine ticket 33 (lines lost on OCR pages that are not scans)

**Status:** done

**Branch:** `feat/ocr-tables`

**Pages that are not scans**
- [x] The grid comes from the page image, as on scans: the rules the PDF draws are in the image too. Nothing is taken from PyMuPDF's table finder on these pages.
- [x] **Synthetic corpus documents,** with reference text: the four ruled tables of ticket 04, on a page with a wrong ToUnicode map and on a page drawn as shapes. Record the harness's cells column in Comments.
  - During grilling, with the image softened, junk filtered and sub-rows split, these pages reached 38 of 44 cells, with every table's structure right.

**Beside other things on OCR pages**
- [x] **A text-layer row over a scan that falls inside a grid** goes into its cell, as a box does. A stamped header is still removed as page furniture.
- [x] **Two columns:** a table's boxes are taken out before the page is cut into columns (ticket 18 of the converter). A two-column page with a table reads its columns in order, with the table whole.
- [x] **Kept images:**
  - With kept images chosen, pages with an untrusted text layer and pages drawn as shapes still get their tables.
  - Kept scans are unchanged.

**Tests**
- [x] Fast tests with `FakeEngine`:
  - a ruled table on an untrusted page and on a page drawn as shapes;
  - a note typed over a cell;
  - a table on a two-column page;
  - the same pages with kept images chosen.
- [x] Real-OCR tests (`pytest -m ocr`): a table on an untrusted page and on a page drawn as shapes comes out as a table with PaddleOCR, every line present.
- [x] Checked by breaking the code on purpose: the note in its cell, and the table taken out of the column cut.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **The grid already runs on every OCR page,** as the user chose: `ocr._ocr_page` finds it on whatever image it reads, softened or not. Nothing about these pages was tested in ticket 04.
  - A pixel darker than grey 160 is ink. Softened by 1.5 px, a 0.5-pt rule should still peak darker than that, by estimate, but this was not measured.
- **Already in place, untested:** a table's boxes are taken out before the page is cut into columns, as `_in_cells` runs before `_reading_parts`. This ticket needs the test and the check by breaking it.
- **Not yet:** a text-layer row over a scan stays a row even when it lies inside a grid (`_LayerRow`).
- **To reuse:** `RULED_TABLE_PAGES` in `generate.py` holds the four tables' pages and reference text; `FakeEngine` reads a `Grid` where `pdf_builder` draws it, on a `Drawn` page too.

**2026-10-28, implemented on branch `feat/ocr-tables`**

- **Pages that are not scans needed no new code.** The grid is found on the softened image as on a scan: a softened 0.5-pt rule stays darker than grey 160. Nothing comes from PyMuPDF's table finder on these pages: `reading.py` already drops an untrusted page's text-layer tables, and a page drawn as shapes has none.
- **A note typed over a scanned table lands in its cell.** The text-layer rows that `_ocr_page` keeps go to `_in_cells` with the engine's boxes, so a row whose centre lies in a cell is a line of that cell. A row outside every cell stays a row, so a stamped header over a scan is still removed as page furniture.
  - The page's font size is still told by the engine's boxes alone, as for rows: a cell's line made of text-layer rows only is left out of it.
  - A cell's lines are still all measured less the detector's padding, text-layer rows too. Measuring a text-layer row without it changed the cell's text in none of six notes of two lines tried, each with a first line filling its cell to a different degree, so it was not kept.
- **Two columns, a fault found and fixed:** a table in the left column split a paragraph of the right column where the table starts. A paragraph never runs across a table, and layout judged that by height alone.
  - **The fix:** `PlacedTable` now holds its left and right edges, and a paragraph stops at a table only when the table lies under it. Text pages build their tables with the edges too; their tests and the corpus are unchanged.
- **Taking a table out before the column cut** was in place from ticket 04. Its test needed a table right under two columns whose cells reach across their gutter. Neither a table a few lines under the columns, nor a table inside one column, failed when the table's boxes were left in the cut.
- **Kept images:** pages with an untrusted text layer and pages drawn as shapes are still read with kept images, and get their tables. A scan with a table, kept, is its placeholder alone and is not read.
- **Corpus:** `ruled-tables-wrong-unicode-map` and `ruled-tables-drawn-as-shapes` hold ticket 04's four table pages; every page is an OCR page.
- **The harness's cells column, PaddleOCR:**

  | Page | Wrong ToUnicode map | Drawn as shapes |
  | --- | --- | --- |
  | 1, payment schedule | 6/12 | 8/12 |
  | 2, budget | 12/13 | 12/13 |
  | 3, dates | 5/6 | 5/6 |
  | 4, coarse table | 15/16 | 15/16 |
  | In total | 38/47 | 40/47 |

  - Every table's structure is right, and no line is missing on any page.
  - The cells out of place are misreads: lost tone marks ("งวดที", "เกียวข้อง"), Thai digits read as "ด" or "3", and stray mark boxes ("9 ญ", "2 2"; ticket 07).
  - OCR pages in total: 152/181. Every page the harness scored before scored the same.
- **Tests:**
  - `test_ocr_tables.py`:
    - a payment schedule and a budget on a page with a wrong ToUnicode map and on a page drawn as shapes, with images read and kept;
    - a scanned table kept as an image is not read;
    - a note typed over a scanned table, in an empty cell, lands there;
    - a table right under two columns, across their gutter;
    - a table in the left column, beside the right column's paragraph.
  - `test_paddle.py` (`-m ocr`): the payment schedule on each kind of page is a table of four rows of three cells, with no line missing and a CER under 0.05. Its shape is checked rather than its cells in place: on so small a table, a few misreads leave half its cells out of place, 6 of 12 on the wrong-map page.
- **Checked by breaking the code on purpose,** with `test_ocr_tables.py` and `test_ocr_pages.py`:

  | Broken | Tests that fail |
  | --- | --- |
  | text-layer rows kept out of cells | 1, the note |
  | the table taken out of the page after the column cut | 1, the table right under two columns |
  | a table beside a paragraph splitting it | 1, the table in a column |
- **Run:**
  - pytest: 606 passed and 1 skipped on Windows (a Linux-only test), and 607 passed in the Linux image;
  - mypy, and `pytest -m ocr` (23 passed in the image);
  - the harness, the same on Windows and in the image.

**2026-10-28, after code review (two axes)**

- **Spec found a real fault: a table in the right column was read in the left one.**
  - Each table went before the first paragraph that starts below its top, in whichever column. So with the left column's second paragraph starting below the table's top, the table came out between the left column's paragraphs.
  - The edges added above only stopped the paragraph split; my test had its table in the left column, where both rules agree.
  - **The fix:** a table goes before the first paragraph that starts below its top and lies under it across the page, which is in its own column; or else after the last such paragraph above it. A table under no text is placed by its top, as before. Images are placed as before.
  - **New test:** a table in the right column, beside the left column's second paragraph. It failed before the fix, and fails again when tables are placed by their top alone.
- **Spec also noted:** text pages build their tables with the edges too, so the paragraph rule and the reading order apply there. Text pages are read in rows, not columns, so a paragraph lies across a table it runs past; their tests and the corpus are unchanged.
- **Standards: no written rule broken. Fixed:**
  - `KAR_AS_KAM`, the wrong ToUnicode map, is named once in `generate.py` and used by the corpus and the tests, in place of a map written out in each;
  - `_in_cells` now says it places text-layer rows too, and that its evidence about rules is the engine's boxes';
  - the tables' overlap across the page is one function, `layout._across`, for the paragraph rule and the reading order.
- **Standards, left:**
  - `test_ocr_tables.py` imports the two-column fixtures from `test_ocr_pages.py`, the first test module to import from another; moving them would touch ticket 18's tests for no gain;
  - the `isinstance(box, _LayerRow)` checks in `_ocr_page`, which follow its existing split of the engine's boxes and the text layer's rows.
- **Run again:** pytest (607 passed and 1 skipped on Windows, 608 passed in the Linux image), mypy, `pytest -m ocr` (23 passed in the image) and the harness, with the same cells: 152/181 on OCR pages, 46/46 on text pages.
