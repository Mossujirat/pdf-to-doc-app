# 14: Scanned tables

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Tables on scanned pages, such as a budget table, come out as tables where the CPU pipeline can manage it. Where it cannot, the reader is told that the table structure may be incomplete, instead of getting unexplained loose lines. This ticket evaluates PaddleOCR's table model (PP-StructureV3) on CPU and adopts it if it is good enough.

**Blocked by:** 08, 09, 33

**Status:** done

**Branch:** `feat/ocr`

**Evaluation**
- [x] Run PP-StructureV3 on scanned table pages from the synthetic corpus and, locally, from the confidential reference pages. Measure:
  - cell-level accuracy (correct cell text in the correct cell)
  - Thai integrity inside cells
  - seconds per page on CPU
- [x] Record the numbers in the ticket's comments. Measured on synthetic pages only; the real pages wait for /implement (see the comment of 2026-10-25).

**If PP-StructureV3 is good enough**
- [ ] Scanned tables become document-model tables with spans, rendered like text-page tables.

**If it is not**
- [ ] A detected table region is output as text lines, preceded by an "incomplete table" placeholder.

**Either way**
- [ ] The summary notes how many scanned tables were output each way.
- [ ] Default-mode time for a 110-page mixed document stays within the target from ticket 08.

**Tests**
- [ ] Corpus fixtures with simulated scanned tables cover the chosen path.

## Comments

**2026-10-20, handed over from ticket 10 (text-layer validation)**

- The contract's budget tables on pages 69-72 now become OCR pages, because their font's ToUnicode map turns "การ" into "กำร". Until this ticket, they come out as lines of text, without table structure. The user accepted that.
- Those pages still draw their table rules as vector lines, and PyMuPDF's table finder still finds the grid (ticket 04).

**2026-10-21, from ticket 11 (uncertain text)**

- Only paragraphs and list items carry uncertain text so far: the document model's `uncertain` stretches, which renderers and the summary read through one accessor.
- Table cells read with OCR will need them too, so that a misread in a scanned table is marked like any other. So when an OCR page carries a ruled grid in the PDF, the cells could come from that grid and the text from OCR, with each box placed in the cell that holds its centre. Ticket 04 notes that this grid is coarse on these pages.

**2026-10-23, from checking more samples while grilling kept images**

- **A third kind of page with tables.** A five-page agreement among the local samples was printed to PDF with its text drawn as shapes, so every page is an OCR page, although none is a scan. Its tables are ruled with drawn lines.
  - In a payment schedule, the amount cell's text landed in the middle of the description cell's sentence, because OCR joins boxes into lines across the whole row.
  - Two-row tables of dates came out as one line each.
  - The ruled grid is there to use, as the comment above suggests.
- **Scanned tables on a 34-page scanned supplement.** Seven pages had their tables flattened, with cells mixed or rows shifted. Two of those tables are also printed sideways (ticket 21).
- **The 110-page contract,** checked page by page against its images:
  - About 25 scanned pages had their tables flattened or their cells interleaved: proposal forms, researcher profiles, and tables that share out intellectual property.
  - The shaded bars of a schedule chart were lost, so the schedule says nothing.
  - On pages 69–72, OCR reads better than the broken text layer did. Its numbers match apart from a few slips, but the tables come out one row per line or run on.
  - Ticks in table cells are lost (ticket 26).

**2026-10-24, from grilling ticket 21 (sideways pages)**

- **More tables to come.** Once ticket 21 turns sideways pages upright, their tables reach OCR the right way up. Most of the twelve sideways pages in the local samples hold tables: a price schedule, a project timeline, a work plan, a budget and a table of delegated powers. As the user decided, their structure is left to this ticket.
- **Why rows run together:** on a synthetic price schedule turned upright and read again, every row came out in order, but they joined into one paragraph. On a text page, a row set out in columns stays a line of its own (`in_columns`). OCR rows never get that flag.
- **Sideways column headers** inside upright tables are ticket 29. Placing their text in the header row needs this ticket.

**2026-10-25, grilled with the user: measurements and decisions**

The decisions below replace the sections "If PP-StructureV3 is good enough" and "If it is not" above.

**The test pages (synthetic, built for this grilling)**
- **Four ruled tables:**
  - a payment schedule with wrapped cells;
  - a budget with merged cells;
  - a two-row table of dates;
  - a coarse table whose printed sub-rows share one ruled cell. Its truth gives each sub-row a row of its own.
