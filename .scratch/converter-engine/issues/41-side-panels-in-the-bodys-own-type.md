# 41: Side panels set in the body's own type are read across

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, and on text pages drawn line by line across, a narrow panel set beside a letter in the letter's own type, such as the sender's offices and bank details, is joined line by line with the letter. An account or registry number lands in the letter's sentences. Nothing marks it.

**Blocked by:** none

**Status:** needs-triage

**Split from:** ticket 32, on 2026-11-04. Ticket 32 reads a panel set in smaller type after the body beside it: its lines do not share the body's baselines, as labels beside their values do. A panel in the body's own type shares them, so it looks like labels and values set apart, and the column finder keeps it row by row.

**What is known so far**
- **The test fixture** "a letter with a panel of addresses in its own type" in `tests/test_ocr_pages.py` pins today's reading, row by row.
- **On the samples,** both side panels seen were in smaller type (the GIZ supplement's letter and the 110-page contract's privacy notice), and ticket 32 reads them.
- **Cues not yet tried:** the panel's lines are much shorter than the body's on every row; the panel sits at the page's edge and runs down more lines than any label column; the body's lines read as sentences that run on from row to row.

**To decide at triage**
- Whether a sample shows this layout at all, before building for it.
- Which cue separates it from labels and values, measured on the label–value fixtures.

## Comments
