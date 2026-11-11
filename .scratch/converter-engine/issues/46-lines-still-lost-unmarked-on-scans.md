# 46: Lines can still be lost on scans with nothing marking the gap

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A line on a scan can still be missing from the output, with nothing marking the gap and no warning in the summary. A reader, or an AI, takes the text for complete. This is broken text (missing text).

**Blocked by:** none

**Status:** needs-triage

**Split from:** ticket 42, on 2026-11-11, at the release. Ticket 42 re-reads a page when the detector dropped a region shaped like a line, and recovers what that reading finds. Its decision 5 put a known limitation on the what's-new page. That limitation points here.

**What is known so far** (tickets 25 and 42)
- **What ticket 42 recovers:** a region the detector dropped, scoring under 0.6, that is 0.5–2.5 of the page's lines tall and at least 5% of the page wide. The page is read again, blurred by 1.5. Only boxes read at a confidence of 0.7 or more, with 2 characters or more, and over no box already read, are kept.
- **What it can still lose:**
  - a line the detector drops in a region outside those limits;
  - a line the blurred reading misses too, or reads below 0.7;
  - a line the detector never scored as a region at all.
- **Nothing warns when a line-shaped region stays unread.** Tickets 25 and 42 decided against it: most such regions are not lost lines. On the samples, 15 of 46 gave nothing when blurred, being highlight bands, rules and signatures, and 13 repeated text already read.
- **The detector's score does not separate real text from junk.** Both scored 0.40–0.60.
- **No synthetic page loses a line this way.** Ticket 42 tried about 180 variants.

**To decide at triage**
- Whether a sign narrow enough to warn on exists: say, a line-shaped region left unread between two lines of one paragraph.
- Whether the summary, or a mark in the text, should say where a line may be missing.