- **Each table was built three ways:**
  - **untrusted:** a page whose text layer is untrusted (a wrong ToUnicode map), with rules drawn as vectors;
  - **drawn:** a page whose text and rules are drawn as shapes;
  - **scanned:** a 200-dpi scan, 0.4° askew, with grain.
- **Four more pages:**
  - **unruled:** a scan with only the header row boxed, and two scans with no rules;
  - **sideways:** the price schedule printed sideways, once each way.
- **In all,** 17 pages and 201 cells.
- **Today,** no cell lands in a table: OCR rows run together into paragraphs.

**Cells right, by method (measured, 4 CPU threads, Windows)**

| Method | untrusted | drawn | scanned | unruled | sideways | Peak memory | s per page | Docker image grows by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| today | 0/44 | 0/44 | 0/44 | 0/29 | 0/40 | 1.35 GiB | 2.3 | – |
| rules found in the page image, OCR boxes placed by centre | 28/44 | 27/44 | 27/44 | 2/29 | 36/40 | no change | +0.2 | nothing |
| PP-StructureV3 (formula, seal and chart off; our OCR models) | 28/44 | 27/44 | 26/44 | 12/29 | 36/40 | 3.06 GiB | 19 | about 1.0 GB, and 25 packages |
| TableRecognitionPipelineV2 | 27/44 | 26/44 | 23/44 | 0/29 | 36/40 | 3.22 GiB | 17 | about 1.2 GB |
| our boxes + PP-DocLayout_plus-L + SLANet_plus | 28/44 | 27/44 | 27/44 | 12/29 | 36/40 | 2.13 GiB | 5.5 | about 130 MB |
| our boxes + PP-DocLayout-S + SLANet_plus | 0/44 | 0/44 | 13/44 | 0/29 | 36/40 | 1.6 GiB | 2.4 | about 13 MB |

- **The cells every method gets wrong are OCR misreads, not placement:**
  - lost tone marks: เริม, ปีที, ครัง;
  - a lone "๑" or "-" the detector misses;
  - upper marks boxed apart from their line ("ญ ญ"), which land in the cell.
- **With the image softened (ticket 33), the junk boxes filtered and sub-rows split,** the untrusted and drawn pages reached 38/44, with every table's structure right.
  - That run took its grid from the PDF's vectors. The image grid finds the same grid on those pages, so the same result is expected from it. That is inferred, not measured.
- **Thai inside cells:**
  - No method left orphan marks or sara am stored as two characters.
  - PaddleX joins a wrapped cell's lines with a space, which puts two spaces inside words on each ruled page. Our `join_lines` puts none.
- **PP-StructureV3 on unruled tables is unreliable:**
  - The budget page came out 6×2, with both intro lines inside a cell and the closing paragraph dropped from the page.
  - The dates page got no table.
  - Only the page with a boxed header came out right.
- **150 pages** at PP-StructureV3's 19 s each would take about 48 minutes, over the sandbox's 30.
- **The image grid:**
  - It made no false grid on the corpus's scans: stamped, two-column, rotated and damaged ones.
  - A dark photo did make one. Rejecting rule pieces thicker than max(8 px, 0.15 box height) removed it.
  - It held at 150 dpi and at 3° of skew. It broke at 100 dpi with heavy grain, where lost rule pieces gave false spans.
  - No OCR box crossed a rule through its middle. Boxes reach over rules only by the detector's padding, and placing each by its centre is right.
  - It took 198 ms per 300-dpi page at the median, and 257 ms at most.
- **One line per OCR row, by a gap wider than two font sizes between the detector's boxes** (`in_columns`, as text pages have it):
  - Every table row stayed a line of its own.
  - No body-text line was flagged: on 381 OCR rows, every flagged row was a table row, a label–value pair, a tab-stop list, a signature line or junk.
  - The two-column cover sheet's CER fell from 0.0194 to 0.0039.
  - On one sideways page, a "1" misread as "-" now shows, marked uncertain. Before, it was hidden as a list bullet.
- **Sub-rows:**
  - The rule: split a ruled row when two or more of its cells hold the same number of lines, more than one, and those lines line up.
  - It gave 13/15 cells on the coarse table, with its structure right.
  - It failed once, where a junk mark box gave a cell an extra line.
  - It did not trigger on the payment table's wrapped cells.
