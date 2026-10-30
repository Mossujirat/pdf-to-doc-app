# 09: Final check on the real samples

**Parent:** Tables on OCR pages spec, in this feature folder.

**What to build:** Before the feature is merged, check it on the local samples in `docs/example_pdf/`. On every page with a table, the output must hold the table the page shows, or say plainly that it may be incomplete. Every other OCR page must read as it did, apart from one line per row. The samples are:
- **A 110-page contract.** Its attachments are scans pasted into Word pages:
  - about 25 scanned pages with tables;
  - ten sideways pages, most of them tables;
  - budget tables on pages 69–72, whose text layer cannot be trusted.
- **A 34-page scanned supplement,** with seven table pages, two of them sideways.
- **A 5-page agreement** whose text is drawn as shapes, with ruled tables.

**Blocked by:** 01, 02, 03, 04, 05, 06, 07, 08

**Status:** done

**Branch:** `feat/ocr-tables`

**Permission first**
- [x] Ask the user's permission before converting or opening any sample. The samples are real contracts, and one is marked confidential.
- [x] On the terms of tickets 18 and 21 of the converter:
  - convert on this machine only, never by a sub-agent;
  - nothing of them is committed or sent anywhere;
  - tickets get counts only;
  - the output is deleted after.

**Checks**
- [x] **Convert all three samples** to Markdown and DOCX, in default mode. Then convert pages 69–72 and the agreement with kept images too.
- [x] **Check every page with a table against its image:**
  - each ruled table is a table, with the right text in each cell, merged cells kept and wrapped cells whole;
  - sub-rows are split where the page shows them;
  - an incomplete table is labelled and gives its rows one per line;
  - a table with no rules gives its rows one per line.
- [x] **No false tables:**
  - no table appears where the page shows none;
  - ruled letterheads stay page furniture;
  - boxed notices stay text.
- [x] **Every other OCR page** reads as before, apart from one line per row. Check any other page that changes against its image.
- [x] **No line is lost** on pages 69–72 or on the agreement's pages (ticket 33).
- [x] **The summary's table counts** match what the pages show.
- [x] **In real Word:** merged cells, breaks inside cells, and uncertain text highlighted inside cells.
- [x] **Time:** record how long each OCR page takes, and the whole conversions. They must stay within ticket 08's target for 110 pages.
- [x] **If a real table's content comes out wrong,** stop and ask the user.
- [x] Run the checks in the Linux container once more.
- [x] **Comments:** record the results here as counts only, with no text or content from the samples.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **Check each scan's resolution where it has a table.** The grid holds on synthetic scans at 150 dpi and more. At 110 dpi and below, thin rules scan lighter than the ink threshold (grey 160): cells merge into false spans, and their text reads in a worse order than with no table at all. The user chose to keep the threshold, as the samples' scans are 300 dpi. If a sample's table scan is that coarse, show the user what it does.
- **Shaded headers:** the threshold was kept partly because a lighter one lost a table whose header was shaded 30% grey. Check that shaded header rows on the samples keep their cells.
- **Stray mark boxes** ("ญ", "ะ") land in cells as an extra line until ticket 07 drops them.

**2026-10-29, from ticket 08 (incomplete tables)**

- **Check where the label lands.** A table is incomplete when only part of its rules is found (a boxed header row with rows set out under it, or rules that close off a space that is no rectangle), or when one of the engine's boxes runs through a rule of its cell, more than half a font size inside both its ends. On the corpus no page got a false label; on the samples, count the labels and check each against the page image: a stamp, a signature box or a form's boxes should get none.
- **A short paragraph one blank line under an incomplete table** is taken as its lines. Note any on the samples.
- **The summary's counts** now say how many tables on OCR pages came out as tables and how many may be incomplete, with their pages.

**2026-10-29, checked on the samples (counts only)**

- **The user allowed it** on the terms above: converted on this machine by the main session, no sub-agent; page images and outputs were looked at in the session; nothing committed or sent; outputs deleted after.
- **Each page was compared with the branch base `e43f853`,** before tables on OCR pages.
- **Found, and fixed with tests, with the user's decisions:**
  - **The 110-page contract failed to convert.** Rules that meet but close off no space, as an L does, made `grids._grid` index an empty list. This came in with ticket 08.
  - **False tables:** on 2 pages, a watermark printed as dots was taken for rules, making tables of empty cells. A grid none of whose cells holds text is no table now.
  - **Tables whose rules a scan broke:** on 3 sideways pages, spaces left open made no cell. Their text, such as 5 column headings on one page, fell out after the table, and check marks landed in the wrong cells. On a fourth page, a row's label fell out of its incomplete table.
    - Text within a grid's frame that no cell holds now makes the table incomplete, taking that text too.
    - Every other table on the samples had none.
  - **False labels:** 3 ruled tables were labelled incomplete.
    - 2 had a box whose stacked upper marks reached 0.58 and 0.62 font sizes over the rule above, in a tight row.
    - 1 had a box reaching 0.53 past the frame beside it, in small print.
    - A rule must now lie 1.0 font size inside both ends of a box. It was 0.5. The one box that held two cells' text reached 2.9 past the rule on its shorter side.
  - **Tables joined in Word:** a table ending one page and one starting the next touched in the DOCX, and Word joined them, 2 times on the contract. A paragraph between them now starts the new page.
