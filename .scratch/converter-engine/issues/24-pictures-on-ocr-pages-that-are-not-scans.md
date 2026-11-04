# 24: Pictures on OCR pages that are not scans

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A page whose text is drawn as shapes is an OCR page, but it is not a scan. Its pictures are separate images in the PDF, as on a text page: signatures, initials, logos. The spec gives OCR pages no placeholders, on the grounds that they are images themselves. So these pictures are not turned into placeholders, and OCR reads them instead:
- Handwritten initials at the foot of every page came out as nonsense words.
- A signature came out as two letters.

Both are marked uncertain, so nothing false is passed off as certain. But the Markdown never says the document was signed. The initials, the same image at the same place on every page, are not dropped as page furniture either.

**Blocked by:** none

**Status:** ready-for-agent

**Seen on:** a five-page agreement among the local samples in `docs/example_pdf/`, printed to PDF with its text drawn as shapes, converted on 2026-10-23 with the user's permission. Every page carries the same initials at its foot, and the last page carries two signatures, one beside an electronic signing stamp.

**The same question inside scans.** A 110-page Thai contract among the same samples was converted on 2026-10-23 with the user's permission. On its 91 OCR pages, signatures, stamps, logos, QR codes and photos inside the scans came out as junk text or vanished. No placeholder appears on any of those pages, and its only placeholders are on two text pages. That follows the spec, but it means the Markdown of a signed contract never says it was signed. Finding pictures inside a page image takes image analysis, unlike the separate images above. It may belong in a ticket of its own.

**To decide at triage**
- **Tell such a page from a scan.** A scan's picture covers the page body. These pictures are small.
- **Treat their pictures as pictures on a text page are treated:**
  - they become signature, stamp or image placeholders by the same rules;
  - repeated edge images are dropped as page furniture;
  - they are blanked out of the page image before OCR reads it, so that their ink is not read as text.
- **How this meets kept images (the next feature).** There, pictures on text pages are shown as themselves in DOCX, and pages whose text is drawn as shapes are still read with OCR. Their pictures could be shown as themselves too.

## Comments

**2026-10-30, triage**

- **After the next deploy:** the user chose to leave it for a later version. See `.scratch/next-deploy.md`.
- Status stays `needs-triage` until then.

**2026-11-03, triage**

- **In this round,** with 37, 26 and 32.
- **Pictures inside scans split out** as ticket 38. This ticket keeps the separate images on OCR pages that are not scans.
- **The known limitation on the what's-new page** speaks of scans, which is ticket 38's part. When this ticket closes, the limitation stays for 38, reworded if need be, and the release says only what this ticket fixed.
- **Scope:**
  - **Their pictures are treated as on a text page:** signature, stamp or image placeholders by the same rules, and repeated edge images dropped as page furniture. The images are already collected for every page; `_ocr_page` drops them when it returns its rows. On a sideways page their boxes must be turned with the page.
  - **Hidden before OCR reads the page:** hide the image itself rather than paint a white box over it, so that drawn text over a picture, such as a signing line under a signature, is still read. Check whether initials repeated on every page are one image shared by all pages.
  - **Telling such a page from a scan, in scope:** a scan's picture covers the page body. Today a signing page with little text and several pictures can be judged a scan, because its pictures hold most of the ink, and it would get no placeholders. Several small pictures do not make a scan. Check that real scans are still judged scans.
  - **Kept images:** their pictures are shown as themselves in DOCX, as on a text page. The kept-images spec left this to this ticket.
  - **The converter-engine spec** says OCR pages get no placeholders; it changes to say scans get none.
- **Accepted:** the signature rule looks for "ลงชื่อ" or "Signature" beside the picture. On these pages that word comes from OCR, so a misread gives an image placeholder in place of a signature one. It still tells the reader something is there.
- **Corpus:** `text-drawn-as-shapes` holds no pictures. New pages: a signing page, and pages with initials at the foot. The builder drops a stamp's soft mask when it draws a page as shapes, so pictures must be inserted after the shapes.
- **Estimate:** small to medium, about 50–100 lines in `ocr.py` and `reading.py`, plus tests, corpus pages and a check on the five-page sample.