- **The line lost above each table on untrusted and drawn pages** is ticket 33. The rule is not the cause.

**Decided with the user**
1. **When the converter cannot place a table's text in its cells with certainty,** the output gives the table row by row, each printed line on its own, after the label [ตารางอาจไม่สมบูรณ์]. A table with clear rules comes out as a table, with no label.
2. **The summary tells about tables apart from placeholders,** and counts them both ways: tables that came out as tables, and incomplete tables with their pages.
   - **Incomplete table** is now a term in `GLOSSARY.md`. Its text is transcribed, so it is not a placeholder.
   - The exact Thai is approved at /implement.
   - The web app's per-page notes follow the same split.
3. **The lost line is ticket 33,** done before this ticket.
4. **A cell holding several printed lines:**
   - Lines that line up across two or more cells become sub-rows.
   - Otherwise, a line that fills its cell carries on into the next line, joined by the Thai line rules.
   - A short line ends its item, and the line break is kept inside the cell.
5. **Rule 4 applies to every table, text pages included.** The `tables` corpus fixture breaks a cell's text mid-word ("ความก้าว|หน้า") in a cell that is not full. It is rebuilt to wrap the way Word wraps.
6. **Junk boxes are dropped on every OCR page.** A junk box holds upper marks that the detector boxed apart from the line below, whose reading already holds them.
   - A box is dropped only where the line below holds upper marks at that place, and never across a rule.
   - The corpus is checked so that no real text goes; a lone "-" in a cell was lost to a looser filter.
7. **The real samples are checked at /implement only,** on the terms of tickets 18 and 21:
   - converted on this machine, with no sub-agent;
   - counts only in tickets;
   - the outputs deleted after.
8. **PP-StructureV3, and PaddleOCR's other table models, are not used.**
   - Its full pipeline peaks over the sandbox's memory and is about eight times slower.
   - On ruled tables it is no better, and on unruled ones it is unreliable.
   - Accurate mode (ticket 15), which reads tables as HTML, is the way to get the structure of unruled tables.
9. **A table with no rules at all comes out one line per row, with no label,** as on text pages. Labels and their values look the same, so the label would land on forms too. The label appears where a table is seen but its rules are incomplete, such as one with only its header boxed.
10. **One method for every OCR page:** the rules are found in the page image. It works where OCR pages are read, through the `OcrEngine` interface, as tickets 18 and 21 do, so that any engine that gives boxes, and `FakeEngine`, get it.
   - It covers scans, sideways pages once turned, untrusted pages and pages drawn as shapes.
   - Taking the PDF's vectors instead worked on untrusted pages. On drawn pages it needed two workarounds inside PyMuPDF's table finder: it throws away a table with no text, and glyph paths cut its grid.

**Decided by the implementer's side, and told to the user**
- **Uncertain text in cells:**
  - Cells are marked like paragraphs: `<mark>` in Markdown, yellow in DOCX, and counted in the summary.
  - The document model's single accessor for uncertain text covers table cells.
- **One line per row on every OCR page,** by the gap rule measured above.
- **Text-layer rows over a scan that fall inside a table** go into its cells, as the engine's boxes do.
- **Time:** an OCR page takes at most about 0.3 s longer, so ticket 08's target for 110 pages holds.
- **The harness** reports how many cells land in the right place on pages whose reference holds tables, for this ticket's checks and for ticket 17.
- **The web page's "ข้างในทำอะไรกับไฟล์ของคุณ"** says OCR pages do not yet get tables (`web/pages.py`). It changes in this ticket, as the spec's rule asks.
- **Unchanged:**
  - Kept pages: a kept scan is not read, so it gets no table.
  - Accurate mode keeps Typhoon's own tables (ticket 15).

**Left out**
- sideways column headers (ticket 29);
- ticks in cells (ticket 26);
- the structure of unruled tables in default mode.

**2026-10-30, done**

- **Built** as the feature `.scratch/tables-on-ocr-pages/`, tickets 01–09. Merged into `main` in PR #17 (`6e85aa5`), with ticket 33.
- **The final check on the samples is in that feature's ticket 09:** 60 tables and 6 incomplete tables over the three samples, counts only.
- **Left over:** ticket 10 of that feature (row labels beside a ruled table), as well as what this ticket left out above.
