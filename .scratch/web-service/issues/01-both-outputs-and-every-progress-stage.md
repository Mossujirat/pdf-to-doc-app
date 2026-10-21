# 01: Both outputs and every progress stage from one conversion

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The conversion function can be asked for both outputs and returns each of them from one reading of the source file, with one summary, so that a visitor never waits for OCR twice. It also reports progress from the moment the source file is open, starting with its page count, which the web service needs for the daily allowance before any page is read. CLI users see no change.

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/web-core`

**Outputs**
- [x] The conversion function takes the set of output formats wanted, one or both. It returns an output for each, rendered from one document model, with one summary.
- [x] A DOCX source asked for both formats gets Markdown only. Asked for DOCX alone, it is still refused as DOCX-to-DOCX.
- [x] The CLI still asks for one format and behaves exactly as before.

**Progress**
- [x] The first report, "opened", comes as soon as the page count is known, with the source type and the page count, and before any page is read.
  - For a PDF, that is right after intake.
  - For a DOCX, it is when intake has counted its pages. Counting them means reading the DOCX, so it is read by then (see the comments).
- [x] Next come the remaining stages, in order:
  - "reading"
  - each OCR page, as current of total (as now)
  - "writing", before the outputs are rendered
- [x] A refusal at intake comes before any report.

**Tests**
- [x] Through the conversion function, with synthetic sources and the fake OCR engine:
  - both outputs from one conversion read the same as the single-format outputs
  - a DOCX asked for both gives Markdown only
  - the sequence of reports for a text-only PDF, a mixed PDF and a DOCX, including the page count

## Comments

**2026-10-21, the interface**

- `convert(to=...)` takes one format, as before, or a set of them. The result holds `outputs`, one per format, Markdown first. `output` still gives the output when there is only one, so the CLI and the existing tests are unchanged.
- Progress reports are `Opened(source_type, pages)` and `Progress(stage, current, total)`, in `progress.py`. Only the "ocr" stage has a count; "reading" and "writing" have `current` and `total` of `None`. The sandbox's "progress" events (ticket 02) carry them as they are, so their count can be empty.

**2026-10-21, a DOCX reports opened, then writing**

A DOCX's pages can be counted only by reading it whole. Pages break where Word's layout recorded them, and the page limit is checked in the same pass. A separate count would repeat that logic and could disagree with it. So for a DOCX:
- "opened" comes once the reading is done, and the reading is not reported after it: the sequence is opened, then writing.
- The daily allowance (ticket 08) is charged after the DOCX is read, not before. That costs little, as a DOCX has no OCR pages, and intake caps it at 200 MB unpacked.

The web (tickets 03 and 08) must not expect "reading" from every source file.

**2026-10-21, after code review**

- Fixed: asking for no format at all read the whole source file, OCR included, and gave no output. It now raises `ValueError`, as an unknown format does.
- Kept: one `Progress` type with an empty count for "reading" and "writing", rather than a separate type for OCR pages. It matches the spec's event, "progress, with stage, current and total", for every stage.
- Kept: the test builders for a 151-page PDF, a locked PDF and a 151-page DOCX repeat one-liners from `test_source_intake.py`. Sharing them would mean moving that file's helpers out of this ticket's scope.
