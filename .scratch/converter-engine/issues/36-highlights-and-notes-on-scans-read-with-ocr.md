# 36: Highlights and notes on scans read with OCR are lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** People highlight or draw over a scan before passing it on, as on the 34-page scanned supplement among the local samples in `docs/example_pdf/`, whose 8 ink annotations sit on 3 pages. When scans are read with OCR, the default, the text under a highlight comes out like any other text, in both outputs. The reader of the output never learns which passages someone marked. Only kept images show the marks, because the whole page becomes an image.

**Blocked by:** none

**Status:** needs-triage

**Why it is a ticket of its own:** ticket 20 covers text pages only. Grilling the what's-new page on 2026-11-02 found that scans read with OCR had no ticket. It is one of the page's known limitations (`.scratch/web-service/issues/16-whats-new-page.md`), and the release that closes it drops the limitation.

**To decide at triage**
- Whether this and ticket 20 are one piece of work: both need the same way to show a highlight in each output.
- Which marks count on a scan: annotations laid over it (as on the supplement), or also highlighter ink printed into the scan itself.
- How a highlight shows: in DOCX, yellow already marks uncertain text; in Markdown, `<mark>` already marks it too.

## Comments
