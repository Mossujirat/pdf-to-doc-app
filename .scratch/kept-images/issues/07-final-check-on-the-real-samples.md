# 07: Final check on the real samples

**Parent:** Kept images spec, in this feature folder.

**What to build:** Before kept images is offered, check it on the local samples in `docs/example_pdf/`. On each, the DOCX must look like the original, and the Markdown must hold what the spec says. The samples are:
- **A scanned contract supplement:** 34 scans, with highlights, typed notes, two sideways pages and six two-column pages.
- **A 110-page contract** whose attachments are scans pasted into Word pages.
- **A 5-page agreement** whose text is drawn as shapes. None of its pages may be kept.

**Blocked by:** 01, 02, 03, 04, 05, 06

**Status:** done

**Branch:** `feat/kept-images-web`

**Permission first**
- [x] Ask the user's permission before converting or opening any sample. The samples are real contracts, and one is marked confidential.
- [x] On the terms given before:
  - convert on this machine only;
  - nothing of them is committed, sent anywhere, or written into a ticket, beyond counts;
  - the output is deleted after.

**Checks**
- [x] **Convert each sample with kept images on the command line.** In Word, the user looks, or the agent where it can, and checks that:
  - every scan is kept, edge to edge, and takes one Word page, with no blank page;
  - sideways pages are as they are in the original;
  - highlights and notes show;
  - pictures on text pages show as themselves, and repeated edge logos stay out;
  - no picture comes out black where it was coloured, as one stored as a stencil would (ticket 03's Comments).
- [x] **Check the scan-detection share against the samples:**
  - every scan is kept;
  - no text page, and no page whose text is drawn as shapes, is kept.

  If the share has to change, add a synthetic test for the case and record the change.
- [x] **In the Markdown:** one placeholder per kept page, notes following it, and the Word header and footer over the scans left out.
- [x] **Sizes:** each DOCX stays within 50 MB. Note whether the resolution was lowered, and the time per page.
- [x] **Comments:** record the results here as counts only, with no text or content from the samples.

## Comments

**2026-10-25, checked on branch `feat/kept-images-web` (60d4773), with the user's permission given that day**

- **The terms:**
  - The samples were converted on this machine alone, with the CLI's `--keep-images`, to DOCX and to Markdown.
  - The DOCX were opened in Word 16 through COM and exported to PDF.
  - Nothing of the samples reached a sub-agent, a commit or anywhere else, and the outputs were deleted after.
- **Page kinds,** from the CLI's summary and from the converter's own measures on every page (the visible text's share of the body, and the share of what the body shows outside the text that lies in images):

  | Sample | Pages | Kept | Text | OCR |
  |---|---|---|---|---|
  | Scanned supplement | 34 | 34 | 0 | 0 |
  | 110-page contract | 110 | 87 | 19 | 4 |
  | 5-page agreement, text drawn as shapes | 5 | 0 | 0 | 5 |

  - **Without kept images,** every kept page is an OCR page, and the text pages are the same 19.
  - **The contract's 4 OCR pages** have no image at all: they are text pages whose text layer cannot be trusted. So they are read with OCR, as the spec says for pages that are not scans.
- **The scan share (0.5) needs no change.**
  - On every one of the 121 kept pages, all of what the body shows outside the text lies in images (share 1.0).
  - On the agreement's pages the share is 0 to 0.08.
  - No page lies near the line, so no synthetic test was added.
- **In Word:**
  - **Supplement:** 35 pages, the summary's and one per scan.
  - **Contract:** 129 pages. Its 87 kept pages each take one, and its 23 text and OCR pages reflow onto A4.
  - **Agreement:** 9 pages.
  - **No blank page** in any of them.
  - **Each of the 121 kept pages** is one image covering the whole exported page, with no text on it, in a section with no margins. Its size and orientation match the source page as shown (121 of 121), the supplement's turned pages included.
- **Highlights:** the supplement's 8 ink annotations, on 3 pages, show in the kept images. Inside each annotation's box, the image is nearer the render with the annotation than without it: a mean difference of 11–24 grey levels, against 25–56. One was also checked by eye. None of the contract's 2 annotated pages is kept.
- **Pictures on text pages:**
  - The contract's 8 placeholders (4 images and 4 signatures) are 8 pictures in the DOCX, on 2 pages.
  - Each was checked by eye beside the same place on the source page: colours and transparency as the original.
  - None came out black: no stencil image showed (ticket 03's gap).
  - No logo repeated at an edge became a picture.
- **The Markdown:**
  - One `[หน้าสแกน]` per kept page (34 and 87), and none on any other page.
  - Text follows the placeholder on 5 of the supplement's kept pages and 6 of the contract's.
  - **The contract's header and footer:** the source's text layer holds 2 rows repeated on all 87 kept pages. Neither appears in the Markdown; no line repeats on 3 or more kept pages.
- **Sizes and time** (the CLI, including Python's start):

  | Sample | DOCX | Lowered | DOCX run | Markdown run |
  |---|---|---|---|---|
  | Supplement | 5.9 MB | no | 14.9 s (0.44 s a page) | 14.4 s |
  | Contract | 11.2 MB | no | 75.2 s, its 4 OCR pages and the OCR engine's loading included | 70.0 s |
  | Agreement | 41 KB | no | 41.0 s, all OCR | 39.8 s |

  Today's OCR took about 200 s for the supplement.
