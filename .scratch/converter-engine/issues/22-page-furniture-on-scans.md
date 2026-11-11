# 22: Page furniture on scans is left in

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, headers, footers and page numbers stay in the output, although the spec says outputs leave page furniture out:
- The text in a letterhead logo comes out as broken fragments at the top of most pages, often marked uncertain.
- A footer line with its page number, and page numbers on their own, come out at the bottom of most pages.

They waste AI tokens and break the text between pages.

**Blocked by:** none

**Status:** done

**Branch:** `fix/page-furniture-on-scans`

**Seen on:** a 34-page scanned contract supplement among the local samples in `docs/example_pdf/`, converted on 2026-10-22 and 2026-10-23 with the user's permission. The file joins three documents, and each one numbers its pages from 1.

**A 110-page Thai contract** among the same samples has scans pasted into Word pages. It was converted on 2026-10-23 with the user's permission.
- **What works:** the Word page's header and footer, laid over each scan as text, were dropped on every page, as the spec intends.
- **What stays:** the scans' own form footers and page numbers stayed on most scan pages, as lines of the body. Examples are a form's name with its revision and page number, and an "x/7" count.

**What is known so far:** `remove_page_furniture` in `layout.py` matches rows by their exact text at the same edge. OCR reads the same letterhead a little differently on each page. One acronym in it came out three different ways, with a capital I read as "l" or "!", so the rows never match. Why lone page numbers stay has not been looked into.

**To decide at triage**
- **Check again after ticket 19.** Every page of this sample is rotated, and the edge bands depend on positions on the page.
- How OCR rows can match while their text differs slightly, for example by similarity rather than equality, and only within the edge bands.
- Whether page numbers need their own rule on OCR pages, where a misread digit breaks the "same distance from the PDF page number" test.

## Comments

**2026-10-30, triage**

- **After the next deploy:** the user chose to leave it for a later version. See `.scratch/next-deploy.md`.
- Status stays `needs-triage` until then.

**2026-11-10, from a 10-page scanned contract**

The 10-page scanned Thai contract of ticket 42 was converted on 2026-11-10 with the user's permission. Its pages are upright, so ticket 19 does not affect what follows. Each page has a header of two lines, and a footer of three lines beside initials.

- **Exact matching works when OCR reads alike.** The header line, with the contract number and "หน้า x/9", was removed on 8 of 9 pages. On the ninth, OCR read one character of the contract number differently, so the line stayed. This is the case this ticket already names.
- **New: lines just outside the edge band are never removed,** however exactly they repeat.
  - The header's second line, a form version, starts at about 10.8% of the page's height. The band is 10%.
  - The footer's first line starts at about 87.6%, above the bottom band, which starts at 90%.
- **New: a block of furniture that crosses the band edge is only partly removed.** Only the footer's middle line is inside the band, so it is the only one removed.
- **New: a footer line that shares a baseline with initials never matches.** `_join_on_baselines` joins it to the initials that OCR read as junk (ticket 38). The row's text then differs on every page.
- **New: leftover furniture damages the body text.** On 3 of 9 pages, a clause runs on from the page before. The leftover version line joins that clause's paragraph, so the clause starts with it. Elsewhere it stands as a paragraph of its own.
- **Leads:**
  - remove a block of lines when one of them is furniture and the others repeat with it;
  - let a row that repeats on most pages lie a little outside the band;
  - match the footer before rows are joined on baselines, or once junk read from initials is gone. That ties this ticket to ticket 38.

**2026-11-11, grilled and fixed**

The four samples in `docs/example_pdf/` were converted again on 2026-11-11 with the user's permission. The rows reaching furniture removal were measured, and the rules were tried on them. Only numbers are recorded here.

- **Why furniture stayed, measured:**
  - **Rows sit just outside the band.** On the 34-page supplement, the lone page numbers end at 87-89% of the page's height, above the bottom band. On the 110-page contract, the scans' own form footer sits at about 81%, as the scans are pasted into larger Word pages. The 10-page contract's second header line starts at 10.7%.
  - **OCR reads the same row differently** on some pages, as this ticket first said.
  - **Footers number their pages with a number at the end of the row,** with no word for "page" before it. Their text differs on every page.
  - **The junk from initials is on the footer's own row.** OCR boxes it beside the footer line, not `_join_on_baselines`. Its boxes score below 0.85 (`LOW_CONFIDENCE`); the footer line's score 0.96 or more.
