# 14: Scanned tables

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Tables on scanned pages, such as a budget table, come out as tables where the CPU pipeline can manage it. Where it cannot, the reader is told that the table structure may be incomplete, instead of getting unexplained loose lines. This ticket evaluates PaddleOCR's table model (PP-StructureV3) on CPU and adopts it if it is good enough.

**Blocked by:** 08, 09

**Status:** ready-for-agent

**Branch:** `feat/ocr`

**Evaluation**
- [ ] Run PP-StructureV3 on scanned table pages from the synthetic corpus and, locally, from the confidential reference pages. Measure:
  - cell-level accuracy (correct cell text in the correct cell)
  - Thai integrity inside cells
  - seconds per page on CPU
- [ ] Record the numbers in the ticket's comments.

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
