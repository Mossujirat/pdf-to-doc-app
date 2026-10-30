# 31: Text pages drawn line by line across their columns are read across them

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** Some PDF writers draw text set in columns line by line across the page: the first line of the left column, then the first line of the right, and so on. A text page drawn that way comes out row by row, with the columns' lines joined, as two-column scans did (ticket 18). This is broken text (wrong reading order), and nothing marks it.

**Blocked by:** none

**Status:** done

**Seen on:** synthetic pages only, built while grilling ticket 18 on 2026-10-24. None of the local samples has shown it: every case of text read across columns there was on OCR pages.

**What is known so far**
- **Drawn one column after the other, as Word writes, text pages read right today:**

  | Page | CER |
  | --- | --- |
  | Thai two-column page | 0.001 |
  | letter with an address panel | 0 |
  | three signature blocks side by side | 0 |

  The one edit on the two-column page is a paragraph that runs across the columns and splits in two, as ticket 18 decided for OCR pages.
- **Drawn line by line across the columns:**

  | Page | CER | What happens |
  | --- | --- | --- |
  | Thai two-column page | 0.63 | MuPDF puts both columns' lines in one block, alternating. `_join_on_baselines` joins the two lines on each baseline. |
  | letter with an address panel | 0.76 | The panel's registry number lands inside a line of the letter. |
  | three signature blocks | 0.34 | The blocks come out row by row: three signing lines, then three names, then three titles. |
- **PyMuPDF's own ordering does not fix it:**
  - `sort=True` sorts only whole blocks. It changes nothing on pages drawn across, and breaks the pages drawn by column: CER 0.39, 0.76 and 0.34.
  - The `TEXT_SEGMENT` flag reads every page drawn across right, and leaves the pages drawn by column right. It costs about 1 ms a page.
    - It also reads an unruled column-aligned list by column (CER 0.15), and the tab-stop rows of the corpus's `page-structure` page 2 (CER 0.25). Text pages are gated at zero broken text.
    - With it, `rawdict` nests text in blocks of type 2, which `text_rows` skips today.
- **Ticket 18's method** finds columns from OCR boxes and splits only where both sides are body text. It was not tried on text-layer rows.

**To decide at triage**
- Whether to wait until a real source file shows the fault.
- Whether to apply ticket 18's method to text-layer rows, with its guards, or to use `TEXT_SEGMENT` with a guard of its own.
- How to keep tab-stop rows and unruled lists reading row by row, under the zero-broken-text gate.

## Comments

**2026-10-30, triage**

- **In the next deploy:** the user chose this ticket among the 6 to be done before it. See `.scratch/next-deploy.md`.
- **Next:** `/grill-with-docs`, then `/implement`.

**2026-10-30, grilling**

- **Measured on new synthetic text pages** (14 pt Thai, gutter 25 pt unless said):

  | Page drawn across | Today | Ticket 18's finder on text rows |
  | --- | --- | --- |
  | Thai two-column, gutters 12–25 pt | 0.76 | 0 |
  | Thai, a paragraph running on into the right column | 0.46 | 0.002 (the split at the column top, as today on pages drawn by column) |
  | English two-column clauses | 0.62 | 0 |
  | letter with a panel, signature blocks, bank details beside signatories | 0.37–0.56 | unchanged: short lines fail the body-text guard |
  | 7 label–value layouts, cover sheet, unruled price list and dates | 0 | 0 |

  No page of `corpus/synthetic` changed, `page-structure` page 2's tab-stop rows included.
- **One real sample** has a text page that the finder splits: the signing page of a research contract, with two signature blocks drawn column after column. Reordering it would move rows the PDF drew in reading order.
- **Decided**
  - **Method:** ticket 18's column finder, with all its guards, on text-layer rows, measured in the page's median row height. Not `TEXT_SEGMENT`, which breaks tab-stop rows (0.25) and unruled lists (0.15).
  - **Only where the drawing order goes across the columns:** where the rows in drawing order go back to a column left of one already drawn. A page drawn column after column keeps its drawing order, as it reads right today.
  - **A new column starts a new paragraph or list item,** as on OCR pages (ticket 18).
  - **Side panels, signature blocks and bank details drawn across on text pages** go to ticket 32, so that one cue serves both kinds of page.
  - **Tests:** through `convert` in `tests/test_text_pages.py`, and a Thai two-column page drawn across in `corpus/synthetic`.
- **Known limit, left as it is:** at gutters of about 11 pt or less under 14 pt type, MuPDF joins the widest left line to its right neighbour in one line, which hides the gutter, so a page drawn across still reads across. Below about 9 pt the finder finds no gutter whichever way the page is drawn. No sample shows it.

**2026-10-30, implemented**

- **Where:** the column finder moved from `ocr.py` into `columns.py`, unchanged. Text pages go through `columns.in_reading_order`, from `reading.read_pdf`.
- **Tests:**
  - in `tests/test_text_pages.py`, two columns in both drawing orders, Thai and English, and a numbered clause running into the right column;
  - the label–value and short-line layouts, drawn across, still read row by row;
  - `tests/test_columns.py` pins the guard. A page like the real signing page, drawn column after column with its contract number drawn first, keeps its drawing order. Through `convert`, no synthetic page showed the difference.
  - corpus: `two-column-drawn-across`, CER 0.
- **On the local samples:** all 149 pages come out of `in_reading_order` unchanged.
- **Known limits, from the review:**
  - On a page drawn by column, a single row of a right-hand column drawn before the end of the left one is enough to count as drawn across. The whole page is then taken by position, each part starting a new paragraph.
  - On a page drawn by column, full-width text drawn out of place, such as a paragraph under the columns drawn before them, keeps its drawing order, as before this ticket.
