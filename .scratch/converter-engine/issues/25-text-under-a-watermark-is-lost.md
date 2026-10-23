# 25: Text under a diagonal watermark is lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On scanned copies that carry a large diagonal watermark, the OCR text under the watermark is missing from the output. Examples are a company registration certificate printed with the registry's mark, and an ID card copy with a line written across it. Whole list items vanish, or only fragments of them are left. Nothing marks the gap, and the summary does not show it. A reader, or an AI, takes the rest of the page for all of it.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`. Its attachments are scans pasted into Word pages. It was converted on 2026-10-23 with the user's permission.
- **A certificate's pages:** on six of them, the text under the watermark was lost. On one page, five of eight numbered items came out as fragments or not at all.
- **Two ID card copies:** the diagonal line across each was missing, as was much of the card's own text.

**Not yet known:** which stage loses the lines.
- The detector may not find lines crossed by the watermark.
- The recogniser may return nothing useful for them.
- Something after the engine may drop what it returned.

**To decide at triage**
- **Find the stage first,** on a synthetic scan with a diagonal watermark over known text.
- **Reduce the watermark's effect before reading,** for example by its colour or lightness, if the cause allows it.
- **Make the loss visible.** Where the page shows ink but nothing was read, the reader should be told, for example by uncertain text or a placeholder. A new placeholder kind is a glossary change.
- **Diagonal text itself:** it is not read while text-line orientation is off (see ticket 21).