- **Tables after the fixes:**
  - **Contract:** 50 tables on 29 pages, and 5 incomplete tables, on pages 29, 69, 106, 108 and 109.
  - **Supplement:** 7 tables on 6 pages, and 1 incomplete, on page 26.
  - **Agreement:** 3 tables on 2 pages.
  - The summary's counts match the outputs on every page, and the headline's pages too.
- **Checked against the page image:** 23 table pages of the contract, 5 of the supplement and 1 of the agreement, and 3 pages with no table. The rest were checked by structure, against a page laid out alike: 10, 2 and 1 pages.
  - **Ruled tables:** right text in each cell; merged cells kept; wrapped cells whole; double rules read as one; empty tables kept with their headers.
  - **Labelled tables:** the 6 are a Gantt chart with shaded cells, a sideways Gantt chart askew, a summary block where one box held two cells' words, and the 3 broken scans.
  - **Tables with no rules** (budget sheets, a reports list) come out one line per row, unlabelled.
- **Not caught, recorded as known limits:**
  - **Row labels outside a budget sheet's rules:** on 3 pages, 15 ruled blocks; the labels are read apart from their numbers. The user chose to open ticket 10.
  - **A table continued onto a page as one boxed row** is read as lines, its two cells' lines interleaved, as before tables on OCR pages: 1 page. The user chose to keep the rule that a boxed row alone is lines.
  - **On the most broken scan,** only a block of check marks made a grid, so the label lands mid-table and the rest reads as lines: 1 page.
  - **A header row whose top rule was not found** reads as a line just above its table: 1 page.
  - **False sub-rows:** a name wrapped onto a second line, level with another column's second line, split 2 rows into sub-rows: 1 page.
  - **The engine missed** a "5" in one cell, list numbers in another, a row's label in a third and dashes in some empty cells. The base missed the same.
- **No false tables otherwise:**
  - A chart with grid lines, page headers, logos and a boxed notice beside a QR code made none.
  - Letterheads and footers stayed page furniture.
- **Other OCR pages:** 34 pages of the contract, 8 of the supplement and 2 of the agreement changed with no table on them.
  - Their characters match the base, but for list markers ("- ") the base gave to numbered lines that are now rows.
  - Of the 6 diffs looked at, all changed by one line per row only.
  - **Checked against the image:** the impact-pathway diagram.
- **No line lost:** on pages 69–72 and the agreement's 5 pages, every character of the base is there, but for one list marker.
- **Kept images:** the contract's 4 untrusted pages and the agreement's 5 pages, still read with OCR, give the same tables as in default mode. 2 lines break differently.
- **In real Word** (Word 16 saving the DOCX as PDF): merged cells, breaks in cells and yellow highlights in cells all show. Word gives the columns equal widths, as for every DOCX table.
- **Time, on Windows** (Ryzen AI 7 350), default mode:

  | Sample | Pages | OCR pages | Total | Per OCR page, mean / most | Base |
  | --- | --- | --- | --- | --- | --- |
  | Contract | 110 | 91 | 450 s | 4.8 s / 13.7 s | 487 s |
  | Supplement | 34 | 34 | 200 s | 5.9 s / 12.8 s | 214 s |
  | Agreement | 5 | 5 | 31 s | 4.7 s / 7.4 s | 33 s |

  - All within ticket 08's 15 minutes. A second run of the contract, after the DOCX fix, took 488 s.
  - With kept images: the contract took 66 s, the agreement 31 s.
  - Word lays out the contract's DOCX on 208 pages, none blank, with 50 tables.
- **The harness** on `corpus/synthetic` and `corpus/degraded` is the same as at 7082519, page by page.
- **From ticket 04's and 08's comments:**
  - **Scan resolution:** every table page's scan is 220 dpi on the contract and 300 dpi on the supplement. The contract's 4 untrusted pages and the agreement's pages have no scan. None is near 110 dpi.
  - **Shaded rows and cells keep their cells:** the contract's grey total rows, its yellow cells, and the supplement's shaded header rows. Only the two Gantt charts, shaded and one askew, were labelled instead.
  - **No short paragraph** under an incomplete table was taken as its lines. The two made from part rules end at their last row.
- **Checked by breaking the code on purpose** (`test_ocr_tables.py`, `test_docx_output.py`):

  | Broken | Tests that fail |
  | --- | --- |
  | no guard for rules round no space | 1 |
  | grids with no text kept | 1 |
  | text within a frame that no cell holds left out | 1 |
  | a rule 0.5 font size inside a box's ends taken as crossed | 2 |
  | no paragraph between tables that touch | 2 |

- **Code review (two axes):**
  - **Standards:** no hard violations. Fixed:
    - the frame check worked out twice;
    - the removal of taken boxes written twice, now `_without`;
    - a name that said nothing (`ruled`);
    - three near-synonyms in `docx_output`, now `touching` and `previous`.
  - **Spec:** the user's decisions are all in place. Fixed: when two grids' frames overlap, the second no longer becomes incomplete for text the first already took.
  - **Not done, no case on the samples:**
    - a watermark's dots round a whole real table would hide it, since rules inside other rules are part of them;
    - a table whose rules close off an L, with a note in the open corner, now gets the label.
- **Run after the review:**
  - **Windows:** pytest (644 passed, 1 skipped) and mypy.
  - **Linux image:** mypy, pytest (645 passed), `pytest -m ocr` (25 passed), `pytest -m slow`, and the harness, with the same totals as at 7082519.
  - **The samples:** Markdown and summary byte for byte the same as before the review's fixes.
