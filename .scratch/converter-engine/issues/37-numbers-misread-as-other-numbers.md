# 37: Numbers misread as other numbers are not marked

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, a number misread as another number reaches the output without being marked as uncertain text, because its shape does not show the misread. Seen on a 110-page Thai contract among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission (ticket 23):
- an extra digit in a tax amount;
- a footnote marker joined onto the number before it, which gained a digit;
- a year that lost its last digit;
- a day in Thai digits read as Arabic digits of another value;
- a page count "x/y" read as one number;
- a range that lost its dash;
- a count dropped from five of seven table rows.

In a contract these are amounts, dates and counts, where one digit changes the meaning. The reader and the AI are not warned.

**Blocked by:** none

**Status:** ready-for-agent

**Why it is a ticket of its own:** ticket 23 marked numbers with letters among their digits, such as "12,ooo.oo", and left these as the spec's known gap: "Numbers misread as other numbers". Grilling the what's-new page on 2026-11-02 found that no open ticket stood for them, so they could not be a known limitation. The user chose to open this one, so that the page names the gap (`.scratch/web-service/issues/16-whats-new-page.md`). The release that closes it rewords the limitation, which stays for ticket 40 (triage, 2026-11-03).

**To decide at triage**
- Which signals could catch them without marking every correct number: the engine's confidence per character, a total that does not add up, a date that cannot be, a number unlike its neighbours in the same column.
- Whether a number that cannot be checked should be marked at all, or only counted in the summary.

## Comments

**2026-11-03, triage**

- **In this round,** with 24, 26 and 32.
- **Scope:**
  - **Rules,** as ticket 23 added in `misreads.py`: a date that cannot be (a year of three digits after พ.ศ., ค.ศ. or ปี, or in a date; a day over 31), and comma groups that are not three digits, such as "1,2345". A number is marked only when a rule finds it wrong; numbers that cannot be checked are not marked.
  - **A measurement of per-character confidence.** PaddleX works out a score per character and keeps only their mean (its text-recognition decoder). Patch it on this machine only, run the 110-page contract, and see whether misread digits score lower than correct ones. Record the result here; whether to use it is decided then, in ticket 40.
- **Left for ticket 40:** totals that do not add up, numbers unlike their column, and per-character confidence if the measurement favours it.
- **The known limitation stays for good,** pointing to ticket 40 once this one closes: some misreads leave no trace, so readers must always check amounts and dates. The release that closes this ticket lists the rules and rewords the limitation to fit what is left.
- **Estimate:** small for the rules. The measurement is a spike of a day or so.
