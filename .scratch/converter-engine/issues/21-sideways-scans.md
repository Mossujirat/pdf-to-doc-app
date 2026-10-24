# 21: Scans printed sideways are read as nonsense

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** A landscape table is often printed sideways on an upright page, such as a price schedule or a project timeline. On a scan, OCR reads such a page as if its lines ran across the page. The output then has three faults:
- The characters are garbled. Latin letters come out mirrored and mixed with Thai letters.
- The order is reversed. The table's totals come first and its title last.
- The table is lost.

Most of the text is marked uncertain, so the reader is warned, but nothing of the page can be used.

**Blocked by:** none

**Status:** done

**Seen on:** two pages of a scanned contract supplement among the local samples in `docs/example_pdf/`, converted on 2026-10-22 and 2026-10-23 with the user's permission: a price schedule and a project timeline. The page itself is upright. Only its content is turned a quarter turn.

**More of it in a 110-page Thai contract** among the same samples. Its attachments are scans pasted into Word pages. It was converted on 2026-10-23 with the user's permission.
- **Ten pages were printed sideways,** and nothing of them survived:
  - five pages of a work plan and a budget;
  - a tax registration certificate;
  - four pages of a table of delegated powers.
- **Sideways column headers** inside upright tables also came out as marked junk.
- This is the largest loss of content in that file, so this ticket now weighs more than when it was opened.

**Where to look:** `paddle.py` turns off PaddleOCR's document orientation, unwarping and text-line orientation (`use_doc_orientation_classify`, `use_doc_unwarping`, `use_textline_orientation`), as the October 2026 benchmark chose. Nothing else turns a page's image before it is read.

Kept images (the next feature) shows these pages as they are, so DOCX readers who choose it are not affected.

