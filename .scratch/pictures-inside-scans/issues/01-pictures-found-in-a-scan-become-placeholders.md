# 01: Pictures found in a scan become placeholders

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`). Its comment of 2026-11-12 holds the decisions and measurements this feature follows.

**What to build:** A signature, a stamp or a picture inside a scan comes out as a placeholder in both outputs, in its place in the reading order. The Markdown of a signed scan then says it was signed. The junk OCR read in the picture goes with it, so a signer's printed name beside a signature is no longer garbled. Today the picture is lost, or comes out as junk marked uncertain.

This ticket cuts the whole path with a picture finder that tests can fake. Ticket 02 plugs in the real model.

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/pictures-inside-scans`

**The picture finder**
- [x] **An interface of its own,** as the OCR engine has one. Given a page image, it returns the regions it found, each with a box and its class: "image", "chart" or "seal".
- [x] **Loaded only when a scan needs it,** once per conversion, and dropped when the conversion ends, as the engine is.
- [x] **Scans only.** It never runs on:
  - text pages;
  - OCR pages that are not scans, which keep ticket 24's pictures;
  - kept pages: with images kept, nothing changes.
- [x] **It reads the image OCR read last,** after any sideways or upside-down turn, so its regions lie in the same frame as the engine's boxes.

**From region to placeholder**
- [x] Each region becomes a picture on the page, in PDF points, as a text page's pictures are.
- [x] **The kind follows ticket 24's rules,** with nothing new:
  - a ring in colour is a stamp, `[ตราประทับ]`;
  - a small picture beside a row to sign on is a signature, `[ลายเซ็น]`;
  - anything else is an image, `[รูปภาพ]`.

  A region of class "seal" goes through the same rules.
- [x] **A ring in colour is judged from the region's pixels,** since a scan has no image of its own to look at. It must give the same answer as today's test on a PDF image for the same ring.
- [x] **Placed by its top,** as pictures on a text page are.
- [x] The summary counts these placeholders like any other.

**Text inside a picture's region**
- [x] **Text OCR read surely stays,** such as a signer's name printed under a signature.
- [x] **Text it is unsure of, and junk, is dropped.** The placeholder stands in its place.
- [x] **Text-layer rows over a scan stay as they are,** such as a typed note or a stamped header.

**Tests**
- [x] **A fake finder,** returning regions where the PDF builder draws pictures. The page image comes from the real PDF, so a stamp's ring is really there.
- [x] Fast tests through the conversion function, on scans:
  - a signature beside a row to sign on gives `[ลายเซ็น]`, and the signer's name under it reads as printed;
  - a red ring gives `[ตราประทับ]`;
  - a logo or photo gives `[รูปภาพ]`;
  - junk read inside a region is gone, and text read surely there stays;
  - the placeholder sits between the paragraphs above and below it.
- [x] Unchanged:
  - a text page with pictures, and an OCR page that is not a scan, both give what they give today;
  - with images kept, the finder is never called.
- [x] No test or corpus text is copied from the sample contracts. Write your own.
- [x] **Checked by breaking the code on purpose.** Each part has a test that fails without it:
  - the frame after a turn;
  - judging a ring from pixels;
  - keeping sure text;
  - dropping junk;
  - scans only.
- [x] Run pytest and mypy.

## Comments

**2026-11-12, implemented on branch `feat/pictures-inside-scans`**

- **The finder:**
  - **Where it lives:** `pictures.py` holds `PictureFinder`, `FoundPicture` (a box in the image's pixels, and the model's label) and `NoPictures`.
  - **Who passes it in:** `convert` takes `pictures=`, and `read_pdf` takes a factory for it, as it does for the engine. It is called once, at the first scan read with OCR.
  - **What it reads:** `read_page` asks it about the image the engine read last, after `_read_upright`, so after any sideways or upside-down turn.
  - **Pages that are not scans:** they pass no finder.
  - **The default** is `NoPictures`, until ticket 02, so production output does not change yet.
