# 04: Initials at the foot of scans are page furniture

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decision 4 of its comment of 2026-11-12.

**What to build:** Initials put at the foot of each scanned page are left out of both outputs as page furniture, with the junk OCR read in them, as they already are on OCR pages that are not scans. Today they come out as junk marked uncertain on nearly every page of a scanned contract.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/pictures-inside-scans`

- [ ] **Pictures at the same edge of two or more scans** are page furniture, as images are on text pages.
- [ ] **Matching handwritten initials.** Initials differ a little in size and place from page to page, unlike a printed logo.
  - Measure how much on the samples, as numbers only, on this machine.
  - Loosen the match for pictures found in scans only as far as that needs.
  - The rule for text pages and for OCR pages that are not scans stays as it is.
- [ ] **The junk goes with them:** text OCR read in a furniture picture, sure or not, and rows that hold nothing OCR is sure of and touch it, such as a row of dots or a stray letter under the initials.
- [ ] **What stays:**
  - a picture at the foot of one page only, such as a full signature, stays a placeholder;
  - a printed footer beside the initials is still found as ticket 22 finds it.

**Tests**
- [ ] Fast tests through the conversion function, with a fake finder:
  - three scans initialled at the foot, each set a little different in size and place, give no placeholder and no junk;
  - a signature at the foot of one scan stays `[ลายเซ็น]`;
  - text pages initialled at the foot give what they give today.
- [ ] **Checked by breaking the code on purpose:** the looser match and dropping the junk rows each have a test that fails without them.
- [ ] Record in Comments what junk is left on the samples, as numbers only, for ticket 44's grilling.
- [ ] Run pytest and mypy.
