# 03: Coloured ink beside a row to sign on is a signature

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decision 2 of its comment of 2026-11-12.

**What to build:** A signature the layout model misses still gets a placeholder when it is in coloured ink beside a row to sign on. Grilling found that the model missed some full signatures, while every scan in the samples is in colour and signatures are mostly in blue pen.

**Blocked by:** 01, and 02 for the signing scan in the corpus, whose photo and stamp the layout model finds

**Status:** done

**Branch:** `feat/pictures-inside-scans`

**Finding the ink**
- [x] **Coloured ink:** pixels clearly coloured, not black, grey or paper, in regions large enough to be a mark, not a speck. Grilling used regions of 1,500 pixels or more at 150 dpi.
- [x] **Highlights are not ink.** A region whose paper is mostly bright colour, a share of 0.3 or more, is a highlight and is dropped. During grilling, bright meant a channel above 0.85 with saturation above 0.15, and the user checked that what this dropped was right to drop.
- [x] **Only beside a row to sign on,** a row `SIGNATURE_LINE` matches, as near as ticket 24 counts a signature beside one. Text printed in colour elsewhere on the page, as on a contract's first page, is never looked at.
- [x] **Not twice:** ink that lies in a picture the finder already found adds nothing.

**What it becomes**
- [x] A picture on the page, so that ticket 24's rules give its kind, as in ticket 01: a small one is `[ลายเซ็น]`, and a ring in colour is `[ตราประทับ]`.
- [x] Junk OCR read in it goes, and sure text stays, as in ticket 01.

**Tests**
- [x] Fast tests through the conversion function, with a fake finder that finds nothing:
  - a blue signature beside a row to sign on gives `[ลายเซ็น]`;
  - a highlighted row to sign on gives no placeholder;
  - a heading printed in colour away from any row to sign on gives none;
  - a signature the finder already found gives one placeholder, not two.
- [x] **Checked by breaking the code on purpose:** the highlight filter, the signing-row limit, and the overlap with found pictures each have a test that fails without them.
- [x] **Measured on the samples,** on this machine only and as numbers only: how many signatures this adds beyond the model's, and how many it adds wrongly. Delete the outputs afterwards.
- [x] **A signing scan in the corpus,** moved here from ticket 02 (see below):
  - a signing page scanned in colour, with reference text, holding a photo, a blue signature whose foot runs down to the signer's name, and a red stamp;
  - real-OCR tests (`pytest -m ocr`): it gives `[รูปภาพ]`, `[ลายเซ็น]` and `[ตราประทับ]` where its reference has them, and passes the corpus's CER bound for OCR pages;
  - the corpus's existing files do not change;
  - record the new document's figures in Comments.
- [x] Run pytest, mypy, `pytest -m ocr` and the harness.

## Comments

**2026-11-12, from ticket 02**

- **The layout model misses a signature that touches its row:** PP-DocLayout_plus-L found no region at all on a synthetic colour scan where the signature's foot runs down to the signer's name, as `pictures-on-drawn-pages` draws it.
- **A signature a blank line above its row** it did find, as "image". But its box hugs the ink, 29 points tall where the drawn picture is 45. That left it 16.4 points from the row, more than the row's 14.7, so ticket 24's rules gave `[รูปภาพ]`.
- **The user chose to move the corpus's signing scan here,** where coloured ink beside the row finds the signature. A gradient box drawn as a logo at the page's head was found by no model region either, so it was left out: real logos are measured on the samples in ticket 05.

**2026-11-13, implemented on branch `feat/pictures-inside-scans`**

- **Finding the ink:** `pictures.coloured_ink` finds the marks, at 150 dpi as in grilling.
  - **A coloured pixel:** its brightest channel is 0.2 of white or more above its darkest. Scanned black print, its edges tinted by the JPEG, stays under that.
  - **One mark:** strokes within 3 points of each other are one mark.
  - **Not a speck:** 1,500 coloured pixels or more.
  - **A highlight:** a mark whose box is 0.3 or more bright colour.
- **Beside a row to sign on:** `ocr._ink_beside_rows_to_sign_on` looks only on scans, and only when a printed line the engine read matches `SIGNATURE_LINE`.
  - The line is set out as `_row` sets out a row, in pixels.
  - `layout.next_to` (renamed from `_next_to`) then judges it, so "beside" is ticket 24's own test.