- **A region becomes a picture** in `ocr._scan_picture`. Its box is kept within the image and turned into points by the same scale as the rows.
  - **Too small:** a region whose shorter side is under 8 points is no picture, as on a text page (`pictures.a_picture`, shared with `pdf_images`).
  - **The label is not used:** ticket 24's placeholder rules decide the kind, so "chart" and "seal" go through the same rules as "image".
- **A ring in colour:**
  - **Shared test:** `ring_in_colour` moved from `pdf_images` to `pictures.py`, unchanged, so PDF images and scans share one test.
  - **On a scan,** every pixel of the region counts. The paper around the ring is not ink, as on an opaque PDF image.
- **What "surely" means:** confidence of at least `LOW_CONFIDENCE` (0.85), the same bar ticket 22 uses for page furniture.
  - **The engine's boxes that are dropped:** those centred in a picture and read below that bar. This happens before the text layer is compared with the engine's reading, so junk never takes the place of a typed note.
  - **Junk read surely stays.** A stricter test, counting words outside the word list as well, would drop signers' names, which are seldom in it. What stays is still marked uncertain when it is not a word. Ticket 05 measures on the samples how much such junk is left.
- **Test support:**
  - **Colour scans:** `pdf_builder.Scan` has `colour`, and stays grey by default. `corpus/generate.py` regenerates the corpus byte for byte the same.
  - **The fake finder:** `fake_ocr.FakePictures` finds each `Picture` where the builder draws it. On a sideways or upside-down page, it finds them turned the way the engine reads them, so a finder asked about the wrong image finds them out of place.
- **Tests:** `test_pictures_in_scans.py` holds 15 fast tests through `convert`:
  - a signature beside a row to sign on, a red ring, a photo between two paragraphs, a pie chart labelled "chart" (only an image), and a thin rule (no placeholder);
  - junk dropped;
  - the signer's name under the row to sign on reads as printed;
  - text read surely inside a signature stays;
  - a note typed over a signature stays when junk read there holds fewer unknown words;
  - a signature on a sideways scan, each way, and on an upside-down scan;
  - the finder never asked about a text page or a page drawn as shapes, nor with images kept, and asked once a scan.
- **Checked by breaking the code on purpose:**

  | Broken | Tests that fail |
  | --- | --- |
  | the finder asked about the image before any turn | 3, the sideways and upside-down scans |
  | no ring judged from pixels | 1, the red ring |
  | sure text dropped too | 1 |
  | junk kept | 3: junk, the signer's name, the note |
  | junk dropped after the text layer is compared | 1, the note |
  | no smallest picture | 1, the thin rule |
  | the finder asked on every OCR page | 1, the page drawn as shapes |

**2026-11-12, after code review (two axes)**

- **Spec found a real fault:** a text-layer row typed over a picture could be lost.
  - The engine's reading of its place took its place when it held fewer unknown words, and was then dropped as junk.
  - Junk is now dropped first. The new note test fails with the old order.
- **Spec also found:**
  - no test of the signer's name under the row to sign on;
  - no test of an upside-down scan;
  - no test of the smallest picture.

  All three were added.
- **Spec noted:** pictures at the same edge of two or more scans are already page furniture, because `remove_page_furniture` treats them as it treats a text page's. Ticket 04 still has to measure and loosen the match for handwritten initials.
- **Standards: no written rule broken. Fixed:**
  - `a_picture` is shared, not written twice;
  - the model's label is `FoundPicture.label` (`PictureLabel`), with "seal" explained as its word for a stamp, so it is not confused with a builder `Picture`'s kind;
  - `ring_in_colour`'s mask is optional, so a scan's region needs none;
  - `fake_ocr._layout` is renamed `_laid_out_with_pictures`;
  - the tests share `SIGNING_PAGE` and `SIGNED_PAGE`;
  - a broken sentence in `FakePictures`' docstring is fixed.
- **Standards, left as they are:**
  - "picture finder" is not in GLOSSARY.md: it is a name in the code, not a word readers use;
  - `None` for "not a scan" in `read_page`, beside `NoPictures` for "finds none";
  - `pictures.py` holds both the finder and the stamp test, both about pictures.