**Measured on synthetic pages (2026-10-24)**
- **Pages:** five sideways pages (a price schedule and a project timeline, each turned both ways, and one with an upright header and page number), and 19 upright pages (the corpus's scans, the damaged scans, short pages, a 30-line page, and an upright table with sideways column headers). They were read at 300 dpi with 4 threads.
- **Why it goes wrong:** PaddleOCR turns every crop at least 1.5 times as tall as wide a quarter turn counter-clockwise before reading it (`paddlex/inference/pipelines/components/common/crop_image_regions.py`).
  - **Content turned clockwise:** each line is read right, at confidence 0.97–0.98. But `ocr_page` sorts the tall boxes by their vertical centres, so the order comes out reversed, and almost nothing is marked: 505 of 540 edits carry no warning.
  - **Content turned the other way:** each line is read upside down, the "mirrored" text, and most of it is marked.
  - CER is 0.85–0.90 on sideways pages, against 0.02 for the same tables upright.
- **Finding a sideways page:** take the share of text-box area in boxes at least twice as tall as wide. It is 0.85–0.96 on sideways pages and 0–0.12 on upright ones; the upright table with sideways headers scores 0.12. The boxes exist already, so this costs nothing. Single upright digits reach a height 1.47 times their width, so use a factor of 2–3, not 1.5.
- **Telling the direction:**
  - The tall boxes' confidence on the first read is 0.97–0.98 for content turned clockwise and 0.50–0.65 for the other way.
  - Reading one or two of the largest tall crops turned the other way separates the two by 0.34–0.42 in confidence. It was right on all five pages and costs about 0.15 s.
  - Counting unknown words fails, because upside-down text yields few Thai words; their share does separate.
- **Turned and read again:** CER drops to 0.014–0.025, the same as upright. The second read adds 1.3–2.0 s; a page takes 0.4–2.5 s to read upright.
  - On the page with an upright header, CER is 0.101: once the page is turned, the header is sideways and lands in the middle of the table.
  - Table rows come out in order, but run together into one paragraph, as on other scanned tables (ticket 14).
- **Ruled out:**
  - PaddleOCR's document orientation classifier (`PP-LCNet_x1_0_doc_ori`: 6.9 MB, 15 ms a page). It got all five sideways pages right, but called 3 of 19 upright pages upside down, because it looks only at the middle of the page.
  - Text-line orientation (0° or 180° per line). It turned correct lines upside down on upright pages, and it does not fix the order.

**Decided at triage (2026-10-24, grilled with the user)**
- **Scope:** OCR pages whose whole content is turned a quarter turn, either way. That includes scans, and pages whose text is drawn as shapes or whose text layer is not trusted, since the method uses only what OCR reads.
- **Out of scope:**
  - sideways column headers inside upright tables, and sideways text in a text layer (ticket 29);
  - upside-down scans (ticket 30).
- **Goal:** the text reads right, in the right order. Table structure comes with ticket 14.
- **How:**
  - Find a sideways page by its tall boxes, as measured above. The exact threshold is the implementer's.
  - Tell the direction by the tall boxes' confidence, checked by reading one or two crops turned the other way.
  - Then turn the whole page image and read it again.
  - When the signs disagree or are weak, read the page as today.
  - Do it where OCR pages are read, through the `OcrEngine` interface, not inside `paddle.py`, so any engine and `FakeEngine` get it.
- **Mixed pages:** when part of a scan is upright, the page turns with the larger part, and the upright part may land out of place. Check whether the real sideways pages have such parts; if they do, open a ticket.
- **Text layer on a sideways page:** headers, footers and notes from the text layer behave as on any other page. Page furniture is still removed, and a note comes out once. Keep every comparison in one frame (ticket 19).
- **Time:** upright pages are not slowed. A sideways page may take about twice as long.
- **Summary:** it does not say which pages were turned.

**To do**
- [x] A fast test with `FakeEngine`, extended so that it can report a page's lines as tall boxes, as PaddleOCR does on a sideways page. Cover both directions, an upright page that must not turn, and a weak-signal page that must not turn.
- [x] A synthetic sideways page in the corpus, turned each way, with reference text, so that the harness measures it. Keep the mixed page out of the gated corpus.
- [x] Confirm with PaddleOCR in `pytest -m ocr`.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.
- [x] Final check on the local samples, with the user's permission given on 2026-10-24: the supplement's two sideways pages and the 110-page contract's ten.
  - Converting them and reading the output on this machine is allowed. Nothing of them is committed or put in a ticket, and the output is deleted after.
  - Check that the text reads right and in order, whether any page has upright parts inside its scan, and how long each page takes.

## Comments

**2026-10-24, implemented on branch `fix/sideways-pages`**

- **What changed**
  - `ocr.read_page` reads each OCR page. When the tall boxes hold most of the page's text and the direction is clear, it turns the page image and reads it again. `reading.py` calls it in place of `ocr_page`, which became the private `_ocr_page`.
  - `_ocr_page` puts the text layer on the turned page in two steps:
    - Each row is compared with the engine's boxes where it lies on the turned image, so a note's OCR copy is dropped.
    - The row is then placed at the same share of the page's height and width, so a header stays at the top edge and is still removed as page furniture.
  - `PageImage.turn` records how far an image was turned, and `turned_box` moves a box with it.
- **The direction, changed from the first draft**
  - The first draft read the two largest tall boxes turned each way.
  - Each crop read took 0.3–0.75 s, so a sideways page took 2.4–2.9 times its first read: over the budget.
  - It now does what triage decided. It compares the engine's first reading of the largest tall box with the same box read turned clockwise, which is one crop read.
  - This relies on PaddleOCR turning every box at least 1.5 times as tall as wide counter-clockwise before reading it. The code says so where it decides.
  - **The gap between the two readings:**
    - 0.22–0.65 on the samples' sideways pages, and 0.29–0.33 on synthetic ones.
    - A page turns when the gap is 0.15 or more, and the reading taken for upright is at least 0.8 sure.
  - **The 0.8 floor came from code review.** A crop in which the engine found nothing had counted as a clear win for 270, so a page needing 90 was turned upside down.
    - The readings taken for upright on the samples were 0.90–0.99 sure, so the floor changes none of their decisions.
    - PaddleOCR reads the same image the same way every run: two runs on the samples gave identical numbers.
- **A fault found on the way.** A crop catches bits of the lines beside it. Averaged per box, two stray letters outweighed the line itself, and a synthetic timeline was turned the wrong way. Confidence is now weighted by characters, and a PaddleOCR test guards it.
- **Measured on the local samples**
  - **Which pages turned:** exactly the 12 sideways pages, the supplement's 2 and the contract's 10. None of the other 113 OCR pages turned.
  - **Time:**
    - Upright pages took exactly as long as before.
    - A turned page took 1.9–2.4 times its first read, 2.2 at the median. Even without the crop, the second read alone takes a little longer than the first, because more of the text is read.
  - **Text quality:**
    - The contract's turned pages went from 34–73% dictionary words to 86–97%, and their marked text from nearly all to 2–4%.
    - The one exception is a tax registration form, still 27% marked, for its stamps and handwriting.
    - The supplement's two pages are English, and read cleanly.
  - **Mixed pages:** none. Every page's header, footer and page number belonged to the turned content and came out in place. No ticket opened.
  - **The text layer:** the contract's Word header and footer did not appear on the turned pages, so page furniture is still removed there.
  - **Dense tables:** they come out with cells of different columns run together, as decided (ticket 14).
- **Corpus**
  - `sideways-scans` holds a price schedule turned each way. It scores CER 0.0084 and 0.0042, against 0.88 and 0.77 without turning.
  - Two other tables were tried and left out, because they failed for other reasons, the same way in both directions:
    - a timeline with "ที่" and empty cells (CER 0.11: rows regrouped and "ที่" misread unmarked, tickets 14 and 23);
    - a work plan whose detector lost one cell's text.
- **Tests**
  - **Fast tests in `test_ocr_pages.py`, with `FakeEngine` (which now reads sideways pages as PaddleOCR does):**
    - a sideways page reads as the same page upright, both ways;
    - an upright page with a little sideways text, such as two column headers, is not turned;
    - a sideways page whose box reads as nothing once turned is not turned the wrong way;
    - a sideways page that reads no better turned is read as it is;
    - a note typed at the foot of a sideways page comes out once, after the table, where turning it with the page would have put it before;
    - a stamped header is removed from a sideways page too.
  - **`test_paddle.py`:** a sideways timeline is turned the way it reads, both ways, and its lines come out in order.
  - **Checked by breaking the code on purpose.** Each test fails when its mechanism is removed:
    - the share of tall boxes;
    - the gap;
    - the floor on the reading taken for upright;
    - turning the text layer onto the turned image;
    - placing it by share of the page;
    - the weighting by characters;
    - turning at all, for the PaddleOCR test in both directions.
