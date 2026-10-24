# 02: Keep searchable scans, and scans whose text layer is wrong

**Parent:** Kept images spec, in this feature folder.

**What to build:** With kept images chosen, two more kinds of scan are kept like any other scan:
- **A searchable scan,** one whose text is hidden under the picture or drawn invisible. Its hidden text follows `[หน้าสแกน]` in the Markdown.
- **A scan whose text layer cannot be trusted,** such as hidden Thai text that a scanner misread, or a Word header in a broken font. It is kept with no text passed on.

A page whose visible text lies over a background image stays a text page. Without kept images, all these pages are read as they are today.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/kept-images`

**Searchable scans**
- [ ] Text is hidden when either holds:
  - it is drawn before an image that covers it;
  - it is drawn invisible.

  PyMuPDF's bounding-box log shows both, in drawing order: `fill-text` before `fill-image`, and `ignore-text`. This was checked on synthetic pages with PyMuPDF 1.28.2.
- [ ] A page becomes a kept page when three things hold:
  - today's rule makes it a text page;
  - its text is hidden;
  - its images together cover most of its body.
- [ ] In the Markdown, its hidden text follows the placeholder. Page furniture is removed, and no headings are made: the font sizes of hidden text are whatever the scanner's software set.
- [ ] A page whose visible text lies over a background image, such as a letterhead, stays a text page. Its image is left out as today.

**Scans whose text layer cannot be trusted** (decided with the user on 2026-10-24)
- [ ] A scan whose text layer fails the text-layer check is kept. This covers a searchable scan whose hidden text is wrong, and a scan with a broken header over it.
- [ ] Its text layer passes on nothing, as an untrusted text layer passes nothing on OCR pages today. The Markdown gets the placeholder alone.
- [ ] A page with an untrusted text layer that is not a scan is still read with OCR. `GLOSSARY.md` already says so: "unless it is a scan".

**Tests** (through the conversion function, with synthetic PDFs and the fake OCR engine)
- [ ] `pdf_builder` gains a searchable scan in both forms: text drawn invisible over the image, and text drawn under it.
- [ ] Both forms are kept, and their hidden text follows the placeholder. The fake engine is never given them.
- [ ] A searchable scan whose hidden text is wrong is kept, without that text.
- [ ] A scan with a wrong header over it is kept, without the header.
- [ ] A text page with a wrong text layer is still read by the fake engine.
- [ ] Visible text over a background image stays a text page.
- [ ] Without kept images, searchable scans and wrong text layers are read as today.
- [ ] pytest, mypy, the harness and the checks in the Linux image all pass.
