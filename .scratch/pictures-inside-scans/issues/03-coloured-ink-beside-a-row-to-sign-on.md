# 03: Coloured ink beside a row to sign on is a signature

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decision 2 of its comment of 2026-11-12.

**What to build:** A signature the layout model misses still gets a placeholder when it is in coloured ink beside a row to sign on. Grilling found that the model missed some full signatures, while every scan in the samples is in colour and signatures are mostly in blue pen.

**Blocked by:** 01

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
- [ ] Run pytest and mypy.
