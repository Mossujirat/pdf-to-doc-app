# 30: Upside-down scans are read as nonsense

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A page scanned upside down is read line by line upside down, so its text comes out as junk. It is mostly marked uncertain, but nothing of the page can be used.

**Blocked by:** none

**Status:** ready-for-agent

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
