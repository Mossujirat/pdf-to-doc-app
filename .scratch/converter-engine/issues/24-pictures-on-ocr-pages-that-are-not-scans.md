# 24: Pictures on OCR pages that are not scans

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A page whose text is drawn as shapes is an OCR page, but it is not a scan. Its pictures are separate images in the PDF, as on a text page: signatures, initials, logos. The spec gives OCR pages no placeholders, on the grounds that they are images themselves. So these pictures are not turned into placeholders, and OCR reads them instead:
- Handwritten initials at the foot of every page came out as nonsense words.
- A signature came out as two letters.

Both are marked uncertain, so nothing false is passed off as certain. But the Markdown never says the document was signed. The initials, the same image at the same place on every page, are not dropped as page furniture either.

**Blocked by:** none

**Status:** done

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

**2026-11-04, built**

**What changed:**
- **A scan is a page whose ink lies in a picture of a page:** an image covering a quarter of the body or more holds at least half of what the body shows outside its text, or else pictures hold nearly all of it (98%), as a logo alone on a page. Before, any images holding half the ink made a scan, so a signing page drawn as shapes, whose photo, signature and stamp hold most of its ink, was one. On the three samples a scan's image covered 0.42 of its body at least, and a picture on a drawn page 0.01 at most; every sample page is judged as before.
- **An OCR page that is not a scan keeps its pictures,** turned with the page when it is read sideways. They become placeholders by the text page's rules, and repeated edge images page furniture. A scan's images are its picture of a page and are dropped, as before.
- **Its pictures are hidden from the image OCR reads.** The page is copied into a document of its own and each picture redacted there, images only (`pictures_hidden` in `pdf_images.py`), so what is drawn over a picture, such as a signing line, still shows. Images too small to be pictures, such as bullets, stay.
- **With images kept,** its pictures are shown as themselves, as on a text page.
- **The signing word may have lost its mai ek,** "ลงชือ": PaddleOCR read the corpus's signing line so. Not any mark: "ลงช่อง" ("in the box") must not count. This also serves text pages and ticket 32.
- **The test PDF builder** inserts a drawn page's pictures as images after the shapes, keeping their transparent ground; the fake engine lays out pictures as the builder does.
- **Specs:** the converter-engine spec now says scans get no placeholders, and the kept-images spec records the new scan test.

**Corpus:** `pictures-on-drawn-pages`, three pages drawn as shapes: the placeholders signing page, and two pages initialled at the foot. With real PaddleOCR:
- Before: the photo, signature and stamp read as junk ("525"), no placeholders, the initials as marked junk ("√r", "y").
- After: placeholders "[รูปภาพ]", "[ลายเซ็น]" and "[ตราประทับ]" in place, the initials gone. CER 0.0095 on the signing page and 0.004 on the others.
- The rest of `corpus/synthetic` reports as before.

**The samples,** converted on this machine with the user's standing permission:
- **The five-page agreement printed to PDF:** the initials at the foot of two pages, read as junk before ("Ahmod uKha"), are dropped as page furniture; the two signatures on the signing page, junk before, are "[รูปภาพ]": no signing word stands beside them, so they are images, as on a text page. Uncertain marks fell from 7 to 5. With images kept, its DOCX holds the two signatures, where it held none.
- **The 110-page contract's four budget pages** with an untrusted text layer, OCR pages that are not scans: the same output as before; their only images are 3-point marks, too small to be pictures.
- **Every page of the three samples** is judged a scan, or not, as before.

**The known limitation** on pictures in scans now stands for ticket 38 alone; its wording already speaks of scans only. A draft line for the release is in `.scratch/next-deploy-2026-11.md`.

**2026-11-04, after code review**

**Fixed:**
- **An inline image was not hidden:** deleting an image needs its xref, which an inline image lacks, so it became a placeholder and was still read as junk. Each picture's box is now redacted, images only, which hides inline images and image objects alike and keeps the drawings and text over them, on rotated pages too (checked on synthetic pages).
- **The signing page of the corpus file** had a line of 48 dots, which PaddleOCR reads as a dot or two (ticket 18): CER 0.17, over the corpus gate of 0.05. Its signing line now names the signer, "ลงชื่อ นายสมชาย ใจดี ผู้ให้ทุน", over which the signature lies.
- **One rule for what size of image is a picture,** shared by placing and hiding; the share 0.98 says where it comes from; the scan test is named `_in_a_picture_of_a_page`; the fake engine lays pictures out with the builder's own helper; the kept-images spec no longer says both that ticket 24 is out of scope and what it did.

**Answered:** the initials of the five-page agreement are a separate image on each page (xrefs 98, 15, 36, 41 and 59). Hiding works on a copy of each page anyway, so a shared image could not be hidden elsewhere.

**Left, recorded:**
- **No test reads a sideways or upside-down page drawn as shapes with pictures.** Its pictures' boxes turn with `turned_box`, as the rows OCR reads do.
- **With images kept, a picture on a sideways page drawn as shapes is not turned with it** in the DOCX: the box moves, the picture does not. No sample has one.
- **The signing word may lose its mai ek** ("ลงชือ"), a widening triage had not asked for: triage accepted an image placeholder in its place. PaddleOCR read the corpus's signing line so; it costs one optional mark in the rule, and serves text pages and ticket 32 too. For the user to keep or drop.
