# 34: Diagonal text on scans is not read

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** Some scans carry text set at a slant across the page, such as a watermark naming the issuer, or a line written across an ID card copy. That text is missing from the output. Nothing marks it.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission. A certificate's pages carry a diagonal watermark, and two ID card copies carry a line written across them.

**What is known so far**
- **Split out of ticket 25.** That ticket recovers the upright text under a watermark; the user chose to leave the slanted text itself for later.
- **PaddleOCR's text-line orientation is off** (see ticket 21), and its detector finds slanted regions only now and then. On the contract's pages, regions slanted 30–45° scored 0.5–0.6.

**To decide at triage**
- Whether such text belongs in the output at all. A watermark repeats the issuer's name on every page, but a line written across an ID card copy, which often states what the copy may be used for, can matter to the reader.
- Where it goes, if read: where it sits on the page, or once at the page's end.
- How to read it: turn the slanted region upright before reading it, and what that costs.
