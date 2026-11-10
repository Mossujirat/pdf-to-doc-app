# 42: Single lines are lost on clean scans

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On a clean scan, with no watermark, one whole line of a contract clause is missing from the output. Nothing marks the gap, and the summary does not warn. A reader, or an AI, takes the clause for complete. This is broken text (missing text).

**Blocked by:** none

**Status:** done

**Branch:** `fix/single-lines-lost-on-clean-scans`

**Seen on:** a 10-page scanned Thai research-funding contract among the local samples in `docs/example_pdf/`. It was converted on 2026-11-10 with the user's permission. Every page is a 300-dpi scan, upright and clean.

**What is known so far (measured)**
- **The line is clean.** It is printed like the lines around it, starts at a paragraph indent, and has wide gaps between its words.
- **The detector finds the line.** It scores the region 0.59, just under `box_thresh` (0.6), and drops it before it is read. The recogniser and the later steps drop nothing.
- **A blur brings it back.** With the page blurred at a standard deviation of 1.0 or 1.5 pixels, the line is read in full and spelt right.
- **Tickets 33 and 25 fixed the same stage in other cases. Neither covers this one.**
  - **Ticket 33** blurs only OCR pages that are not scans. It kept scans as they were "unless the samples show that real scans lose lines the same way". This sample shows that.
  - **Ticket 25** re-reads a page blurred only when a dropped region is taller than 3 lines and wider than a quarter of the page. This region is one line tall.
  - **Ticket 25 already saw this case.** While grilling, 14 of the 20 lines lost on the watermarked pages lay in regions of one line that scored 0.38–0.59. Its synthetic dot patterns also "lost lines one by one, each just under the threshold and without the sign". Its fix covered only the tall-region sign.
- **Lowering `box_thresh` is ruled out.** Ticket 25 measured 0.5: 35 of the samples' other scans changed, and some added text came out garbled or doubled.
- **Regions the detector dropped across this file:**

  | Page | What | Height | Width | Score |
  | --- | --- | --- | --- | --- |
  | 8 | the lost line | 99 px, about 1.5 times a line | 56% of the page | 0.59 |
  | 1 | the logo | 422 px | 34% | 0.17 |
  | 3, 7 | dotted signing lines | 19 px | 2–5% | 0.49–0.52 |
  | 10 | a signature and a dotted line | 19–116 px | 2–6% | 0.50–0.52 |

  A sign for "a dropped region shaped like one line of text" (about one line tall, wide, and scored near the threshold) would fire on page 8 only.

**To decide at triage**
- **The sign,** and its limits on height, width and score, measured on:
  - the samples' other scans;
  - `corpus/synthetic` and `corpus/degraded`, where no scan should change.
- **The fix:** re-read the whole page blurred, as ticket 25 does, or read only the dropped region. Which blur to use: ticket 25 uses 2.0, and here 1.0 and 1.5 worked.
- **Cost:** a page that fires is read twice, about 5 s more on this machine.
- **Making a loss visible.** Ticket 25 decided that "lines still lost are not marked", and left it to tickets 23 and 27. Neither took it up. With this sign, the converter knows a line is there. If the second reading still misses it, should the summary warn?

## Comments

**2026-11-10, grilled**

**Measured first,** with the user's permission, on this machine, without a sub-agent. The corpus (31 files) and the four local samples were read, about 135 OCR pages of samples. Only numbers are kept here. Each region the detector dropped was compared with the page's lines. A reading blurred by 1.5 showed what lay in it.
- **46 dropped regions look like a line:** 0.5–2.5 of the page's lines tall, and at least 5% of the page wide.
  - **13 repeat text already read.** They are cells and diagram labels that the kept boxes cover. Adding them would double the text.
  - **15 give nothing when blurred.** They are highlight bands, rules and signatures.
  - **18 give new text:**
    - this file's lost line;
    - a signing line;
    - a chart's axis of years;
    - about 11 pieces on the 110-page contract's watermarked pages, which ticket 25 left. Most are garbled, but they are real text;
    - 5 pieces of junk read from signatures, at a confidence of 0.24–0.60;
    - a lone "o".
  - The real text read at 0.67 and above, at 0.7 and above all but one piece.
- **The detector's score does not separate them.** Real text and junk both scored 0.40–0.60.
- **Cost:** 19 of the samples' OCR pages would be read again, about 15% more time on the 110-page contract. Two corpus pages, both upside-down scans, would be read again too.
- **Reading only the dropped region,** with the recogniser alone, took 0.34 s. It dropped a letter from this file's line, at a confidence of 0.98, so nothing would mark it. A blurred reading of the page read the line exactly.

**Decided with the user**
1. **The sign:** a region the detector dropped (score under 0.6) that is 0.5–2.5 of the page's lines tall, and at least 5% of the page wide. It is checked on every image the engine reads, as ticket 25's sign is. When ticket 25's sign has fired, it is checked on the reading the engine returns.
2. **The fix:** read the page again, blurred by 1.5, and add only the new boxes:
   - each lies mostly inside such a region;
   - none overlaps a box already read;
   - each is read at a confidence of 0.7 or more, with 2 characters or more.

   Every other line stays as first read.
3. **Recovered lines are marked as any other text is.** The detector's low score says where the line is, not how well it reads, so the whole line is not marked uncertain.
4. **No warning when nothing is recovered.** Most such regions are not lost lines, so ticket 25's decision stands.
5. **A known limitation at the release:** a line on a scan can still be lost unmarked. It points at this ticket. The Thai wording is agreed at the deploy.
6. **Tests:**
   - first, try to build a corpus scan that loses a line, time-boxed to half a day;
   - failing that, test the sign on recorded region geometry, which holds no contract text;
   - either way, no corpus page may read differently.
