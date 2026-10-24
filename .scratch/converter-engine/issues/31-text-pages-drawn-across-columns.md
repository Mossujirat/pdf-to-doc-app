# 31: Text pages drawn line by line across their columns are read across them

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** Some PDF writers draw text set in columns line by line across the page: the first line of the left column, then the first line of the right, and so on. A text page drawn that way comes out row by row, with the columns' lines joined, as two-column scans did (ticket 18). This is broken text (wrong reading order), and nothing marks it.

**Blocked by:** none

**Status:** needs-triage

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
