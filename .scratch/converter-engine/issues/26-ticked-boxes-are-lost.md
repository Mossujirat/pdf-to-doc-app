# 26: Ticked boxes on scans are lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On scanned forms and tables, a tick in a box often carries the meaning:
- which project type or duration was chosen;
- whether a company is an SME;
- which party owns, manages and pays for each kind of intellectual property.

The ticks vanish from the output, so the choice is lost. Sometimes a tick comes out as a stray "V" or "√", marked uncertain. Nothing tells the reader that a choice was made at all.

**Blocked by:** none

**Status:** done

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

**2026-11-03, triage**

- **In this round,** with 37, 24 and 32.
- **OCR pages only.** Word exports boxes on text pages as characters, which already come through. A text page that loses its boxes would be a ticket of its own.
- **Output:** ☒ for a ticked box and ☐ for an empty one, in both Markdown and DOCX, set before the text the box qualifies. No new placeholder kind. Mid-line, `[x]` would not be a task list anyway.
- **When unsure:** a box whose tick cannot be confirmed is uncertain text, by giving it a low confidence.
- **Where the work is:**
  - A new pass finds small, square, closed outlines in the page image and measures the ink inside them. The grid finder cannot: its rules must be at least one text height long. Its ink and straightening helpers can be reused.
  - A found box enters the OCR page as one more piece of text, so it follows the existing path into lines, cells and both outputs.
  - The engine's own reading of the box ("V", "√", "口") is dropped where it overlaps a found box.
- **To check on the samples first:** whether the rights tables have drawn boxes, or bare ticks in a cell with no box; a bare tick needs a second detector, ink in a cell that holds no text. And what PaddleOCR makes of a box: a piece of its own, part of its label, or nothing.
- **Risks:** a box taken for "口", "O" or "0"; a hand tick that crosses the box edge; a row of digit boxes, such as a tax ID, taken for boxes to tick; noise or stamps read as ticks.
- **Estimate:** medium, two to four days with tests, a corpus file and the harness.

**2026-11-04, built**

**On the samples first** (the 110-page contract's page images recorded for ticket 37; `docs/example_pdf/reference/ticked-boxes/`):
- **The lost ticks are drawn boxes,** ☑ and ☐, on the proposal form, the company status table and the rights annex, in cells of ruled tables there. Some empty ones are drawn with a shadow on two sides.
- **Bare ticks in table cells** (pages of evaluation tables and delegations) are typed characters, and PaddleOCR already reads them as "✓", "√" or "x". Nothing is lost there.
- **PaddleOCR reads a box as a box with no text,** or takes it into the text beside it and drops it: "1.4 ระยะเวลาโครงการ☑12 เดือน" came out "1.4 ระยะเวลาโครงการ12 เดือน".

**What was built** (`check_boxes.py`, wired in `_ocr_page`):
- **Found in the page image:** straight rules (an opening, as for a table's rules, but short) that close off a small square, 0.6 to 1.2 of a line's box height; each side a rule along 90% of it, its rules meeting at the corners; an inside of a third of the box at least; and clear paper a tenth of its side to its left and right. Each threshold is set from the contract: its boxes against the look-alikes the finder took before each was added.
- **Ticked** when ink covers 15% of the inside clear of the rules or more (the contract's ticks: 21 to 35%), **empty** at 1% or less (all its empty boxes: 0), and **ticked, uncertain** between. More than half is a block within a square, as at a QR code's corners (59 to 71%), and no box.
- **In the text:** each box is one more box of text, ☒ or ☐, so it follows the existing path into lines, cells and both outputs. The engine's own short reading of it ("V", "√") gives way. Where the engine took the box into the text around it, its text is cut where a word starts (PyThaiNLP's tokenizer, as the word list uses), or at its start or end, nearest the share of characters left of the box; so "☒ โครงการเดี่ยว" and "☐ ใหญ่ ☒ กลางและย่อม (SME) ☐ เริ่มต้น" come out in order, though the engine boxed a box with its choice.

**Look-alikes ruled out, each by one of the rules above, on the contract:** bold letters of a "confidential" header on every page (inside too small), a footer's "o" and "p" (too small), a certificate's printed pattern (sides not whole), a QR code's corners (a block inside), a bold "0" in "ภ.พ.20" and a logo's "D" (ink beside them); on the five-page agreement, the "o" of a large typed name (ink beside it). After the rules: 46 boxes found on the contract, every one a box, checked against the page images; none on the other two samples.

**Tests** (`tests/test_check_boxes.py`, through `convert()` with `FakeEngine` on scans): a form's ticked and empty boxes before their choices; boxes in a ruled table's cells; a speck, ticked and uncertain; the engine's "V" giving way; a box taken into the text around it; DOCX; and look-alikes: square letters and a QR corner, a row of digit boxes.

**Corpus:** `check-box-scans`, a form of choices and a rights table on scans. With real PaddleOCR, CER 0.113 → 0.008 and 0.148 → 0.000, every box right.

**The samples,** converted on this machine with the user's standing permission: on the 110-page contract (replayed from ticket 37's recorded boxes), the proposal form, the company size row, the IP status list, the rights annex and the in-cash and in-kind choices now show which were ticked; the five-page agreement and the GIZ supplement come out as before.

**Left:**
- A box drawn touching a table's rules joins them and is not found; none on the samples.
- A hand tick that runs out over the box's edge into the text beside it may fail the clear-paper rule; the samples' ticks are typed glyphs.
- Which box goes with which choice is left to where it sits: a box after its choice, as some forms set them, comes out after it.

**The known limitation** is dropped; the release that deploys this lists the fix.

**2026-11-04, after code review**

**Fixed, each with a test:**
- **Digits written a digit to a box were lost,** their boxes taken for ticked check boxes and the digits dropped as the engine's reading of them. A box the engine reads a digit or a letter in is now no check box, and its character stays; only a tick ("V", "√", "✓", "x") or nothing gives way. Boxes three or more in a row, each less than its side from the next, are a row of character boxes too.
- **Text close to a box made it vanish:** the clear paper beside a box is now a tenth of its side, not a fifth. On the contract the look-alikes still had ink there (0.16 and 0.98), and its boxes none. Text closer than about a tenth of the box, after a scan's blur, can still hide it.
- **A tick the engine read into the text beside its box** ("√วิสาหกิจ") is left out of that text.
- **A box with no word start near it in the text the engine took it into** came out after the text, unmarked; it is now uncertain text.
- **Tidied:** the module is `check_boxes.py`, as the glossary spells it; ink thresholds and check-box confidences have names apart from the glyphs and from `<mark>`, the unsure one tied to `LOW_CONFIDENCE`; each new constant in `ocr.py` says where it comes from; the generator takes ☒ and ☐ from the module; the builder exports the kinds of mark; the tests share one form.

**Also checked:** a box on a page drawn as shapes, sideways and upside-down scans, grain and skew, a grid of small empty cells (the reviewer's probes, and a test for the drawn page). The three samples and the corpus file come out as recorded above.

**Left, recorded:** a hand tick that runs out over the box's edge breaks its sides or corners, and the box is not found, silently; a box filled in solid is taken for a QR code's corner. The samples' ticks are typed glyphs.
