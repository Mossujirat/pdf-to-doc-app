# 03: Coloured ink beside a row to sign on is a signature

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decision 2 of its comment of 2026-11-12.

**What to build:** A signature the layout model misses still gets a placeholder when it is in coloured ink beside a row to sign on. Grilling found that the model missed some full signatures, while every scan in the samples is in colour and signatures are mostly in blue pen.

**Blocked by:** 01, and 02 for the signing scan in the corpus, whose photo and stamp the layout model finds

**Status:** ready-for-agent

**Branch:** `feat/pictures-inside-scans`

**Finding the ink**
- [ ] **Coloured ink:** pixels clearly coloured, not black, grey or paper, in regions large enough to be a mark, not a speck. Grilling used regions of 1,500 pixels or more at 150 dpi.
- [ ] **Highlights are not ink.** A region whose paper is mostly bright colour, a share of 0.3 or more, is a highlight and is dropped. During grilling, bright meant a channel above 0.85 with saturation above 0.15, and the user checked that what this dropped was right to drop.
- [ ] **Only beside a row to sign on,** a row `SIGNATURE_LINE` matches, as near as ticket 24 counts a signature beside one. Text printed in colour elsewhere on the page, as on a contract's first page, is never looked at.
- [ ] **Not twice:** ink that lies in a picture the finder already found adds nothing.

**What it becomes**
- [ ] A picture on the page, so that ticket 24's rules give its kind, as in ticket 01: a small one is `[ลายเซ็น]`, and a ring in colour is `[ตราประทับ]`.
- [ ] Junk OCR read in it goes, and sure text stays, as in ticket 01.

**Tests**
- [ ] Fast tests through the conversion function, with a fake finder that finds nothing:
  - a blue signature beside a row to sign on gives `[ลายเซ็น]`;
  - a highlighted row to sign on gives no placeholder;
  - a heading printed in colour away from any row to sign on gives none;
  - a signature the finder already found gives one placeholder, not two.
- [ ] **Checked by breaking the code on purpose:** the highlight filter, the signing-row limit, and the overlap with found pictures each have a test that fails without them.
- [ ] **Measured on the samples,** on this machine only and as numbers only: how many signatures this adds beyond the model's, and how many it adds wrongly. Delete the outputs afterwards.
- [ ] **A signing scan in the corpus,** moved here from ticket 02 (see below):
  - a signing page scanned in colour, with reference text, holding a photo, a blue signature whose foot runs down to the signer's name, and a red stamp;
  - real-OCR tests (`pytest -m ocr`): it gives `[รูปภาพ]`, `[ลายเซ็น]` and `[ตราประทับ]` where its reference has them, and passes the corpus's CER bound for OCR pages;
  - the corpus's existing files do not change;
  - record the new document's figures in Comments.
- [ ] Run pytest, mypy, `pytest -m ocr` and the harness.

## Comments

**2026-11-12, from ticket 02**

- **The layout model misses a signature that touches its row:** PP-DocLayout_plus-L found no region at all on a synthetic colour scan where the signature's foot runs down to the signer's name, as `pictures-on-drawn-pages` draws it.
- **A signature a blank line above its row** it did find, as "image". But its box hugs the ink, 29 points tall where the drawn picture is 45. That left it 16.4 points from the row, more than the row's 14.7, so ticket 24's rules gave `[รูปภาพ]`.
- **The user chose to move the corpus's signing scan here,** where coloured ink beside the row finds the signature. A gradient box drawn as a logo at the page's head was found by no model region either, so it was left out: real logos are measured on the samples in ticket 05.
