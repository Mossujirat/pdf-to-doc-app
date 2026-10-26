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

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**Pages that are not scans**
- [ ] The grid comes from the page image, as on scans: the rules the PDF draws are in the image too. Nothing is taken from PyMuPDF's table finder on these pages.
- [ ] **Synthetic corpus documents,** with reference text: the four ruled tables of ticket 04, on a page with a wrong ToUnicode map and on a page drawn as shapes. Record the harness's cells column in Comments.
  - During grilling, with the image softened, junk filtered and sub-rows split, these pages reached 38 of 44 cells, with every table's structure right.

**Beside other things on OCR pages**
- [ ] **A text-layer row over a scan that falls inside a grid** goes into its cell, as a box does. A stamped header is still removed as page furniture.
- [ ] **Two columns:** a table's boxes are taken out before the page is cut into columns (ticket 18 of the converter). A two-column page with a table reads its columns in order, with the table whole.
- [ ] **Kept images:**
  - With kept images chosen, pages with an untrusted text layer and pages drawn as shapes still get their tables.
  - Kept scans are unchanged.

**Tests**
- [ ] Fast tests with `FakeEngine`:
  - a ruled table on an untrusted page and on a page drawn as shapes;
  - a note typed over a cell;
  - a table on a two-column page;
  - the same pages with kept images chosen.
- [ ] Real-OCR tests (`pytest -m ocr`): a table on an untrusted page and on a page drawn as shapes comes out as a table with PaddleOCR, every line present.
- [ ] Checked by breaking the code on purpose: the note in its cell, and the table taken out of the column cut.
- [ ] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **The grid already runs on every OCR page,** as the user chose: `ocr._ocr_page` finds it on whatever image it reads, softened or not. Nothing about these pages was tested in ticket 04.
  - A pixel darker than grey 160 is ink. Softened by 1.5 px, a 0.5-pt rule should still peak darker than that, by estimate, but this was not measured.
- **Already in place, untested:** a table's boxes are taken out before the page is cut into columns, as `_in_cells` runs before `_reading_parts`. This ticket needs the test and the check by breaking it.
- **Not yet:** a text-layer row over a scan stays a row even when it lies inside a grid (`_LayerRow`).
- **To reuse:** `RULED_TABLE_PAGES` in `generate.py` holds the four tables' pages and reference text; `FakeEngine` reads a `Grid` where `pdf_builder` draws it, on a `Drawn` page too.
