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

**Status:** ready-for-agent

**Branch:** `feat/ocr-tables`

**Permission first**
- [ ] Ask the user's permission before converting or opening any sample. The samples are real contracts, and one is marked confidential.
- [ ] On the terms of tickets 18 and 21 of the converter:
  - convert on this machine only, never by a sub-agent;
  - nothing of them is committed or sent anywhere;
  - tickets get counts only;
  - the output is deleted after.

**Checks**
- [ ] **Convert all three samples** to Markdown and DOCX, in default mode. Then convert pages 69–72 and the agreement with kept images too.
- [ ] **Check every page with a table against its image:**
  - each ruled table is a table, with the right text in each cell, merged cells kept and wrapped cells whole;
  - sub-rows are split where the page shows them;
  - an incomplete table is labelled and gives its rows one per line;
  - a table with no rules gives its rows one per line.
- [ ] **No false tables:**
  - no table appears where the page shows none;
  - ruled letterheads stay page furniture;
  - boxed notices stay text.
- [ ] **Every other OCR page** reads as before, apart from one line per row. Check any other page that changes against its image.
- [ ] **No line is lost** on pages 69–72 or on the agreement's pages (ticket 33).
- [ ] **The summary's table counts** match what the pages show.
- [ ] **In real Word:** merged cells, breaks inside cells, and uncertain text highlighted inside cells.
- [ ] **Time:** record how long each OCR page takes, and the whole conversions. They must stay within ticket 08's target for 110 pages.
- [ ] **If a real table's content comes out wrong,** stop and ask the user.
- [ ] Run the checks in the Linux container once more.
- [ ] **Comments:** record the results here as counts only, with no text or content from the samples.

## Comments

**2026-10-26, from ticket 04 (ruled tables on scans)**

- **Check each scan's resolution where it has a table.** The grid holds on synthetic scans at 150 dpi and more. At 110 dpi and below, thin rules scan lighter than the ink threshold (grey 160): cells merge into false spans, and their text reads in a worse order than with no table at all. The user chose to keep the threshold, as the samples' scans are 300 dpi. If a sample's table scan is that coarse, show the user what it does.
- **Shaded headers:** the threshold was kept partly because a lighter one lost a table whose header was shaded 30% grey. Check that shaded header rows on the samples keep their cells.
- **Stray mark boxes** ("ญ", "ะ") land in cells as an extra line until ticket 07 drops them.

**2026-10-29, from ticket 08 (incomplete tables)**

- **Check where the label lands.** A table is incomplete when only part of its rules is found (a boxed header row with rows set out under it, or rules that close off a space that is no rectangle), or when one of the engine's boxes runs through a rule of its cell, more than half a font size inside both its ends. On the corpus no page got a false label; on the samples, count the labels and check each against the page image: a stamp, a signature box or a form's boxes should get none.
- **A short paragraph one blank line under an incomplete table** is taken as its lines. Note any on the samples.
- **The summary's counts** now say how many tables on OCR pages came out as tables and how many may be incomplete, with their pages.
