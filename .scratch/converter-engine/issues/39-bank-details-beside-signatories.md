# 39: Bank details beside a list of signatories are read across

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages and on text pages drawn line by line across, bank details set beside a list of signatories are joined line by line with it. An account number can land beside the wrong name. Nothing marks it.

**Blocked by:** none

**Status:** done

**Split from:** ticket 32, on 2026-11-03, in triage. Ticket 32 keeps side panels and signature blocks side by side, which each have a cue. This layout has none yet.

**What is known so far** (ticket 32, synthetic pages)
- **Today's CER:** 0.36 on a scan, 0.56 on a text page drawn across.
- **Neither of ticket 32's cues covers it.** Both sides are set in the same type on the same rows, so their lines pair as fully as a label–value list's, and no signing word repeats on a row.
- **It looks like a label–value list with a second list beside it,** which the column finder's guard rightly keeps whole.

**To decide at triage**
- A cue that tells it from a label–value list, if there is one.
- Whether it is a known limitation of its own on the what's-new page.

## Comments

**2026-11-04, from ticket 32**

- **A known limitation,** together with ticket 41, worded with the user: "แถบข้อความข้างจดหมายที่ตัวอักษรขนาดเท่าเนื้อความ และเลขบัญชีที่วางข้างรายชื่อผู้ลงนาม บนหน้าสแกน ยังถูกอ่านปนกับข้อความข้างๆ เลขบัญชีอาจไปอยู่ผิดที่".

**2026-11-11, triage (grilled with the user, together with ticket 41)**

**The real layout is not the fixture's.** The five-page agreement's page holds four blocks under headings, without rules, two by two: the bank's name and address above the account's name and number on the left, transfer instructions above the signatories on the right. They are set in the body's own type, but each side keeps its own rows: the right-hand blocks start lower than the left-hand ones. The fixture in `tests/test_ocr_pages.py` ("bank details beside the signatories") pairs every line on one baseline, as labels and values do; no sample shows that.

**Measured** (OCR boxes recorded on this machine, then deleted; numbers only):

| Region | Box heights | Lines | Median characters | Lines on the other side's baselines | Block starts from the nearest on the other side |
| --- | --- | --- | --- | --- | --- |
| five-page agreement, the four blocks | 44 / 43 | 8 / 7 | 19.5 / 27 | 25% / 29% | 0.82 and 0.44 box heights |
| 110-page contract, unruled table A | 52 / 62 | 9 / 8 | 40 / 19 | 44% / 50% | 0.6 (header), 0.07 |
| 110-page contract, unruled table B | 55 / 58 | 15 / 19 | 36 / 20 | 87% / 68% | 0.1, 0.0 |

- Ticket 32's panel rule without its smaller-type condition splits the four blocks right, and the two unruled tables wrong (each item away from its owner). It splits nothing new on the GIZ supplement (38 reads) or the 10-page EGAT contract (10 reads).
- The gutter between the blocks is 43 px, about one box height, so the cut finds it.

**Decided**
- **Scope:** headed blocks side by side in the body's own type, each side on its own rows, on OCR pages and on text pages drawn line by line across (the same `in_reading_order` path). Bank details paired with signatories line by line, as in the fixture, move to ticket 41 and stay read row by row; the fixture stays as a guard.
- **Mechanism:** one, ticket 32's. `_panel_columns` also takes a narrower column in the body's own type when both of these hold:
  - each side has fewer than about a third of its lines on the other side's baselines (25–29% on the agreement, 44% or more on the tables);
  - no block on one side starts on the row where a block on the other side starts. A block starts at a side's first line or after a gap of about 1.5 line pitches; starts within about a quarter box height share a row. Table rows start together (0.0–0.1); the agreement's blocks do not (0.44 at the nearest).
  Smaller-type panels keep ticket 32's rule unchanged. The thresholds are the implementer's, with a wide margin from the numbers above. Where either sign is weak, the region stays row by row.
