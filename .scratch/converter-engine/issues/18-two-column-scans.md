# 18: Two-column scans are read across their columns

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On an OCR page set in two columns, each output line joins a line of the left column to the line beside it in the right column. Sentences from the two columns interleave, and the text cannot be read. This is broken text (wrong reading order). None of it is marked uncertain, because every word in it is a real word, so the summary does not warn about it either.

**Blocked by:** none

**Status:** done

**Seen on:** a scanned contract supplement among the local samples in `docs/example_pdf/`. It was converted on 2026-10-22 and 2026-10-23 with the user's permission, while grilling the kept-images feature, and every page was checked against its image. The same fault hits any text set side by side:
- six two-column pages of standard terms and conditions;
- a letter whose right edge holds a narrow panel of the sender's offices, registry and bank details, joined line by line with the letter's body;
- a signing page with three signature blocks side by side.

The single-column pages of the same file read in order.

A five-page agreement printed to PDF shows the same fault. Its text is drawn as shapes, so its pages are OCR pages, though none is a scan:
- Its bank details sit beside its list of signatories, and the account number landed in the signatory's text, away from its label.
- On its signing page, the two signers' titles came out joined line by line, the right-hand signer's first. A reader could match a name to the wrong title.

A 110-page Thai contract with scans pasted into Word pages shows it again, in these layouts:
- diagrams whose boxes sit in columns;
- captions of two figures side by side;
- signature blocks beside a company stamp;
- a notice box beside a QR code;
- handwritten initials in a margin, joined into the item beside them.

**Where to look:** `ocr.read_page` reads each OCR page: `_sideways_turn` turns a sideways page upright first (ticket 21), then `_ocr_page` builds the rows. Its `_printed_lines` groups the engine's boxes into lines by their vertical centres across the whole page width, and `_ocr_page` then sorts every row by its top. In `layout.py`, `_continues` decides whether a row carries on a paragraph or list item.

**Measured on synthetic pages (2026-10-24)**
- **Pages:** scans built as the corpus builds them (200 dpi, 0.4° skew, grain), read with PaddleOCR at 300 dpi on 4 threads. A page took 0.7–5.1 s to read.
  - **Set side by side:** a Thai two-column page under a full-width title; an English two-column terms page in 9.5 pt; a letter with a narrow panel in 8–9 pt at its right edge, and the same with the panel on the left; two and three signature blocks side by side; bank details beside a list of signatories; two captions side by side. The two-column pages were also built with gutters of 8, 12, 16, 24 and 36 pt.
  - **Read row by row:** a single-column page, the corpus's scanned page and an official letter; the price schedule upright and sideways both ways; an unruled table of amounts; a form with two fields on each line; label–value lists (aligned at a tab stop, with colons, long labels with short values, and a block set off by blank lines inside body text); a term–definition list; an unruled table without numbers; a timetable; a contents page.
- **Why it goes wrong:** at gutters of 24 pt or more, the detector never draws a box across the two columns. The whole fault comes from `_printed_lines` and the sort by top. CER today: 0.70–0.74 on two-column pages, 0.65 with a side panel, 0.34–0.41 with signature blocks side by side.
- **The detector at narrow gutters:**
  - Thai 14 pt, 15 pairs of lines side by side: boxes ran across the gutter 3, 1, 1, 0 and 0 times at 8, 12, 16, 24 and 36 pt.
  - English 9.5 pt, 26 pairs: 6 times at 8 pt, never from 12 pt. At 12 pt the boxes still reach 3.4 pt into the gutter, so they leave no clean gap.
  - A box reaches about 2.5 pt past its text on each side, and is about 1.27 times the font size tall.
