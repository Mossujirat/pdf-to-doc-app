# 01: Both outputs and every progress stage from one conversion

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The conversion function can be asked for both outputs and returns each of them from one reading of the source file, with one summary, so that a visitor never waits for OCR twice. It also reports progress from the moment the source file is open, starting with its page count, which the web service needs for the daily allowance before any page is read. CLI users see no change.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Outputs**
- [ ] The conversion function takes the set of output formats wanted, one or both. It returns an output for each, rendered from one document model, with one summary.
- [ ] A DOCX source asked for both formats gets Markdown only. Asked for DOCX alone, it is still refused as DOCX-to-DOCX.
- [ ] The CLI still asks for one format and behaves exactly as before.

**Progress**
- [ ] The first report, "opened", comes as soon as the page count is known, with the source type and the page count, and before any page is read.
  - For a PDF, that is right after intake.
  - For a DOCX, it is when intake has counted its pages.
- [ ] Next come the remaining stages, in order:
  - "reading"
  - each OCR page, as current of total (as now)
  - "writing", before the outputs are rendered
- [ ] A refusal at intake comes before any report.

**Tests**
- [ ] Through the conversion function, with synthetic sources and the fake OCR engine:
  - both outputs from one conversion read the same as the single-format outputs
  - a DOCX asked for both gives Markdown only
  - the sequence of reports for a text-only PDF, a mixed PDF and a DOCX, including the page count
