# 01: Keep scans as page images

**Parent:** Kept images spec, in this feature folder.

**What to build:** A user can choose kept images, with `--keep-images` on the command line or the conversion function's flag. Each scan then becomes a kept page:
- **DOCX:** the page as it looks, highlights and notes included, filling a Word page of the original's size and orientation from edge to edge.
- **Markdown:** `[หน้าสแกน]`, followed by the text the file already holds on that page, such as a typed note.

The scan is never read with OCR, so a file of scans converts in a fraction of OCR's time. Without the setting, nothing changes. This is the tracer bullet: the later tickets add searchable scans (02), pictures (03), the size limit (04) and the web (05).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Branch:** `feat/kept-images`

**The setting**
- [ ] The conversion function takes a kept-images flag, off by default.
- [ ] The CLI takes `--keep-images`, with Thai help text. It says that scans and pictures stay images in the DOCX instead of being read with OCR, and that the Markdown gets `[หน้าสแกน]`. The README documents it.
- [ ] Off, every output is byte for byte what it was before this ticket:
  - every existing test passes unchanged;
  - the corpus and `pdf-to-doc-eval` give the same results.
- [ ] A DOCX source ignores the setting.

**Which pages are kept**
- [ ] A page is a kept page when two things hold:
  - it needs OCR by today's test;
  - its images together cover most of its body, outside the edge bands.

  Set the share on synthetic pages. Ticket 07 checks it on the samples.
- [ ] These are still read with OCR:
  - a page whose text is drawn as shapes;
  - a text page whose text layer cannot be trusted;
  - until ticket 02, a scan whose text layer cannot be trusted.
- [ ] Kept pages are never given to the OCR engine. A file whose OCR pages are all kept never loads it.

**Page images**
- [ ] A kept page's image is the page as it is shown, rotation applied and annotations included (highlights, ink, notes).
- [ ] It is rendered in RGB at 150 dpi and encoded as JPEG at once. The raw pixmap is dropped straight away, so only compressed bytes are held.

**Document model**
- [ ] A third page kind, kept, beside text pages and OCR pages.
- [ ] A kept page opens with a placeholder of a new kind, scan, labelled `หน้าสแกน`. The placeholder carries the page image.
- [ ] The rows of the page's text layer follow the placeholder:
  - page furniture is removed across the document as usual;
  - they make no headings and do not count towards the document's body size, as an OCR page's rows do.

**DOCX**
- [ ] **Each kept page is a Word section of its own:**
  - the size and orientation of the original page as shown, with no margins;
  - the page image fills it from edge to edge;
  - a page over Word's 22 inches a side is scaled down to fit, keeping its shape;
  - the next section returns to A4 with normal margins.
- [ ] **A kept page holds only its image,** with no text.
- [ ] **One Word page per kept page, with no blank page.**
  - python-docx puts a section break in a new empty paragraph. After an image as tall as the page, that paragraph falls onto a page of its own.
  - Carry the break so that this cannot happen.
- [ ] **The summary stays the first paragraph,** on A4. When page 1 is kept, the summary has the first Word page to itself.
- [ ] **Checked once in real Word,** on a synthetic DOCX with:
  - an upright scan;
  - a landscape page;
  - a scan on a rotated page;
  - a sideways scan;
  - a text page between kept pages.

  Every kept page is edge to edge and takes one Word page. A landscape page is landscape, and the sideways scan shows as it is in the original.

**Markdown**
- [ ] A kept page gives its page marker, then `[หน้าสแกน]`, then its text.

**Summary and progress**
- [ ] The headline counts kept pages: "เก็บเป็นภาพ N หน้า ได้แก่หน้า …".
  - The sentence shows only when there are kept pages.
  - The scan placeholder is not counted among placeholders.
- [ ] A new progress stage for the page images, with a current and total count, as OCR has.
- [ ] The CLI prints one line per page image, as it does per OCR page.

**Tests** (through the conversion function, with synthetic PDFs and the fake OCR engine)
- [ ] A scan is kept in both outputs. The fake engine is never given it, and the engine is never loaded.
- [ ] A scan with a typed note: the note follows the placeholder. Over several scans, a repeated header is left out.
- [ ] Each of these is kept as shown, with the matching Word page:
  - a scan on a page rotated by /Rotate;
  - a sideways scan;
  - a landscape page.
- [ ] Each of these is still read by the fake engine:
  - a page whose text is drawn as shapes (`pdf_builder` gains such a page);
  - a text page whose text layer is wrong.
- [ ] A mixed file of text pages and scans keeps text pages as editable A4 text.
- [ ] The summary and the progress reports, with kept pages and without them.
- [ ] The CLI with `--keep-images`.
- [ ] pytest, mypy, the harness and the checks in the Linux image all pass.