- **Finding columns from the boxes (recursive XY-cut):** cut the page where a horizontal band holds no box (0.8 of the median box height worked best), then where a vertical gutter crosses no box (0.3–0.5 of the median box height), and recurse. Bands that share a gutter must be merged, or a two-column page's section gaps line up and get cut. It adds 0.0–2.1 ms a page.
  - **With guards against narrow and numeric columns** (every part at least 15% of the region's width; no cut beside a column whose lines are mostly numbers), every side-by-side page read right, at CER 0.001–0.11. The price schedule, the unruled table of amounts and the sideways pages read as today.
  - **But it cut 5 of the 9 label–value layouts, and separated labels from their values.** Pairs kept:

    | Layout | Today | Cut |
    | --- | --- | --- |
    | label–value list at a tab stop | 8/8 | 1/8 |
    | term–definition list | 6/6 | 0/6 |
    | unruled table without numbers | 6/6 rows | 0/6 |
    | label–value block set off by blank lines | 4/4 | 1/4 |
    | long labels, short values | 5/5 | 0/5 |

    The form with two fields on each line went from CER 0.007 to 0.58. A label–value list with colons and a narrow gap, the timetable and the contents page were not cut.
  - **No guard on box positions separates those layouts from columns.** Nine were tried: width ratio, label length, how far the left lines fill their part, ragged against aligned edges, lines pairing on baselines, extra lines on the right, a varying gap, and colons. The best, "no cut when either side's median line is under 15 characters", passed this set by 3 characters: 13.5 at most on the row layouts, 16.5 on signature blocks.
  - **Median characters per line on the shorter side:**

    | Layout | Median |
    | --- | --- |
    | two-column body text (lines fill 0.86–0.99 of their column) | 27–40 |
    | bank details beside signatories | 18.5 |
    | form with two fields on each line | 18 |
    | side panel | 17 |
    | signature blocks | 16.5–17 |
    | label–value layouts | 13.5 at most |
- **Narrow gutters:** cutting on boxes fails below about one text height of gutter: Thai at 16 pt, English at 12 pt.
  - **An image step** fixed the Thai 12 and 16 pt pages and the English 8 and 12 pt pages. It finds the gutter in the page image when the boxes show none, and reads a box that runs across it again as two halves.
  - **Its cost:** 8–26 ms a page, plus 0.7–0.9 s for each Thai box read again. The English 8 pt page took 6.8 s, for 12 boxes.
  - **What it missed:** the Thai 8 pt page, because the 0.4° skew narrows the white gutter by about 2.5 pt.
  - **PaddleOCR's word boxes** (`return_word_box`) split English boxes at the gutter with no second read. Thai comes back as one word per run.
- **Ruled out: PaddleOCR's layout model** (PP-DocLayout-S, 5.2 MB, 46–79 ms a page). It was wrong on 4 of the 7 side-by-side pages: one region spanned both columns, and every narrow gutter failed. It also read the unruled table of amounts by column.
- **With the rows in column order, in `layout.py`:**
  - `_join_on_baselines` joined nothing.
  - In `_continues`, the step up to the right column counts as an indent, so a paragraph running across the columns splits in two. A list item running across stays whole, through the hanging-indent exception.
  - A stamped header and a page counter were still removed as page furniture.
- **Text pages (ticket 31):** they read right when the PDF draws one column after the other. Drawn line by line across the columns, they interleave as here.

**Decided at triage (2026-10-24, grilled with the user)**
- **Scope:**
  - OCR pages of every kind: scans, pages whose text is drawn as shapes, and pages whose text layer is not trusted. Sideways pages count once they are turned.
  - A page is split into columns only where both sides are body text: long lines that fill their column, as on two-column terms and conditions.
- **Read row by row, as today:** label–value lists, term–definition lists, tables of any kind, forms, timetables, contents pages, and any page where the signs are weak.
  - The user stressed that reading the left side before the right can make content wrong. A label separated from its value is wrong content even when every character is right, and worse than today's fault, because nothing tells the reader.
- **Out of scope:**
  - side panels, signature blocks side by side, and bank details beside signatories (ticket 32);
  - text pages (ticket 31);
  - table structure (ticket 14);
  - kept images.
- **Reading order:** each column to its end before the column to its right, and text across the full width in place, top to bottom. See Column and Reading order in `GLOSSARY.md`.
- **A new column starts a new paragraph or list item,** as a new page does. Ticket 13 splits a paragraph across pages the same way. This includes a numbered clause that runs across the columns.
- **Text-layer rows over a scan,** such as a stamped header or a typed note, take part in finding the columns, so that a note lands in its column. Page furniture is still removed.
- **How:**
  - Recursive XY-cut on the engine's boxes, after any turn, where OCR pages are read in `ocr.py`. It goes through the `OcrEngine` interface, so `FakeEngine` and any engine get it.
  - The body-text guard, and the guards against narrow and numeric columns.
  - The thresholds are the implementer's. Keep a wide margin from the row layouts measured above.
- **Narrow gutters:** measure the gutters of the real two-column pages first.
  - If their boxes bridge the gutter, add the image step, keeping such a page within about twice its first read (ticket 21's budget).
  - If not, leave it out and record why.
- **Time:** pages without columns are not slowed.
- **Summary:** it does not say which pages were split.

**To do**
- [x] Fast tests with `FakeEngine`, with `Styled` lines placed in columns:
  - A Thai and an English two-column page each read column by column.
  - These must not split:
    - label–value lists: at a tab stop, with colons, long labels with short values, and a block inside body text;
    - a term–definition list;
    - unruled tables with and without numbers;
    - a form with two fields on each line;
    - a side panel, signature blocks side by side, and bank details beside signatories;
    - a single-column page and a sideways page.
  - A text-layer row over a column lands in that column. A stamped header and a page counter are still removed.
  - A new column starts a new paragraph, and a new list item.
- [x] Confirm with PaddleOCR in `pytest -m ocr`: a two-column scan reads in order, and a label–value scan reads row by row.
- [x] A synthetic document `two-column-scans` in the corpus, with reference text: a Thai two-column page, an English terms page, and a label–value page as a control.
- [x] Check content, not only CER. On every page that splits, each column must be read whole, and no label separated from its value.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.
- [x] Local samples, allowed by the user on 2026-10-24 for /implement only. Convert all three files on this machine, to set the thresholds on real pages and as the final check.
  - Nothing of them is committed or put in a ticket or test, and the output is deleted after.
  - The supplement's six two-column pages split and read right. Measure their gutters for the narrow-gutter decision.
  - Every other OCR page of the three files reads as today. Check any other page that splits against its image.
  - If a real page splits and its content comes out wrong, stop and ask the user.
  - Record how long each split page takes.

**Also found while measuring, outside this ticket**
- OCR misreads the dotted lines of signature blocks. A synthetic signing page read in the right order still scored CER about 0.10.
- A stray "-" box made a line of a two-column page start a list item, with today's code as well.

## Comments

**2026-10-24, implemented on branch `fix/two-column-scans`**

- **What changed**
  - `ocr._ocr_page` reads an OCR page in parts (`_reading_parts`): bands down the page, and where a band is set in columns, each column to its end before the one to its right. A page without columns is one part and reads exactly as before.
  - The cut works on the engine's boxes, after any turn, in median box heights: a band at 0.8, a gutter at 0.5.
  - Text-layer rows over the scan take part in the cut as boxes of their own, so that a note lands in its column.
  - A band is read in columns only when every column:
    - is body text: lines of 24 characters or more at the median, spaces left out, and fewer than half its characters digits;
    - lines up: most of its lines start at one place, or centre on one, within half a box height.
  - A part of a single line, such as initials in the margin, joins the column beside it, across the narrower gutter.
  - A band goes with the columns of body text above it only when it is more of them:
    - body text set in the same columns, their gutters lining up, as when two columns' paragraphs end on the same line;
    - or body text under the one column that reaches further down than the others.
    - Labels and values, or signatures, under the columns are read row by row after them.
  - `layout.Row.starts_block`: the first row of each part starts a paragraph or list item, as the first row of a page does.
- **Changed from the triage decisions**
  - **No guard on column width.** A column of 24-character lines is never narrow. The digits guard stays, for tables of amounts whose numbers sit close together.
  - **Fill was left out.** How far lines fill their column did not separate the row layouts (0.84 at most) from body text (0.86 at least).
  - **Two rules came from the final check on the samples, below:**
    - **A column that carries on below the other.** On the last page of the supplement's terms, the right column ends mid-page. The band cut split the left column in two, read on either side of the right column.
    - **Lines that line up,** decided with the user on 2026-10-24. On the 110-page contract, the holes a diagonal watermark leaves in three lines lined up and were taken for a gutter: the tail of one numbered item moved below the start of the next.
      - Real columns' lines started within 0.3 box heights of each other, and two centred captions' centres matched exactly.
      - On either side of the watermark's holes, the lines started up to 5.5 box heights apart, and centred up to 5.2 apart.
- **Measured on the local samples.** OCR read each of the three files once. The boxes it found were then put through the code on `main` and on this branch.
  - **Pages that changed:** 7 of the 130 OCR pages.
    - The supplement's six two-column pages.
    - On the 110-page contract, one page with two figure captions side by side.
  - **Each changed page was checked against its image.** Every column reads whole and in order, and no letter or digit was lost or added. No other OCR page changed.
  - **Time:**
    - On the seven pages read in columns, finding columns took 0.7–5.3 ms, against 5.3–12.3 s to read the page in that run.
    - Over every OCR page it took 0.2–0.3 ms at the median.
  - **Gutters:**
    - The supplement's columns left 8–9 pt between their boxes, 0.8–1.0 box heights, above the 0.5 needed. They split on boxes alone, so the image step was not added.
    - The two captions left 44 pt.
    - On synthetic pages, Thai gutters up to 16 pt and English ones up to 12 pt still read as before.
  - **After the code review,** OCR read the three files again. The fixed code read every page exactly as the version checked by eye, and changed the same seven pages.
- **Synthetic pages.** The sub-agent's recorded PaddleOCR boxes were replayed through this branch.

  | Page | Before | After |
  | --- | --- | --- |
  | Thai two-column page | 0.742 | 0.014 |
  | English two-column terms | 0.705 | 0.001 |
  | The Thai page with a stamped header and page counter | 0.768 | 0.044 |
  | Captions side by side | 0.137 | 0.018 |

  - Every label–value layout, form, table, sideways page, single-column page, side panel, signature page and narrow gutter reads exactly as before.
  - **Corpus `two-column-scans`:** CER 0.0114 on the Thai page, 0.0014 on the English page, and 0.0194 on the cover sheet, which is read row by row.
- **Tests**
  - **`test_ocr_pages.py`, with `FakeEngine`:**
    - Thai and English two-column pages;
    - columns whose paragraphs end on the same line;
    - a column that carries on below the other;
    - a note under a column;
    - a stamped header and page counter;
    - initials in the margin;
    - a numbered clause running across columns;
    - eight label–value layouts and three short-line layouts read row by row;
    - labels and values, and signatures, under two columns;
    - a watermark's holes;
    - a line with a wide gap.
  - **`test_corpus.py`:** the `two-column-scans` pages scored against their references with PaddleOCR.
  - **Checked by breaking the code on purpose.** Each mechanism has a test that fails without it:
    - the cut;
    - the line length;
    - the digits;
    - the lining up;
    - joining single-line parts;
    - bands with lined-up gutters;
    - a column carrying on;
    - checking that a band is body text before it goes with the columns;
    - text-layer rows in the cut;
    - `starts_block`.
- **Code review (two axes) found two faults, both fixed:**
  - Rows under two columns whose gaps lay under the gutter, such as labels and values or signature blocks, were taken into the columns, so labels were separated from their values.
  - Any band under the longer column was taken into it, a signature or a date line included.
  - A band now goes with the columns only when it is body text itself.
- **Left as they are**
  - Body text under the longer column, after the other column has ended, is read at the end of that column, such as a closing paragraph that runs across the page but stops short of the gutter. There is none in the samples.
  - `layout.Row.in_columns` means parts of a row set apart at tab stops, which the glossary's Column is not. Renaming it reaches beyond this ticket.
