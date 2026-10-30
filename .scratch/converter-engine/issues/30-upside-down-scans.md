# 30: Upside-down scans are read as nonsense

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A page scanned upside down is read line by line upside down, so its text comes out as junk. It is mostly marked uncertain, but nothing of the page can be used.

**Blocked by:** none

**Status:** done

**Seen on:** none of the local samples yet. Opened while grilling ticket 21 (2026-10-24), which turns only pages whose content is a quarter turn from the page.

**What is known so far** (measured on synthetic pages for ticket 21)
- **Ticket 21's sign does not show it.** That ticket finds sideways pages by their tall text boxes, and an upside-down page has wide ones.
- **PaddleOCR's document orientation classifier is unsafe as it stands.** `PP-LCNet_x1_0_doc_ori` is 6.9 MB and takes 15 ms a page.
  - It called 3 of 19 upright pages upside down, at scores of 0.25–0.52. It looks only at a square in the middle of the page, and those pages had little text there.
  - Cropping the page to its ink before classifying got all 23 pages right. An unoptimised crop took 0.26 s.
- **Text-line orientation turns single lines 0° or 180°.** It turned correct lines upside down on upright pages, so it is ruled out.
- **A cheaper sign may exist:** text read upside down has low confidence, and most of its words are not in the word list (a share of 0.75–1.00, against 0.08–0.15 for text read the right way up).

**To decide at triage**
- Whether this is worth doing before a sample shows it.
- How to find such a page: the confidence and word-list signs on what OCR already read, or the classifier on a page cropped to its ink.
- What it may cost on upright pages, which ticket 21 keeps at nothing.

## Comments

**2026-10-30, triage**

- **In the next deploy:** the user chose this ticket among the 6 to be done before it. See `.scratch/next-deploy.md`.
- **Next:** `/grill-with-docs`, then `/implement`.

**2026-10-30, grilling**

- **Measured with PaddleOCR** on 29 synthetic OCR pages, the 5 damaged scans and 130 real OCR pages, upright, and on 49 of them turned upside down (all synthetic and damaged, 15 real):

  | Pages | Per-character confidence |
  | --- | --- |
  | synthetic upright | 0.95–0.99 |
  | damaged scans upright | 0.96–0.98 |
  | real upright, with text | 0.872–0.98 (the lowest a run of poor scans in the 110-page contract) |
  | upside down, all sets | 0.42–0.749 |

  - The same page read both ways dropped by 0.225 or more.
  - **The word-list share is no sign:** upside-down Thai is read mostly as other characters, so 35 of 49 such pages had under 20 Thai words, and 12 none.
  - **Confirming on the widest or largest box,** read turned, missed 2–3 of 49: tables whose widest box is a short row.
  - **Turned back and read again,** all 34 synthetic and damaged pages gave the same Markdown as upright.
  - **Timings:** a page read takes 1.3–1.4 s on synthetic pages and 4.9 s on real ones (median; 26.9 s at most). A box read takes 0.18–0.48 of that.
- **Decided**
  - **Sign:** an OCR page whose reading holds at least 20 characters, at a per-character confidence under 0.80. Not the word-list share, and not PaddleOCR's orientation classifier.
  - **Confirm:** read the whole page turned a half turn. Keep that reading when it is 0.80 sure or more and at least 0.15 surer than the first; otherwise keep the first, whose text is marked uncertain as before. An upside-down page must be read again anyway, so confirming costs it nothing. An upright page that reads well costs nothing either: none read under 0.80.
  - **After the sideways check,** so a sideways page turned the wrong way is put right too.
  - **Whole pages only.** An upside-down stamp or line on an upright page stays as it is.
  - **Kept pages are not turned:** they show the page as it looks.
  - **Nothing in the output or summary** says that a page was turned, as for sideways pages.
  - **Tests:** through `convert` with the fake engine (upside down, upright but poorly read, little text), and an upside-down scan in `corpus/synthetic`, checked with real OCR.
- **Cost on the web:** a 110-page contract scanned upside down throughout reads in about 18 minutes instead of 9, within the 30-minute limit of a conversion.
- **Glossary:** "Upside-down page" added.

**2026-10-30, implemented**

- **Where:** `ocr.read_page` reads the page, turns it if sideways, then `_read_upright` reads it again turned round when it may be upside down, as decided.
- **Only pages whose text runs across the page are checked.** Code review found the case: a sideways page that `_sideways_turn` leaves as it is, read turned round, gives tall boxes that the engine reads surely, but in the wrong order and unmarked, where before they came out marked uncertain. Such a page is now left as it is. A page the sideways check turned reads across, so it is still checked.
- **Tests:**
  - in `tests/test_ocr_pages.py`, through `convert` with the fake engine's `UpsideDown` page: an upside-down page reads as upright; an upright page read surely is read once; one read unsurely either way is read twice and kept as read; one with little text is not turned; a note typed over an upside-down scan comes out once, under the table;
  - corpus: `upside-down-scans`, a ruled payment schedule and a page of clauses. With PaddleOCR they read at CER 0.017 and 0.008, against 0.89 and 1.0 before.
- **Not checked on the samples:** none of them is upside down. Their upright scans read at 0.87 or more, so none is read twice.
