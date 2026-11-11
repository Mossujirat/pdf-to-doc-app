# 45: List markers that OCR does not read at all

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, PaddleOCR sometimes reads a list item's line without its bullet or dash. With no marker, the row is not a list item:
- The item's text runs on from the item or paragraph above it, when the line before is close enough to carry on.
- Nothing marks the place, so a reader cannot tell an item was there.

**Blocked by:** none

**Status:** needs-triage

**Split from:** ticket 43, on 2026-11-11. Ticket 43 puts back the space OCR drops after a marker it did read. It cannot bring back a marker OCR never read.

**Seen on:**
- The 10-page scanned contract of ticket 42, converted on 2026-11-10 with the user's permission: one dash of a dash list was lost, while the dashes around it were read.
- A synthetic scan, Sarabun at 16 pt, 200 dpi, on 2026-11-11: a line starting "• " with a full space lost its bullet, on three seeds, and its text ran on from the item above, which started with "– ". The probe's script was not kept: draw a list of dash and bullet items with `Scan` in `corpus/pdf_builder.py` and convert it with PaddleOCR.

**To decide at triage**
- Whether the row's indent, beside list items whose markers were read, is enough to tell that an item starts there.
- Whether the gap where the marker was can be found on the image, as the detector's box starting further right than its neighbours.
