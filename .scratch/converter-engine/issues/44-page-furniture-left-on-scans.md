# 44: Some page furniture is still left on scans

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** Ticket 22 removes most headers, footers and page numbers on OCR pages. Some still come out as lines of the body:
- **Letterheads OCR garbles,** read less than 0.9 alike from page to page (`_ALIKE` in `layout.py`).
- **Furniture outside the 10% band on fewer than 3 pages,** or on pages none of which is next to another, such as a short appendix's page numbers. The same holds for furniture inside the band that OCR read only alike, not the same.
- **Page numbers OCR misreads,** which no longer follow the pages.
- **A first page's footer at another height** from the rest.

They waste AI tokens, and a line left at the top of a page can join the paragraph that runs on from the page before.

**Blocked by:** none

**Status:** needs-triage

**Split from:** ticket 22, on 2026-11-11. Its comment of that day holds the measurements.

**Seen on:** the samples in `docs/example_pdf/`, converted on 2026-11-11 with the user's permission:
- the 110-page contract: 4 letterhead rows of a company certificate, and the form footer on its first page;
- the 34-page supplement: a few letterhead rows read on one page alone, form names printed once, and two page numbers at different heights.

Junk rows read in initials at the foot of the page are ticket 38's.

**To decide at triage**
- Whether a lower bar is safe where a row repeats on many pages, as a letterhead does. At 0.8, a form's label in the body matched as well (ticket 22).
- Whether furniture on a single page, such as a cover's contract number, should go at all.

## Comments

**2026-11-12, grilled together with ticket 38**

- **Its rules wait for ticket 38.** Ticket 38 drops initials at the foot of scans as page furniture, and finds pictures such as logos in scans, which changes what furniture is left. This ticket's two triage questions are settled after ticket 38 is built, on fresh measurements of the samples.

