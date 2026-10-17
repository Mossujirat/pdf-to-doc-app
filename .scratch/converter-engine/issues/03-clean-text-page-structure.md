# 03: Clean text-page structure

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Markdown from a text-page PDF keeps the document's structure and drops page furniture. Headings come out as headings with the right level. Numbered and bulleted lists come out as lists. Page headers, footers and page numbers that repeat across pages are removed.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/text-pages`

**Headers and footers**
- [ ] Lines repeated in the same position across pages are removed. This includes a confidentiality stamp line and "หน้าที่ x/y" counters that restart in each appendix.
- [ ] Removed counters are never used as page numbers. Page markers always use the PDF's own page index.
- [ ] Text that appears on only one page is never removed, even near the page edge.

**Headings and lists**
- [ ] Headings are detected from font size and weight relative to body text, and rendered with matching Markdown levels.
- [ ] Thai and Arabic-numbered clauses and bulleted items are rendered as Markdown lists. Thai digits stay Thai digits.

**Tests**
- [ ] Synthetic fixtures cover a stamped header, a page counter that restarts, two heading levels, and a numbered list. They are added to the corpus, and the harness shows zero broken text on them.
