# 19: Text laid over a rotated scan comes out twice, and other text is lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On a scan turned upright by a page rotation, text laid over it in the text layer, such as a typed note, causes two faults:
- **The note comes out twice.** It is kept from the text layer, as the spec intends, but OCR reads it off the page image as well. The OCR copy carries misread marks and uncertain text.
- **Other lines of the page are lost.** On one page with two notes, about ten lines of the body were missing from the output, a heading among them. They lay in the band one note's box covers when its unrotated position is read as a position on the rotated page. Nothing marks them as uncertain, and the summary does not show the loss.

**Blocked by:** none

**Status:** needs-triage

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