- **Labels:** each mark is a `FoundPicture` labelled "ink".
  - `FoundAs` is the model's labels plus "ink".
  - `PictureLabel` still lists only the model's labels, which `paddle.py` filters by.
- **Not twice:** ink is dropped when half its box or more lies in a picture found that a placeholder stands for.
  - **Found on the samples:** on the 10-page contract's signing page, the layout model took the whole signature block for one image, rows of print and all. That is the page behind the text, so no placeholder stands for it.
  - **The first version** dropped the blue signature inside that image, so the page got nothing.
  - **The fix:** `_ocr_page` now takes the ink apart from the finder's pictures and checks it only against those that stand in. A test of a region found behind the text covers it.
- **Tests:** `test_pictures_in_scans.py` gained 6 fast tests with `NoPictures`:
  - a blue signature;
  - a red stamp beside a row;
  - a highlighted row;
  - a heading printed in colour;
  - one placeholder, not two;
  - a signature inside a region found behind the text.

  To draw them, `pdf_builder.Styled` gained `colour` and `highlight`.
- **Checked by breaking the code on purpose:**

  | Broken | Tests that fail |
  | --- | --- |
  | no highlight filter | 1, the highlighted row |
  | no signing-row limit | 1, the coloured heading |
  | no overlap with found pictures | 8, every scan whose signature the fake finder finds |
- **The corpus:** `pictures-in-scans` is the `pictures-on-drawn-pages` signing page, scanned in colour as the corpus's scans are (200 dpi, askew 0.4°, grain 6).
  - **Real OCR:** it gives `[รูปภาพ]`, `[ลายเซ็น]` and `[ตราประทับ]` as its reference does, at CER 0.0063 and Thai CER 0.0066. The signature is found by its ink; the model finds the photo and the stamp.
  - **The corpus's existing files** regenerate byte for byte the same.
  - **The harness:** on every existing document, every row is the same as at 87adacf. Only the totals change, by the new page.
  - **Checks run:** `pytest -m ocr` gave 32 passed. pytest and mypy pass.
- **On the samples,** on this machine, numbers only. OCR and the layout model were cached, and the outputs deleted afterwards.

  | File | Pages with a row to sign on | Ink marks beside one | Became `[ลายเซ็น]` |
  | --- | --- | --- | --- |
  | The 10-page contract | 1 | 1 | 1, the signing page, which had none before |
  | The 110-page contract | 6 (5 scans) | 1 | 0: three rows of print lie over it, so it is taken for the page behind them |
  | The 34-page supplement | 1 | 0: its signing page holds no coloured ink | 0 |
  | The 5-page agreement | 3, text pages | none looked for: not scans | — |

  - **Added wrongly:** none known. The one added placeholder goes on the contact sheets of ticket 05 for the user to check.
  - **Left to the new ticket in 05:** the supplement's signing page, signed in black or not at all.

**2026-11-13, after code review (two axes, with tickets 04 and 05)**

- **Spec: a row to sign on was matched box by box,** while page layout matches a row's whole text.
  - **Not a fault in practice:** `_row` joins boxes with a space. A signing word boxed in two, "ลง" and "ชื่อ", matches neither way.
  - **Changed anyway,** so that both tests read the same text: the ink is looked for beside rows that `_row` itself sets out, at one point a pixel. That also drops `_row_in_pixels`, which copied `_row`.
- **Spec: "not twice" checks ink only against pictures a placeholder stands for,** and ink under three rows of print or more gets none. Both are left as they are, from the sample page above, and ticket 47 takes the second.
- **Standards:**
  - **Constants:** `_IN_A_PICTURE`, `_INK_CHROMA`, `_INK_JOIN` and `_INK_PIXELS` now say where their values come from. Two say plainly that they were not measured.
  - **Names:** in `_ocr_page`, the list of found pictures is `scan_pictures`, no longer `in_scan`, the name of `PlacedImage`'s field.
  - **Left as they are:**
    - the triples of picture, place and whether it stands in, which are only used inside `_ocr_page`;
    - "row to sign on" missing from GLOSSARY.md: it is a name in the code, as `SIGNATURE_LINE`, not a word readers use.
- **The samples' outputs** are byte for byte the same after these changes.