7. **Check on the samples:** about 17 pieces recovered, no junk added, and the 110-page contract about 15% slower at most. Only counts are recorded, and outputs are deleted after.
8. **The exact limits** (heights, width, confidence) may move at implement, as long as the checks above hold.
- **Glossary:** no new term. **ADR:** none, as the choice is easy to reverse.

**2026-11-10, implemented on branch `fix/single-lines-lost-on-clean-scans`**

- **Where:** `PaddleOcrEngine.read`, after ticket 25's watermark check.
  - `lost_lines` finds the regions the detector dropped that are shaped like a line.
  - The page is read again, blurred by 1.5.
  - `recovered` keeps only what that reading found in those regions, read at a confidence of 0.7 or more, with 2 characters or more, and not over a box already read.
  - Each comparison uses the area of the detector's own four-cornered boxes, so a page fed in askew compares the same way.
- **The boxes first read keep their bounds.** The page's slant is still measured on the first reading alone. Measured on every box, a recovered line moved the slant, and all 19 boxes of one corpus page moved with it.
- **No synthetic page loses a line this way.** About 180 variants were tried: Sarabun and Niramit, 12–17 pt, black and grey ink, JPEG quality 60–90, noise, slant, line gaps. None lost a whole line. The only regions dropped were upper marks boxed on their own, on pages in 17-pt type whose lines ran off the page. So, as decided, the tests are:
  - **`tests/test_lost_lines.py`, fast:** the sign and the filters, on region geometry shaped as the samples' detector found it. No contract text is used.
    - a line-tall region across the page is a lost line;
    - dots, a logo and a one-word region are not;
    - a kept region is not;
    - a line found in a lost line is recovered alone;
    - text read already is not recovered again;
    - text found outside every lost line is not recovered;
    - junk read unsurely, and a lone letter, are not recovered.
  - **`tests/test_paddle.py`, real OCR:** the corpus test that no scan is read twice is now two checks on every corpus page with an image.
    - With lost lines turned off, no page is read again for a watermark.
    - With them on, the boxes first read are unchanged, and everything added is in the page's reference text.
    - It adds one box today: a table header cell on `rotated-text-pages` page 1, which the detector dropped. That page converts as a text page, so outputs do not change.
  - **Checked by breaking the code on purpose:** each of the six filters fails a fast test. Recovering nothing, or measuring the slant on every box, fails the corpus test.
- **Harness:** `corpus/synthetic` and `corpus/degraded` give the same reports with and without the change.
- **The samples,** converted on this machine with the user's permission. Only counts are recorded here, and the outputs are deleted.

  | Sample | Output | Time the re-reads add |
  | --- | --- | --- |
  | 10-page contract (this ticket) | its lost line is back, joined into its paragraph; nothing else changed | 2 re-reads, 6 s, 16% |
  | 110-page contract | 17 rows added, 7 rearranged, none lost. Added: a signing line; a chart's axis of years; a form's field label; phrases on the watermarked pages, the garbled ones marked uncertain. No unmarked junk. | 16 re-reads, 55 s, 12% |
  | GIZ supplement | unchanged | 2 re-reads, 14 s, 7% |
  | five-page agreement | unchanged | none |

  - **How the time was measured:** the time of the re-reads themselves. Timing whole conversions twice gave +23% and −15% on pages with no re-read, so that measure is noise.
  - The 10-page contract runs a point over the 15% agreed: a short file and two re-reads.
- **Checks:** mypy; pytest (740 passed, 1 skipped); `pytest -m ocr` (27 passed).
- **Left for the release:** the known limitation decided above, that a line on a scan can still be lost unmarked. Its Thai wording is agreed at the deploy.

**2026-11-10, after code review (two axes)**

- **Spec, decided with the user:**
  - **The corpus test names what is added.** Decision 6 said no corpus page may read differently. One page does: the header cell "จำนวนเงิน" on `rotated-text-pages` page 1, which the detector dropped, comes back. The page converts as a text page, so outputs and the harness are unchanged. The test now:
    - requires every box first read to stay as it was;
    - requires that cell to be the only box added across the corpus.

    This replaces a looser check that any added text appear in the page's reference text.
  - **Overlap with boxes already read is summed.** A box is not recovered when half of it or more lies inside the boxes first read, all together, not inside any one of them. That catches a box that lies a third inside each of two lines.
  - The width limit is now "at least 5%", as decided, not "more than".
- **Standards, fixed:**
  - `_line_height`, shared with ticket 25's `_watermarked`;
  - `Reading` is a `NamedTuple`, and `Region` names the detector's region with its score;
  - clearer local names in `read`;
  - one helper for a blurred reading;
  - every constant's comment says where its value comes from.
- **Recorded, not changed:**
  - **The sign also runs on the crops `_sideways_turn` reads, and on `_read_upright`'s turned page.** A recovered box counts towards the confidence that decides which way a page reads. The harness, which converts the corpus's upside-down and sideways scans through those steps, gives the same reports.
  - **The corpus test checks two things,** to save a third OCR pass over the corpus. It is also the only test that uses `monkeypatch`.
  - **"Lost line" is not added to the glossary.** It names an engine step, not something a reader of the output meets.
- **Checked after the fixes:**
  - The two samples that changed give the same outputs as before the review.
  - pytest (741 passed, 1 skipped); `pytest -m ocr` on `test_paddle.py` (14 passed); mypy.