- **Order:** the left column to its end, then the right, as for ticket 32's panel: no heading cue is needed. Each block stays whole.
- **Corpus:** one new synthetic document, with invented text: four headed blocks two by two on offset rows, as on the agreement, and as a control, a two-column unruled table of multi-line cells that start together, which must read row by row. Every existing file in `corpus/synthetic` stays byte-identical; the new document is the only change.
- **Tests:** the four blocks read column by column on an OCR page and on a text page drawn across; the unruled table with cells that start together, and the fixture's line-by-line pairing, read row by row. Every test in `NOT_BLOCKS_OR_PANELS` and the label–value tests still pass.
- **Final check on the samples,** on this machine only, numbers in the ticket and outputs deleted: all four files in `docs/example_pdf/`. Only the agreement's region may change. If anything else changes, stop and ask the user.
- **The known limitation** in `releases.py` drops this ticket and takes the wording agreed for ticket 41 (see there).
- **Estimate:** small to medium. The code change is a condition in `_set_in_smaller_type`; the cost is the new corpus document, the guard tests, and the four-file check.

**2026-11-11, built** (branch `fix/headed-blocks-side-by-side`)

**Code** (`columns.py`): `_set_in_smaller_type` is now `_body_and_side_panel`. A narrower column beside body text of three lines or more is a panel:
- in smaller type, by ticket 32's rule, unchanged;
- otherwise, when fewer than 35% of each side's lines share a baseline with the other side (`_OWN_ROWS`), and no block start on one side shares a baseline with a block start on the other. A block starts at a side's first line and at each line 1.5 of the side's box heights or more below the one before (`_BLOCK_GAP`, `_block_starts`). On the agreement, lines followed one another 0.85–1.09 box heights apart, and its blocks 1.70 and 2.25.
- **Changed from the triage wording:** the gap is measured in box heights, not the side's median line pitch. Code review found that on a side made mostly of one-line blocks, the median pitch is the gap itself, so no block after the first would start. Box heights give every such block its start, which only makes the guard stricter. The agreement's starts are the same either way.

**Tests** (`FakeEngine` on OCR pages, and the same lines drawn across on text pages):
- the four blocks two by two read one column after the other;
- a table of multi-line cells in one type whose rows start together, 25% of each side's lines on shared baselines, reads row by row. With the block-start guard switched off, it splits;
- a panel in the letter's own type on the letter's rows, its blocks starting below the letter's first line, reads row by row. With the shared-baseline guard switched off, it splits;
- the line-by-line fixture, renamed "bank details paired line by line with the signatories", still reads row by row (ticket 41).

**Corpus:** new `headed-blocks-scans`, two scans with invented text; every existing file in `corpus/synthetic` is byte-identical. With real PaddleOCR:

| Page | Rule off, as on `main` | This branch |
| --- | --- | --- |
| headed blocks two by two | 0.359 | 0.024 |
| unruled table, rows starting together (control) | 0.002 | 0.002 |

On the control, real OCR boxes put 38% of each side's lines on shared baselines, so both guards stop it there; the fast tests hold each guard alone. Its reference follows the printed lines, as a table without rules is read.

**Samples,** on this machine; OCR read each file once and the same boxes were converted with the rule off and on (the 110-page contract replayed from ticket 37's recording). Outputs and boxes deleted after.

| File | Pages | Changed |
| --- | --- | --- |
| five-page agreement | 5 | page 2 only, no character gained or lost |
| GIZ supplement | 34 | none |
| 10-page EGAT contract | 10 | none |
| 110-page contract | 110 | none |

On the agreement's page 2, checked by eye: each of the four blocks comes out whole, in its own paragraph, the left column before the right, and the account number follows its own heading, where it was joined into the signatory's title before.

**The known limitation** in `releases.py` now points to ticket 41 alone, with the wording agreed at triage. The release line is for the deploy.

**Not done:** the Linux container checks; CI runs them on the PR.

**2026-11-11, after code review**
- **Fixed:** block starts in box heights (above); the tests take the pages and their text from `corpus/generate.py` instead of copies; clearer names (`TRANSFER_AND_SIGNATORY_BLOCKS`, `_body_and_side_panel`, `cost_row_lines`'s lines).
- **Left:** "block" for a group of lines under a heading, as ticket 32's signature blocks already use it; the glossary's Column entry names the layout without a new term.
- **Checked after the fixes:** each guard's control still fails with that guard switched off; the agreement changes on page 2 only, as before, and the 110-page contract not at all.
