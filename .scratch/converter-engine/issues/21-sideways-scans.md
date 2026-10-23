# 21: Scans printed sideways are read as nonsense

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A landscape table is often printed sideways on an upright page, such as a price schedule or a project timeline. On a scan, OCR reads such a page as if its lines ran across the page. The output then has three faults:
- The characters are garbled. Latin letters come out mirrored and mixed with Thai letters.
- The order is reversed. The table's totals come first and its title last.
- The table is lost.

Most of the text is marked uncertain, so the reader is warned, but nothing of the page can be used.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** two pages of a scanned contract supplement among the local samples in `docs/example_pdf/`, converted on 2026-10-22 and 2026-10-23 with the user's permission: a price schedule and a project timeline. The page itself is upright. Only its content is turned a quarter turn.

**More of it in a 110-page Thai contract** among the same samples. Its attachments are scans pasted into Word pages. It was converted on 2026-10-23 with the user's permission.
- **Ten pages were printed sideways,** and nothing of them survived:
  - five pages of a work plan and a budget;
  - a tax registration certificate;
  - four pages of a table of delegated powers.
- **Sideways column headers** inside upright tables also came out as marked junk.
- This is the largest loss of content in that file, so this ticket now weighs more than when it was opened.

**Where to look:** `paddle.py` turns off PaddleOCR's document orientation, unwarping and text-line orientation (`use_doc_orientation_classify`, `use_doc_unwarping`, `use_textline_orientation`), as the October 2026 benchmark chose. Nothing else turns a page's image before it is read.

**To decide at triage**
- How to find such a page. One way is PaddleOCR's orientation classifier, measured for its cost in time and its effect on the benchmark. Another is the detector's own boxes: on a sideways page most of them are tall and narrow.
- Whether only the content inside a region turns, or the whole page image, before it is read again.
- A synthetic scan with a sideways table for the corpus.

Kept images (the next feature) shows these pages as they are, so DOCX readers who choose it are not affected.
