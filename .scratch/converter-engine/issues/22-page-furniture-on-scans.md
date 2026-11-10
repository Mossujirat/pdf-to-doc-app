# 22: Page furniture on scans is left in

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, headers, footers and page numbers stay in the output, although the spec says outputs leave page furniture out:
- The text in a letterhead logo comes out as broken fragments at the top of most pages, often marked uncertain.
- A footer line with its page number, and page numbers on their own, come out at the bottom of most pages.

They waste AI tokens and break the text between pages.

**Blocked by:** none

**Status:** needs-triage

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
