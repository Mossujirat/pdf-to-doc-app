# 25: Text under a diagonal watermark is lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On scanned copies that carry a large diagonal watermark, the OCR text under the watermark is missing from the output. Examples are a company registration certificate printed with the registry's mark, and an ID card copy with a line written across it. Whole list items vanish, or only fragments of them are left. Nothing marks the gap, and the summary does not show it. A reader, or an AI, takes the rest of the page for all of it.

**Blocked by:** none

**Status:** done

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`. Its attachments are scans pasted into Word pages. It was converted on 2026-10-23 with the user's permission.
- **A certificate's pages:** on six of them, the text under the watermark was lost. On one page, five of eight numbered items came out as fragments or not at all.
- **Two ID card copies:** the diagonal line across each was missing, as was much of the card's own text.

**Not yet known:** which stage loses the lines.
- The detector may not find lines crossed by the watermark.
- The recogniser may return nothing useful for them.
- Something after the engine may drop what it returned.

**To decide at triage**
- **Find the stage first,** on a synthetic scan with a diagonal watermark over known text.
- **Reduce the watermark's effect before reading,** for example by its colour or lightness, if the cause allows it.
- **Make the loss visible.** Where the page shows ink but nothing was read, the reader should be told, for example by uncertain text or a placeholder. A new placeholder kind is a glossary change.
- **Diagonal text itself:** it is not read while text-line orientation is off (see ticket 21).

## Comments

**2026-10-26, from implementing ticket 33 (lines lost on crisp OCR pages)**

- **A lead on the stage.** While checking ticket 33 on the samples, each OCR page was read twice: as rendered, and blurred with a standard deviation of 1.5 pixels. On three of the 110-page contract's scanned pages, the blurred reading had 3, 3 and 2 whole lines more. Checked by eye, those lines lie under a diagonal watermark. So at least there, the detector does not find the lines, or drops them, and a blur brings them back.
- **Why ticket 33 does not blur scans:**
  - On the corpus's synthetic scans, the blur raised CER a little, from 0.0072 to 0.0082.
  - On the samples' other scans, a blurred reading grouped the same text into rows differently, in tables and diagrams.

  Whether the blur, or something aimed at the watermark, should apply to scans is left to this ticket's triage.
- **The detector's box score is a likely stage.** Ticket 33 found that PaddleOCR drops a region whose mean probability over its enclosing rectangle is under `box_thresh` (0.6). That held for crisp pages; for watermarked scans it is not yet measured.

**2026-10-30, triage**

- **In the next deploy:** the user chose this ticket among the 6 to be done before it. See `.scratch/next-deploy.md`.
- **Next:** `/grill-with-docs`, then `/implement`.

**2026-10-31, grilling**

- **Measured with PaddleOCR:**
  - the 110-page contract's scans, of which pages 94–100 carry a certificate's diagonal watermark and pages 102–103 are ID card copies with a line across them;
  - synthetic scans with watermarks of several kinds;
  - the corpus's OCR pages (31 synthetic, 5 degraded) and the samples' other scans.
- **What the watermark is:**
  - The certificate is scanned in black and white at about 220 dpi, and its watermark is a 1-pixel checkerboard of dots, as dark as the text. It is neither lighter nor coloured.
  - Synthetic grey, light, dark, outlined, red, banded and pen-line watermarks lost no line. Only a dense 12-pt black-and-white page under a dot watermark lost one: CER 0.0225 → 0.0745.
- **The stage is the detector.** It shrinks the page to 1280 px without smoothing, so the dots turn into text-like blobs, which join lines together and break them apart. On pages 94–99, 20 lines are missing that a blurred reading finds:
  - 14 of them sit in regions that score 0.38–0.59, under `box_thresh` (0.6);
  - the rest merge with the watermark into one huge region, which scores 0.22 and is dropped whole.
  - The recogniser drops nothing, and neither does anything after the engine.
  - On the ID cards, a blur brings nothing back: the lost line is slanted (ticket 34).
- **Fixes measured.** Lines are rows of 15+ characters gained or lost on pages 94–103. "Other scans" means the samples' other scans.

  | Fix | Watermarked pages | Other scans | Corpus CER |
  | --- | --- | --- | --- |
  | **blur 2.0 where the detector sign fires** | **+21, −3** | **none changed** | **unchanged** |
  | blur 1.5 where the detector sign fires | +12, −2 | none changed | unchanged |
  | blur 1.5 where the image sign fires | +13, −2 | 8 photo and diagram pages changed; one loses 12% of its characters | unchanged |
  | blur 1.5 on every scan | +15, −2 | 107 of 111 changed | 18 pages changed |
  | blur 2.0 on every scan | +24, −4 | one page loses 38% | 0.0086 → 0.0524 |
  | despeckle (3×3 opening) | +17, −7 | one page loses 53% | 0.0398 |
  | `box_thresh` 0.5 | +8, −0; some added text garbled or doubled | 35 changed | 1 page changed |
  | `box_thresh` 0.3 | +23, −15 | not run | 1 page changed |

- **Two signs measured:**
  - **The image sign:** a large area that turns mid-grey once blurred. It catches every certificate page, but also 8 photo and diagram pages.
  - **The detector sign:** a region the detector dropped (score under 0.6) that is taller than 3 lines and wider than a quarter of the page.
    - It fires on pages 94, 96–99 and 102, on none of the samples' 101 other scans, and on no corpus scan.
    - It misses pages 95 and 100, which a blur helps by 1 and 0 lines.
    - Read from the probability map the detector already makes, it costs nothing, but `OcrEngine` does not expose that map today. As a separate pass, it costs 0.4 s a scan.
- **Decided**
  - **Fix:** where the detector sign fires, blur the scan with a standard deviation of 2.0 and read it again. Other pages are read as now.
  - **Cost:** a page that fires is read twice, about 2.7 s more. Reading the sign from the detector's own map is preferred; if PaddleOCR cannot give it, a separate pass costing 0.4 s a scan is accepted.
  - **Check at implement:** what the three lines lost on the watermarked pages are.
  - **Lines still lost are not marked** in this ticket. If the detector does not find a line, nothing knows it is there; marking is for the uncertain-text work in tickets 23 and 27.
  - **Diagonal text itself is not read** in this ticket. It moves to a new ticket, 34.
  - **Tests:**
    - in `corpus/synthetic`, a dense black-and-white scan under a dot-pattern watermark, the kind that loses lines, checked with real OCR to read in full;
    - a test that the sign does not fire on ordinary pages.
- **Glossary:** no new term. "Watermark" is used in its plain meaning.

**2026-10-31, implemented**

- **Where:** `PaddleOcrEngine.read` reads the page. When the detector dropped a region taller than 3 of the page's lines and wider than a quarter of the page, it reads the page again blurred by 2.0, and returns that reading. The `OcrEngine` interface is unchanged: the cause, a detector that shrinks the page without smoothing it, belongs to PaddleOCR.
- **The sign is free.** The engine wraps PaddleX's detector post-processing, so it also finds every region on the probability map already made, at a box threshold of 0.01. Both runs of that step took 25 ms a page at most, of a 1.4 s read. This reaches into PaddleX internals: `paddleocr` is pinned, and `uv.lock` holds PaddleX.
- **Every image the engine reads is checked,** not only scans, since the engine cannot tell them apart:
  - crisp OCR pages, already softened: the sign showed on none of the corpus's 27 or the samples' 9;
  - sideways and upside-down pages turned and read again: the same scans, turned;
  - the crop that tells which way a sideways page reads: it is about two lines tall, so it cannot hold a region three lines tall.
- **On the contract's pages 94–103,** checked locally (counted as text boxes of 15+ characters):
  - the sign shows on 94, 96–99 and 102, as measured while grilling;
  - 33 boxes gained and 3 lost, and the pages read about 2,600 characters more;
  - the 3 lost: a 76-character Thai line on page 94, read at 0.92 before; a 15-character Thai phrase on page 97; and 18 Latin letters on the ID card copy, page 102.
- **Tests changed from the grilling plan.** No synthetic page could be built that loses lines the way the certificate does, into a region merged with the watermark. Grey watermarks lost nothing. Dot patterns either lost lines one by one, each just under the threshold and without the sign, or showed the sign and lost nothing. With the user's agreement, in `tests/test_paddle.py` (real OCR):
  - a black-and-white scan under large letters filled with a 1-pixel checkerboard is read again, and comes out as its blurred copy reads. Whether such a page shows the sign hangs on its text and the letters' size, so this test guards the reach into PaddleX, not the lines gained;
  - no scan in `corpus/synthetic` or `corpus/degraded` is read twice.
- **From code review:** the step added to the detector holds the list it fills, not the engine, so the engine is still freed as soon as a conversion drops it.
