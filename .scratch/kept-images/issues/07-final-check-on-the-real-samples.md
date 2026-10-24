# 07: Final check on the real samples

**Parent:** Kept images spec, in this feature folder.

**What to build:** Before kept images is offered, check it on the local samples in `docs/example_pdf/`. On each, the DOCX must look like the original, and the Markdown must hold what the spec says. The samples are:
- **A scanned contract supplement:** 34 scans, with highlights, typed notes, two sideways pages and six two-column pages.
- **A 110-page contract** whose attachments are scans pasted into Word pages.
- **A 5-page agreement** whose text is drawn as shapes. None of its pages may be kept.

**Blocked by:** 01, 02, 03, 04, 05, 06

**Status:** ready-for-agent

**Branch:** `feat/kept-images-web`

**Permission first**
- [ ] Ask the user's permission before converting or opening any sample. The samples are real contracts, and one is marked confidential.
- [ ] On the terms given before:
  - convert on this machine only;
  - nothing of them is committed, sent anywhere, or written into a ticket, beyond counts;
  - the output is deleted after.

**Checks**
- [ ] **Convert each sample with kept images on the command line.** In Word, the user looks, or the agent where it can, and checks that:
  - every scan is kept, edge to edge, and takes one Word page, with no blank page;
  - sideways pages are as they are in the original;
  - highlights and notes show;
  - pictures on text pages show as themselves, and repeated edge logos stay out;
  - no picture comes out black where it was coloured, as one stored as a stencil would (ticket 03's Comments).
- [ ] **Check the scan-detection share against the samples:**
  - every scan is kept;
  - no text page, and no page whose text is drawn as shapes, is kept.

  If the share has to change, add a synthetic test for the case and record the change.
- [ ] **In the Markdown:** one placeholder per kept page, notes following it, and the Word header and footer over the scans left out.
- [ ] **Sizes:** each DOCX stays within 50 MB. Note whether the resolution was lowered, and the time per page.
- [ ] **Comments:** record the results here as counts only, with no text or content from the samples.
