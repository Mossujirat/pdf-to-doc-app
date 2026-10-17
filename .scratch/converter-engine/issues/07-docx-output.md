# 07: DOCX output

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user can choose DOCX as the output format and get an editable Word file with the same text and structure as the Markdown output. It is rendered from the same document model (ADR 0003). The DOCX keeps the original's structure, not its exact page layout.

**Blocked by:** 03, 04

**Status:** ready-for-agent

**Branch:** `feat/docx`

**Choosing DOCX**
- [ ] The conversion function and the CLI accept DOCX as the output format.

**Fonts**
- [ ] Thai text uses TH Sarabun New, set in the complex-script font slot together with the complex-script size. python-docx's plain font name does not set that slot.
- [ ] English text uses a sensible default font.

**Structure**
- [ ] Headings use Word's built-in heading styles at the right levels.
- [ ] Lists use Word list formatting.
- [ ] Tables are real Word tables, with merged cells where the document model has spans.
- [ ] The summary appears on the first page.

**Tests**
- [ ] Read DOCX outputs back and check the text against the reference text, the complex-script font and size, heading styles and merged cells.
- [ ] Open one DOCX from the corpus in real Word and confirm that Thai renders correctly. Note the result in the ticket's comments.
