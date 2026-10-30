# 26: Ticked boxes on scans are lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On scanned forms and tables, a tick in a box often carries the meaning:
- which project type or duration was chosen;
- whether a company is an SME;
- which party owns, manages and pays for each kind of intellectual property.

The ticks vanish from the output, so the choice is lost. Sometimes a tick comes out as a stray "V" or "√", marked uncertain. Nothing tells the reader that a choice was made at all.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`, whose attachments are scans pasted into Word pages, converted on 2026-10-23 with the user's permission. Seven pages lost their ticks:
- a proposal form's options;
- a company status box;
- a status list;
- four pages of tables that share out intellectual property rights. On one of them, the ticks name the grant recipient alone, where the page before names both parties.

**To decide at triage**
- **Finding boxes:** how to find the boxes, empty or ticked, on an OCR page: small squares in the page image, next to the text they qualify.
- **Writing them out:**
  - In Markdown, perhaps as `[x]` and `[ ]`, as task lists do.
  - In DOCX, as ☒ and ☐.
  - Or as a placeholder. A new placeholder kind is a glossary change.
- **When unsure:** a tick the converter cannot confirm is uncertain text.
- **Text pages:** whether boxes there need anything. Word exports boxes as characters, which already come through.

## Comments

**2026-10-25, from grilling ticket 14 (scanned tables)**

- Once ticket 14 is done, a ruled table on an OCR page comes out as a table.
  - A cell whose only content is a lost tick comes out empty, in its place.
  - A tick read as "V" or "√" lands in its cell, marked uncertain.
- Ticks themselves stay with this ticket.

**2026-10-30, triage**

- **After the next deploy:** the user chose to leave it for a later version. See `.scratch/next-deploy.md`.
- Status stays `needs-triage` until then.
