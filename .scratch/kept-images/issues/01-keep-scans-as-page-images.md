# 01: Keep scans as page images

**Parent:** Kept images spec, in this feature folder.

**What to build:** A user can choose kept images, with `--keep-images` on the command line or the conversion function's flag. Each scan then becomes a kept page:
- **DOCX:** the page as it looks, highlights and notes included, filling a Word page of the original's size and orientation from edge to edge.
- **Markdown:** `[หน้าสแกน]`, followed by the text the file already holds on that page, such as a typed note.

The scan is never read with OCR, so a file of scans converts in a fraction of OCR's time. Without the setting, nothing changes. This is the tracer bullet: the later tickets add searchable scans (02), pictures (03), the size limit (04) and the web (05).

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/kept-images`

**The setting**
- [x] The conversion function takes a kept-images flag, off by default.
- [x] The CLI takes `--keep-images`, with Thai help text. It says that scans and pictures stay images in the DOCX instead of being read with OCR, and that the Markdown gets `[หน้าสแกน]`. The README documents it.
- [x] Off, every output is byte for byte what it was before this ticket:
  - every existing test passes unchanged;
  - the corpus and `pdf-to-doc-eval` give the same results.
- [x] A DOCX source ignores the setting.

**Which pages are kept**
- [x] A page is a kept page when two things hold:
  - it needs OCR by today's test;
  - most of what its body shows outside its text, outside the edge bands, lies in its images.

  Set the share on synthetic pages. Ticket 07 checks it on the samples. (Changed at /implement from "its images together cover most of its body", so that a scan pasted at half a page is still a scan; see Comments.)
- [x] These are still read with OCR:
  - a page whose text is drawn as shapes;
  - a page that is not a scan and whose text layer cannot be trusted;
  - until ticket 02, a scan whose text layer cannot be trusted.
- [x] Kept pages are never given to the OCR engine. A file whose OCR pages are all kept never loads it.

**Page images**
- [x] A kept page's image is the page as it is shown, rotation applied and annotations included (highlights, ink, notes).
- [x] It is rendered in RGB at 150 dpi and encoded as JPEG at once. The raw pixmap is dropped straight away, so only compressed bytes are held.

**Document model**
- [x] A third page kind, kept, beside text pages and OCR pages.
- [x] A kept page opens with a placeholder of a new kind, scan, labelled `หน้าสแกน`. The placeholder carries the page image.
- [x] The rows of the page's text layer follow the placeholder:
  - page furniture is removed across the document as usual;
  - they make no headings and do not count towards the document's body size, as an OCR page's rows do.

**DOCX**
- [x] **Each kept page is a Word section of its own:**
  - the size and orientation of the original page as shown, with no margins;
  - the page image fills it from edge to edge;
  - a page over Word's 22 inches a side is scaled down to fit, keeping its shape;
  - the next section returns to A4 with normal margins.
- [x] **A kept page holds only its image,** with no text.
- [x] **One Word page per kept page, with no blank page.**
  - python-docx puts a section break in a new empty paragraph. After an image as tall as the page, that paragraph falls onto a page of its own.
  - Carry the break so that this cannot happen.
- [x] **The summary stays the first paragraph,** on A4. When page 1 is kept, the summary has the first Word page to itself.
- [x] **Checked once in real Word,** on a synthetic DOCX with:
  - an upright scan;
  - a landscape page;
  - a scan on a rotated page;
  - a sideways scan;
  - a text page between kept pages.

  Every kept page is edge to edge and takes one Word page. A landscape page is landscape, and the sideways scan shows as it is in the original.

**Markdown**
- [x] A kept page gives its page marker, then `[หน้าสแกน]`, then its text.

**Summary and progress**
- [x] The headline counts kept pages: "เก็บเป็นภาพ N หน้า ได้แก่หน้า …".
  - The sentence shows only when there are kept pages.
  - The scan placeholder is not counted among placeholders.
- [x] A new progress stage for the page images, with a current and total count, as OCR has.
- [x] The CLI prints one line per page image, as it does per OCR page.

**Tests** (through the conversion function, with synthetic PDFs and the fake OCR engine)
- [x] A scan is kept in both outputs. The fake engine is never given it, and the engine is never loaded.
- [x] A scan with a typed note: the note follows the placeholder. Over several scans, a repeated header is left out.
- [x] Each of these is kept as shown, with the matching Word page:
  - a scan on a page rotated by /Rotate;
  - a sideways scan;
  - a landscape page.
- [x] Each of these is still read by the fake engine:
  - a page whose text is drawn as shapes (`pdf_builder` gains such a page);
  - a page whose text layer cannot be trusted.
- [x] A mixed file of text pages and scans keeps text pages as editable A4 text.
- [x] The summary and the progress reports, with kept pages and without them.
- [x] The CLI with `--keep-images`.
- [x] pytest, mypy, the harness and the checks in the Linux image all pass.

## Comments

**2026-10-24, implemented on branch `feat/kept-images`**

- **Changes, by module**
  - **`reading.py`**
    - Today's two-step test, whether a page needs OCR, became `_kind`, which returns text, OCR or kept. Without kept images it renders and decides exactly as before.
    - A kept page's image comes from `_kept_image`: the page as shown, annotations included, rendered in RGB at 150 dpi and saved as a JPEG at quality 75. The pixmap is dropped at once.
  - **`model.py`**
    - Gains the page kind `kept`, the placeholder kind `scan` (`[หน้าสแกน]`), and `KeptImage`, which holds JPEG bytes and the size shown, in points.
    - A `Placeholder` can carry a `KeptImage`, and `Page.kept_image` finds it.
  - **`docx_output.py`**
    - Each kept page is a Word section of its own: the page's size and orientation, no margins, and an inline image exactly the page's size, with no space before or after it.
    - The section break goes into the last paragraph of the section that ends. An empty paragraph is added only when that section ends with a table.
    - The last section's properties are the body's own, so no empty section follows a kept last page.
  - **`summary.py`:** adds "เก็บเป็นภาพ N หน้า ได้แก่หน้า …" when there are kept pages. The scan placeholder is not counted among placeholders.
  - **`progress.py`:** gains the stage `images`. It comes after `reading` and before `ocr`, as kept pages are made first.
  - **`cli.py`:** gains `--keep-images` and prints "เก็บภาพหน้า x/y".
- **The scan test changed from the spec** (recorded in the spec and in tickets 01 and 02).
  - **Why:** "images cover most of the body" would send to OCR a scan pasted at half a Word page.
  - **The test now:** at least half of what the body shows outside its text, as `_ink_beyond_text` measures it at 50 dpi, must lie inside the page's images. Text drawn as shapes lies outside every image.
  - **What the reviewer found:** a page holding nothing but a small logo is then kept as well.
  - **What the user decided (2026-10-24):** keep it, since its image is all there is and OCR would read the logo as nonsense. A test records this, and `GLOSSARY.md`'s Kept page now covers it.
  - **Still open:** ticket 07 checks the share on the samples.
- **Headings.** A kept page is not a text page to page layout, so its rows make no headings by size and do not count towards the body size. As on an OCR page, a short row that is all bold can still become a heading.
- **Default path unchanged:** each of the 17 corpus PDFs was converted to both outputs with `main`'s code (98d187e) and with this branch's, OCR pages read as blank.
  - The Markdown was the same byte for byte.
  - The DOCX was the same in every part except `docProps/core.xml`. The zip changes from run to run, on either code, because python-docx stamps the time.
- **In real Word (16, through COM):** on a synthetic DOCX holding:
  - an upright scan with a note;
  - a landscape scan;
  - a text page;
  - a page ending in a table;
  - a scan on a page rotated 270°;
  - a sideways scan;
  - a scan as the last page.
  - **What Word showed:**
    - 8 pages (the summary and 7), with no blank page;
    - each section the size and orientation expected;
    - in the exported PDF, every kept page edge to edge;
    - the rotated scan upright, and the sideways scan as it is.
  - Checked again after the review changes: 8 pages.
- **Checks:**
  - **Windows:** pytest and mypy.
  - **Linux image,** with `src`, `tests` and `corpus` mounted:
    - mypy;
    - pytest: 486 passed;
    - `pytest -m ocr`: 15 passed;
    - `pdf-to-doc-eval corpus/synthetic --max-broken 0`: OCR CER 0.0072, the same as `main` since OCR pages are untouched;
    - a CLI conversion, with and without `--keep-images`;
    - the sandbox entry point.
- **Test support:**
  - **`pdf_builder`** gains:
    - `Drawn` (text drawn as shapes, by way of SVG);
    - `Pasted` (a grey scan pasted over part or all of a page of any size);
    - `Scan.landscape`;
    - `highlighted` (a yellow mark as an annotation).
  - **`docx_reader`** gains:
    - each page's layout;
    - the summary's layout;
    - inline images;
    - a page that starts at a section break.
- **Code review** (two axes):
  - **Glossary terms:** "text page" had been used for a page whose text layer cannot be trusted, and "Picture" for an inline image of a whole page. Both fixed.
  - **Smells, all fixed:**
    - `_scan` renamed `_is_scan`;
    - one zoom constant;
    - the open section's properties held in one variable;
    - `Page.kept_image`;
    - a label map in the CLI;
    - the PDF builders kept in `pdf_builder`.
  - **Tests added:**
    - a kept page with text holds no text in the DOCX;
    - the summary's page is A4;
    - with kept images on and nothing to keep, the reports and the output are the same as with it off;
    - the rotated and sideways images' ink lies where it should.
- **Left for later tickets:** a scan whose text layer cannot be trusted is still read with OCR (ticket 02); `--keep-images` already promises pictures, which come with ticket 03; and the web does not offer the setting yet (ticket 05).
