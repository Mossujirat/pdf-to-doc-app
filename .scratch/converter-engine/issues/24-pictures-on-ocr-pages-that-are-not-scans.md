# 24: Pictures on OCR pages that are not scans

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A page whose text is drawn as shapes is an OCR page, but it is not a scan. Its pictures are separate images in the PDF, as on a text page: signatures, initials, logos. The spec gives OCR pages no placeholders, on the grounds that they are images themselves. So these pictures are not turned into placeholders, and OCR reads them instead:
- Handwritten initials at the foot of every page came out as nonsense words.
- A signature came out as two letters.

Both are marked uncertain, so nothing false is passed off as certain. But the Markdown never says the document was signed. The initials, the same image at the same place on every page, are not dropped as page furniture either.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a five-page agreement among the local samples in `docs/example_pdf/`, printed to PDF with its text drawn as shapes, converted on 2026-10-23 with the user's permission. Every page carries the same initials at its foot, and the last page carries two signatures, one beside an electronic signing stamp.

**The same question inside scans.** A 110-page Thai contract among the same samples was converted on 2026-10-23 with the user's permission. On its 91 OCR pages, signatures, stamps, logos, QR codes and photos inside the scans came out as junk text or vanished. No placeholder appears on any of those pages, and its only placeholders are on two text pages. That follows the spec, but it means the Markdown of a signed contract never says it was signed. Finding pictures inside a page image takes image analysis, unlike the separate images above. It may belong in a ticket of its own.

**To decide at triage**
- **Tell such a page from a scan.** A scan's picture covers the page body. These pictures are small.
- **Treat their pictures as pictures on a text page are treated:**
  - they become signature, stamp or image placeholders by the same rules;
  - repeated edge images are dropped as page furniture;
  - they are blanked out of the page image before OCR reads it, so that their ink is not read as text.
- **How this meets kept images (the next feature).** There, pictures on text pages are shown as themselves in DOCX, and pages whose text is drawn as shapes are still read with OCR. Their pictures could be shown as themselves too.