- **Decided with the user:**
  - **On OCR pages, rows OCR read match by what OCR is sure of in them,** leaving out boxes below `LOW_CONFIDENCE`; all of the row when OCR is sure of none of it.
    - Two rows match when their middles lie within 1.5% of the page's height of each other.
    - They must say the same, or be at least 0.9 alike by difflib's ratio when both have 8 characters or more. Rows that differ in their digits alone never match.
    - Text from the text layer, as a Word header laid over a scan, still matches exactly only. So does a row that holds text-layer text beside OCR's.
  - **Inside the 10% band, one other page will do** when the rows say the same past what OCR is unsure of, as before. Rows only alike need the 3-page rule below, a change made in review.
  - **Further in, up to 20% from the edge, a row must repeat on at least 3 pages, one of them next to its own.** A form's label repeated on every other page is content, and stays.
  - **A number ending the row counts as a page number on OCR pages,** under the same 3-page rule. Read as it stands too, so a header ending in a year still matches.
  - **The junk from initials on a footer's row is handled here,** without waiting for ticket 38: the whole row goes, its junk too. Junk rows of their own stay for ticket 38.
  - **No rule for page numbers OCR misreads.** None was seen among lone page numbers.
  - **Text pages are unchanged.** The corpus's existing files are unchanged; `furniture-on-scans` is added.
  - **What remains** goes to ticket 44, and the known limitation is reworded to point to it.
- **The similarity bar was raised from 0.8 to 0.9 in testing.**
  - At 0.8, a test's two body lines in the top band that differ in a word, 0.81 alike, were removed.
  - At 0.8 on the 110-page contract, a company certificate's list heading was removed on 2 of the 4 pages that repeat it at the same height, 0.79-0.85 alike.
  - At 0.9, both stay. The cost: 4 rows of the certificate's letterhead that OCR garbled, 0.80-0.89 alike, stay too.
- **Copies of one page keep what they repeat.** In testing, three pages drawn with the same clauses lost their first two lines, at 17%, repeated on three pages in a row. Two OCR pages that share half the lines of either's body or more, away from the edges, now count as copies, such as a form filled in for each of several people. Neither counts for the other. A first try that counted any shared line lost 6 rows of furniture on the samples, where pages share a signatory's name. The rule now gives the samples the same rows as without it.
- **Rows removed, before and after:**

  | Sample | OCR pages | Removed before | Removed as well now |
  |---|---|---|---|
  | 10-page contract | 10 | 26 | 28 |
  | 34-page supplement | 34 | 56 | 31 |
  | 110-page contract | 91 of 110 | 220 | 69 |
  | 5-page agreement, no furniture | 5 | 0 | 0 |

  - **10-page contract:** every header and footer line of pages 2-10 is gone. Left: 5 junk rows from initials (ticket 38), and the cover's contract number, on one page.
  - **34-page supplement:** the page numbers of 14 pages, a footer on 5, and 12 letterhead rows OCR misread. Left: a few letterhead rows read on one page alone, form names printed once, and two page numbers at different heights.
  - **110-page contract:** the form footer on 52 of its 53 pages, and a company certificate's footer and header. Left: the form footer on its first page, at another height, and 4 letterhead rows.
  - No row removed as well now is content, read row by row.
- **Not done:**
  - **Removing a block of lines when one is furniture,** a lead from 2026-11-10: each line of the measured blocks repeats on its own, so the 3-page rule removes them.
  - **Taking the band from the scan's own edges:** a pasted scan's furniture is found by the 20% reach.

**2026-11-11, after code review (two axes)**

- **Spec, fixed:**
  - **Rows only alike in the band now need 3 pages, one of them next to their own.** Review measured two body lines a word apart at 0.96 alike, and a signing line with "ผู้ว่าจ้าง" against "ผู้รับจ้าง" at 0.90. Either pair would be removed from two pages in the band. Rows that say the same, past what OCR is unsure of, still need only one other page in the band. The cost on the samples: 3 letterhead rows of the 34-page supplement stay, matched on one other page only. The other samples give the same rows.
  - **A row holding text-layer text beside OCR's is matched exactly only.** Before, its text-layer part was matched as alike.
  - **The docs now agree on the 3-page rule:** the row's page and two others, one of them next to it. `spec.md` and `corpus/README.md` said it two other ways.
- **Standards, fixed:** a shared `_page_counter`; clearer names (`_OCR_EDGE_REACH`, `_FURTHER_IN_PAGES`, `page_index`); each new constant says where its value comes from; `remove_page_furniture`'s docstring mentions the 3-page rule.
- **Recorded, not changed:**
  - **The digit guard gives way to any other difference.** An amount that differs, plus a letter OCR misreads elsewhere in the row, can be alike. Such rows now need 3 pages, one of them next to their own, at the same height.
  - **A short row that is a label and a number following the pages,** such as an instalment's heading at the same height on consecutive pages, would be taken for a page number. None was seen.
  - **Pages of different heights** are compared by share of height. A footer at a fixed distance from the bottom moves between them, by little on the samples.
  - **The improvement line for the release** is written at the deploy, as the release rules in `releases.py` say.
  - The test strings were checked for text copied from the samples. The test strings and the corpus were reworded during implementation, and none is copied.
