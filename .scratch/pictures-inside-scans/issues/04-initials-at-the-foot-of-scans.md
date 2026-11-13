# 04: Initials at the foot of scans are page furniture

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decision 4 of its comment of 2026-11-12.

**What to build:** Initials put at the foot of each scanned page are left out of both outputs as page furniture, with the junk OCR read in them, as they already are on OCR pages that are not scans. Today they come out as junk marked uncertain on nearly every page of a scanned contract.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/pictures-inside-scans`

- [x] **Pictures at the same edge of two or more scans** are page furniture, as images are on text pages.
- [x] **Matching handwritten initials.** Initials differ a little in size and place from page to page, unlike a printed logo.
  - Measure how much on the samples, as numbers only, on this machine.
  - Loosen the match for pictures found in scans only as far as that needs.
  - The rule for text pages and for OCR pages that are not scans stays as it is.
- [x] **The junk goes with them:** text OCR read in a furniture picture, sure or not, and rows that hold nothing OCR is sure of and touch it, such as a row of dots or a stray letter under the initials.
- [x] **What stays:**
  - a picture at the foot of one page only, such as a full signature, stays a placeholder;
  - a printed footer beside the initials is still found as ticket 22 finds it.

**Tests**
- [x] Fast tests through the conversion function, with a fake finder:
  - three scans initialled at the foot, each set a little different in size and place, give no placeholder and no junk;
  - a signature at the foot of one scan stays `[ลายเซ็น]`;
  - text pages initialled at the foot give what they give today.
- [x] **Checked by breaking the code on purpose:** the looser match and dropping the junk rows each have a test that fails without them.
- [x] Record in Comments what junk is left on the samples, as numbers only, for ticket 44's grilling.
- [x] Run pytest and mypy.

## Comments

**2026-11-13, implemented on branch `feat/pictures-inside-scans`**

- **The match needed no loosening.** The samples were measured on this machine, as numbers only, with OCR and the layout model cached, and the outputs deleted afterwards.
  - **The 10-page contract:** the layout model found the initials at the foot of 7 pages as one region each, both sets together.
    - **Sizes:** 166–173 points wide, within 4% of each other, and 47–52 tall, within 10%.
    - **Places:** their centres lay within 6 points across and 5 points down.
    - **The rule already allows** 20% in size and 36 points in place (`_SAME_IMAGE_SIZE`, `_SAME_IMAGE_PLACE`), so it took all 7 for page furniture, as ticket 01's review had expected.
  - **The other samples:** the model found no picture at the edge of any scan.
- **The junk:** `layout.remove_page_furniture` now drops, beside a picture found in a scan that is page furniture:
  - **Rows whose middle lies in it,** however surely OCR read them. Their text is what OCR read in its ink.
  - **Rows OCR is sure of nothing in,** no letter or digit, that lie beside it, as `next_to` counts a signature beside a row.
  - **Beside such a picture on any page,** not only on the row's own. On the 10-page contract, the model missed the initials on one page and left a letter OCR was unsure of where they lay on the others.
- **Only pictures found in scans,** marked `PlacedImage.in_scan`. On a text page, a row typed over an image that repeats is exact text, and stays.
- **Tests:** `test_pictures_in_scans.py` gained 4 fast tests:
  - three scans initialled, each set a little different, with letters read surely in them and dots read unsurely under them;
  - a fourth page where the finder misses the initials;
  - a signature at the foot of one scan;
  - text pages initialled, with a word typed over each page's initials.
- **Checked by breaking the code on purpose:**

  | Broken | Tests that fail |
  | --- | --- |
  | rows whose middle lies in it kept | 2, the initialled scans |
  | rows sure of nothing beside it kept | 2, the initialled scans |
  | beside one on its own page only | 1, the page where the finder missed them |
  | applied to text pages too | 1, the text pages |

  - **The looser match** has no test of its own, since none was needed. The initialled scans' sets differ as much as the samples' do, and the rule as it stands matches them.
- **Junk left at the foot of the samples' scans,** for ticket 44's grilling:
  - **The 10-page contract:** none. Ticket 38's comment of 2026-11-11 had 5 junk rows on 4 pages.
    - The one change from ticket 03's output is one uncertain letter dropped at the foot of page 4.
  - **The 110-page contract:** 2 rows of 6 and 7 characters, all read unsurely, beside no picture found.
  - **The 34-page supplement:** a single letter at the same place on two pages, read surely on one and unsurely on the other, and a single letter on a landscape page.
    - No picture was found there.
    - Being one letter, they are too short for ticket 22's match by what OCR read.
  - **The other samples' outputs** are unchanged by this ticket.

**2026-11-13, after code review (two axes, with tickets 03 and 05)**

- **Spec found a real fault:** a text layer's row whose middle lay in the initials was dropped with what OCR read there, such as a note typed over them.
  - **The fix:** only rows OCR read go now. A text layer's text is exact, never junk.
  - **A new test** of a note typed over each scan's initials fails without the fix.
- **Spec: rows beside furniture on another page** go beyond "touch it". This is kept, from the sample page where the finder missed the initials.
- **Spec: no test of a printed footer beside the initials.** Ticket 22's own tests cover the footer. Here, only rows whose middle lies in the picture go, so a footer line running beside it stays. On the 10-page contract, nothing but one junk letter changed.
- **Standards:** the pictures found in scans are filtered once a page, no longer once a row.
