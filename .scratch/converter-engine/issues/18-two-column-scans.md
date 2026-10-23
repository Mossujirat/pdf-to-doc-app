# 18: Two-column scans are read across their columns

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On an OCR page set in two columns, each output line joins a line of the left column to the line beside it in the right column. Sentences from the two columns interleave, and the text cannot be read. This is broken text (wrong reading order). None of it is marked uncertain, because every word in it is a real word, so the summary does not warn about it either.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a scanned contract supplement among the local samples in `docs/example_pdf/`. It was converted on 2026-10-22 and 2026-10-23 with the user's permission, while grilling the kept-images feature, and every page was checked against its image. The same fault hits any text set side by side:
- six two-column pages of standard terms and conditions;
- a letter whose right edge holds a narrow panel of the sender's offices, registry and bank details, joined line by line with the letter's body;
- a signing page with three signature blocks side by side.

The single-column pages of the same file read in order.

A five-page agreement printed to PDF shows the same fault. Its text is drawn as shapes, so its pages are OCR pages, though none is a scan:
- Its bank details sit beside its list of signatories, and the account number landed in the signatory's text, away from its label.
- On its signing page, the two signers' titles came out joined line by line, the right-hand signer's first. A reader could match a name to the wrong title.

A 110-page Thai contract with scans pasted into Word pages shows it again, in these layouts:
- diagrams whose boxes sit in columns;
- captions of two figures side by side;
- signature blocks beside a company stamp;
- a notice box beside a QR code;
- handwritten initials in a margin, joined into the item beside them.

**Where to look:** `ocr_page` in `ocr.py` groups the engine's boxes into lines by height across the whole page width. The spec's open questions already list multi-column layouts as not yet tried.

**To decide at triage**
- Whether OCR pages should find columns, for example from a vertical gutter with no boxes in it, and read each column top to bottom.
- Whether text pages need the same, or PyMuPDF's block order already covers them.
- A synthetic two-column scan for the corpus, so that the harness measures reading order.
