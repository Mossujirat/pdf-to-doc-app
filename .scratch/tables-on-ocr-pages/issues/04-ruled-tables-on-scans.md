# 04: Ruled tables on scans

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** A ruled table on a scan comes out as a table in both outputs, sideways pages once turned upright included. Each cell holds the text printed in it, merged cells are kept, and a wrapped cell keeps both its lines. A scanned budget, payment schedule or price schedule can then be read, and pasted into an AI chat, as a table. Today it comes out as paragraphs with its cells mixed.

**Blocked by:** 01, 02

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**Finding the grid**
- [ ] **Where:** where OCR pages are read, through the `OcrEngine` interface, as tickets 18 and 21 of the converter work. It comes after any sideways turn, and uses only the page image and the engine's boxes.
- [ ] **The rules:** long horizontal and vertical rules are found in the page image. Cells are built from them, with row and column spans for merged cells.
- [ ] **The frame:** the grid lies in the same frame as the engine's boxes, which are straightened by the page's slant.
- [ ] **Not rules:** pieces thicker than about max(8 px, 0.15 of a box's height). A dark photo made an empty table without this.
- [ ] **Not tables:**
  - a single ruled frame around text;
  - a grid wholly inside the page's edge bands, which is read as rows, so ruled headers and footers stay page furniture;
  - a grid inside another grid.
- [ ] **No table from** stamps, underlines, photos or page edges, on the corpus's scans and the damaged scans.
- [ ] **OpenCV** may be used, as a direct, pinned dependency; it is already installed with PaddleOCR, under Apache-2.0. Numpy alone is also fine.

**Placing text**
- [ ] Each of the engine's boxes goes to the cell that holds its centre. Boxes outside every cell stay as rows.
- [ ] A cell's lines follow ticket 02's rule, and its text gets the same Thai repair as tables on text pages.
- [ ] **Reading order:** the table is placed by its top. A paragraph never runs across it, as on text pages.

**Time**
- [ ] An OCR page takes at most about 0.3 s longer. Record the ms per page in Comments. During grilling, the grid took 198 ms per 300-dpi page at the median, and 257 ms at most.

**Web**
- [ ] The page "ข้างในทำอะไรกับไฟล์ของคุณ" says today that OCR pages do not yet get headings or tables. Change it to say that ruled tables on OCR pages become tables. The user approves the Thai.

**Corpus**
- [ ] **A synthetic document of ruled tables on scans,** with reference text:
  - a payment schedule with wrapped cells;
  - a budget with merged cells;
  - a two-row table of dates;
  - a coarse table with sub-rows.

  Wrapped text fills its cell before it wraps.
- [ ] **A sideways ruled table,** turned each way.
- [ ] Record the harness's cells column for them in Comments.

**Tests**
- [ ] `FakeEngine` returns a ruled table's cell text as boxes where the PDF builder draws it. The page image comes from the real PDF, so its rules are really there.
- [ ] Fast tests through the conversion function. These come out as tables:
  - a ruled table on a scan, with wrapped cells and merged cells;
  - a two-row table;
  - a sideways table, both ways.

  These do not:
  - a frame around a paragraph;
  - a ruled box in the edge band;
  - a stamp, an underline or a dark photo.

  And a paragraph before and after the table stays in order.
- [ ] Real-OCR tests (`pytest -m ocr`): a ruled scanned table and a sideways ruled table come out as tables with PaddleOCR.
- [ ] Measure where the grid breaks on rebuilt pages: 150 dpi, 3° skew, heavier grain. During grilling it held at 150 dpi and 3°, and broke at 100 dpi with heavy grain.
- [ ] Checked by breaking the code on purpose. Each part has a test that fails without it:
  - the frame;
  - thick pieces;
  - the single frame;
  - the edge band;
  - the nested grid;
  - placing by centre;
  - the reading order.
- [ ] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments
