# 19: Text laid over a rotated scan comes out twice, and other text is lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On a scan turned upright by a page rotation, text laid over it in the text layer, such as a typed note, causes two faults:
- **The note comes out twice.** It is kept from the text layer, as the spec intends, but OCR reads it off the page image as well. The OCR copy carries misread marks and uncertain text.
- **Other lines of the page are lost.** On one page with two notes, about ten lines of the body were missing from the output, a heading among them. They lay in the band one note's box covers when its unrotated position is read as a position on the rotated page. Nothing marks them as uncertain, and the summary does not show the loss.

**Blocked by:** none

**Status:** done

**Seen on:** a scanned contract supplement among the local samples in `docs/example_pdf/`, converted on 2026-10-22 and again on 2026-10-23 with the user's permission. The output was the same both times. Every page of it is stored landscape and turned upright by a page rotation of 270°. Five pages carry typed notes:
- On all five, each note came out twice.
- On four of them, OCR lines were lost: about ten lines on one page, three list items on another, four paragraphs on a third, and two lines on the fourth.
- **The lost lines sit where the unrotated box predicts.** On one page the note's unrotated box spans 298–369 pt from the top. The lost lines, measured on the page as shown, lay between 295 and 367 pt.

**Likely cause (not yet confirmed):**
- No code in `src/` handles page rotation.
- PyMuPDF gives text-layer positions on the unrotated page, but `render` draws the page as it is shown, rotated.
- `ocr_page` drops engine boxes that overlap the rows it keeps. On a rotated page the two sets of positions do not line up:
  - the boxes over the note itself are not dropped, so the note comes out twice;
  - boxes of other lines, which lie where the note's unrotated box falls, are dropped, so those lines are lost.
- `_ink_beyond_text` in `reading.py` blanks the text rows on the rendered page in the same way, so the page classifier may also be measuring the wrong areas on rotated pages.

**To do**
- Confirm the cause on a synthetic scan rotated by 90° and by 270°, with a note over it.
- If confirmed, bring the text layer's positions into the rendered page's frame before comparing them. Check text pages that are rotated too: the rows they make should read in order.

## Comments

**2026-10-23, diagnosed and fixed on branch `fix/rotated-scans` (not committed yet)**

- **Cause, confirmed.**
  - `text_rows` read the text layer with `page.get_text`. That gives positions on the page as stored, before its /Rotate turns it upright.
  - `page.rect`, `render` and PyMuPDF's table finder all work on the page as shown.
  - On a synthetic scan turned by 270°, a note shown at x 72–257, y 413–434 pt came back at x 408–429, y 72–257, its x and y swapped. `ocr_page` then dropped the engine boxes under that misplaced box, which lost those lines, and kept the boxes over the note itself, which gave the second copy.
  - Ruled out: layout losing the lines (they were already gone from `ocr_page`'s rows), the image scale (72/300 at every rotation), and an untrusted text layer.
- **Wider than OCR pages.** Every position taken from the text layer had the same fault, so rotated text pages broke as well:
  - page furniture was kept;
  - rows ran together or split apart;
  - words landed in the wrong table cells;
  - a 270° text page with a short body went to OCR. Every row seemed to sit in the top edge band, and `_ink_beyond_text` blanked the wrong areas.
- **Fix, at the source only.**
  - `text_rows` now builds its text page with `matrix=page.rotation_matrix` and `clip=page.rect`, so MuPDF gives every character, line and image block on the page as shown. Nothing downstream changed.
  - The clip is needed: without it, MuPDF clips to the stored page's box, and text more than 595 pt down a turned page is lost. A rotated test page has a line at 700 pt, so the tests fail without the clip.
  - Checked at 90°, 180° and 270°, and on a rotated page with a cropbox: each row sits on its ink in the render.
  - Unrotated pages are read as before: the existing corpus gives the same results.
- **Impact checked on rotated pages:**
  - OCR pages: the note comes out once, in its place in reading order, and no line is lost.
  - Page classification: `body_text_share` and `_ink_beyond_text` on a rotated page now equal the upright page's. A short text page that used to go to OCR at 270° stays a text page.
  - Text pages: with headings, paragraphs, a list, page furniture at both edges, a ruled table, a signature on its signature line and a stamp, a rotated page's Markdown equals the upright page's.
- **Tests and corpus.**
  - `pdf_builder.Rotated` builds a page stored landscape and turned upright by /Rotate 90 or 270. Its scan image is stored on its side, and its text is written turned, as a PDF editor writes a note. It renders the same as the upright page.
  - Fast tests: a rotated scan with a note, read by `FakeEngine` (`test_ocr_pages.py`), and rotated text pages compared with upright ones (`test_text_pages.py`).
  - New corpus documents: `rotated-scans`, at 270° and 90°, each with a note placed so that its unrotated box lies over lines of the scan, and `rotated-text-pages`.
    - Read the old way, these four pages scored CER 0.77–1.35 with missing text. Now the scans score 0.0034 and 0.0035, and the text pages 0.
    - On the 90° scan the body starts at 300 pt. At 360 pt, PaddleOCR read stray characters before two lines, upright as well, so that is not this ticket's fault.
  - `pytest -m ocr`: with PaddleOCR, each note on the rotated scans comes out once and the pages stay within the OCR CER limit.
  - pytest, mypy, `pytest -m ocr`, the harness with `--max-broken 0`, and CI's conversion steps all pass, on Windows and in the Linux image.
- **The sample supplement.** It was converted again on this machine with the user's permission, and the output was not kept. Only counts were looked at.
  - All 34 pages are turned by 270°.
  - On pages 3, 10, 11 and 17, the old reading dropped 16, 7, 11 and 2 OCR boxes that were not notes. Now only the boxes that read the notes themselves are dropped, and every note comes out once.
  - The only OCR boxes still missing from those pages are one or two per page, 42–68 pt from the top. They come back when page furniture is not removed, so they are rows removed as page furniture, as the spec intends. Their text was not looked at.
- **For ticket 22:** the rows OCR reads were already placed on the page as shown, so their edge bands have not changed. Only text-layer rows over rotated scans have moved.
