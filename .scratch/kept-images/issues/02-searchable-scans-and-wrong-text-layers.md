# 02: Keep searchable scans, and scans whose text layer is wrong

**Parent:** Kept images spec, in this feature folder.

**What to build:** With kept images chosen, two more kinds of scan are kept like any other scan:
- **A searchable scan,** one whose text is hidden under the picture or drawn invisible. Its hidden text follows `[หน้าสแกน]` in the Markdown.
- **A scan whose text layer cannot be trusted,** such as hidden Thai text that a scanner misread, or a Word header in a broken font. It is kept with no text passed on.

A page whose visible text lies over a background image stays a text page. Without kept images, all these pages are read as they are today.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/kept-images`

**Searchable scans**
- [x] Text is hidden when either holds:
  - it is drawn before an image that covers it;
  - it is drawn invisible.

  PyMuPDF's bounding-box log shows both, in drawing order: `fill-text` before `fill-image`, and `ignore-text`. This was checked on synthetic pages with PyMuPDF 1.28.2.
- [x] A page becomes a kept page when three things hold:
  - today's rule makes it a text page;
  - its text is hidden;
  - most of what its body shows outside its text lies in its images, the measure ticket 01 uses for scans.
- [x] In the Markdown, its hidden text follows the placeholder. Page furniture is removed, and no headings are made: the font sizes of hidden text are whatever the scanner's software set.
- [x] A page whose visible text lies over a background image, such as a letterhead, stays a text page. Its image is left out as today.

**Scans whose text layer cannot be trusted** (decided with the user on 2026-10-24)
- [x] A scan whose text layer fails the text-layer check is kept. This covers a searchable scan whose hidden text is wrong, and a scan with a broken header over it.
- [x] Its text layer passes on nothing, as an untrusted text layer passes nothing on OCR pages today. The Markdown gets the placeholder alone.
- [x] A page with an untrusted text layer that is not a scan is still read with OCR. `GLOSSARY.md` already says so: "unless it is a scan".

**Tests** (through the conversion function, with synthetic PDFs and the fake OCR engine)
- [x] `pdf_builder` gains a searchable scan in both forms: text drawn invisible over the image, and text drawn under it.
- [x] Both forms are kept, and their hidden text follows the placeholder. The fake engine is never given them.
- [x] A searchable scan whose hidden text is wrong is kept, without that text.
- [x] A scan with a wrong header over it is kept, without the header.
- [x] A page that is not a scan and whose text layer cannot be trusted is still read by the fake engine (ticket 01's test).
- [x] Visible text over a background image stays a text page.
- [x] Without kept images, searchable scans and wrong text layers are read as today.
- [x] pytest, mypy, the harness and the checks in the Linux image all pass.

## Comments

**2026-10-24, implemented on branch `feat/kept-images`**

- **One rule instead of three conditions.**
  - With kept images, `_kind` judges each page by the text a reader sees on it, the rows that no hidden text covers.
  - It keeps the page when two things hold:
    - judged by those rows alone, the page would be read with OCR: they cover under 5% of the body, and the body shows more outside them;
    - what it shows outside them lies mostly in its images, ticket 01's measure.
  - So the ticket's "today's rule makes it a text page" and "its text is hidden" become "the text a reader sees is too little for a text page".
  - **What follows from this:**
    - A searchable scan with a long visible typed note over it stays a text page, as a scan with such a note did in ticket 01.
    - A page with no hidden text is judged exactly as in ticket 01.
    - Without kept images, nothing changed.
- **Hidden text** (`_hidden_text`):
  - **What it is:** text PyMuPDF's bounding-box log records as `ignore-text` (drawn invisible), or `fill-text`/`stroke-text` that an opaque image drawn after it covers, by 90% of its box.
  - **Which images are opaque:** those without a mask, by `get_image_info`'s `has-mask`.
  - **Pairing images:** the two lists are paired image by image, in drawing order. On every synthetic case they agree in order. Should they hold different numbers of images, no image is taken to hide anything.
  - **Rotated pages:** both lists use the page as stored, so the hidden boxes are turned with `page.rotation_matrix` before they meet the rows, which are on the page as shown (ticket 19). A test covers a rotated searchable scan in both forms.
  - **Hidden rows:** a row is hidden when hidden text covers half of it or more.
- **Not caught:** an image drawn with a constant opacity below 1, through the graphics state rather than a mask. Text under it would count as hidden. No sample has shown one.
- **Untrusted text layers.**
  - An untrusted text layer now passes on nothing on a kept page, as on an OCR page.
  - At the user's choice (2026-10-24), the summary still flags such a page. The headline says "(หน้า … ข้อความในไฟล์ไม่น่าเชื่อถือ จึงไม่ได้นำมาใช้)" after the kept pages, and "จึงอ่านด้วย OCR" stays for OCR pages alone.
  - Ticket 05 gained a line for the web's page table, which today says "จึงอ่านด้วย OCR" for every flagged page.
- **Code review** (two axes):
  - **Spec: the bug.** The first version took an image as opaque when its box lay within any unmasked image's box. The reviewer showed a transparent stamp over a letterhead image counting as opaque, which turned that text page into a kept page. Images are now paired by drawing order, and a test covers the stamp on a plain page and on a letterhead.
  - **Spec: tests added.**
    - Hidden text makes no heading.
    - A hidden header over every scan is left out.
    - The wrong-header scan is never given to OCR.
  - **Standards, all fixed:**
    - the constants named for what they measure, with why;
    - the untrusted-layer emptying done once;
    - `pymupdf.Rect` instead of hand-made box sums;
    - `_ink_needing_ocr`;
    - no clash between a drawing-log entry's kind and a page kind;
    - `pdf_builder` hides text with an `invisible` flag, not a render-mode number;
    - test names and sections.
- **Checks:**
  - **Default output:** the same as `main` on the 17 corpus PDFs: Markdown byte for byte, and DOCX except `docProps/core.xml`.
  - **Corpus:** regenerating it with the changed `pdf_builder` leaves every committed file unchanged.
  - **The transparent-stamp test checks what it should:** with every image taken as opaque, the page becomes kept and the test fails.
  - **Linux image,** with the code mounted:
    - mypy;
    - pytest;
    - `pytest -m ocr`;
    - the harness: OCR CER 0.0072, unchanged;
    - the CLI;
    - the sandbox entry point.
