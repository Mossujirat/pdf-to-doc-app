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
- Those pages still draw their table rules as vector lines, and PyMuPDF's table finder still finds the grid (ticket 04). So when an OCR page carries a ruled grid in the PDF, the cells could come from that grid and the text from OCR, with each box placed in the cell that holds its centre. Ticket 04 notes that this grid is coarse on these pages.
