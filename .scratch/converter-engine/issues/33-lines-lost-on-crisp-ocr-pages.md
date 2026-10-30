# 33: Lines are lost on OCR pages that are not scans

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** An OCR page that is not a scan is rendered from the PDF, so its image is crisp. These are pages whose text layer cannot be trusted, and pages whose text is drawn as shapes. On such a page, PaddleOCR's detector finds some lines and then throws them away before they are read. The line is missing from the output. Nothing marks it, and the summary does not warn. This is broken text (missing text).

**Blocked by:** none

**Status:** done

**Found while grilling ticket 14 (2026-10-25),** on synthetic pages. The test set was four table pages, each built twice: once with a wrong ToUnicode map, and once with text and rules drawn as shapes.
- On all eight pages, the line printed just above the table was lost: "ผู้รับทุนต้องส่งงานตามกำหนดเวลาในตารางนี้".
- The same pages built as 200-dpi scans read it.

**Why it goes wrong (measured)**
- **The detector finds the line.** In the line's core, its mean probability is 0.61, the same as the line above it (0.60).
- **Then it scores the region and drops it.** PaddleOCR scores each region by the mean probability over its smallest enclosing rectangle, and drops a region that scores under `box_thresh`, 0.6.
  - The lost line scored 0.54–0.58 on all eight pages; the line above scored 0.79–0.92.
  - Thin spurs, where the upper marks of ผู้ and นี้ join the text, stretch the rectangle to about twice the text's height, so half of it is blank.
- **The table's rule is not the cause.** The rectangle ends 8 pt above it.
- **What decides it is how sharp the image is.** When the image is softened before the detector shrinks it to 1280 px, the line scores over 0.6:

  | Softening | Score of the lost line |
  | --- | --- |
  | Gaussian blur, sigma 1 px | 0.64–0.78 |
  | shrink with `INTER_AREA` instead of the default | 0.61–0.77 |
  | render at 200 dpi | 0.64–0.75 |
  | whiten every rule (no softening) | 0.60–0.70, borderline |

  With `text_det_box_thresh` at 0.3, the line also comes back, and reads exactly.
- **CER** on those eight pages was 0.21 today, and 0.05 with the blur.
- **Scans got worse with the blur.** On the corpus's 12 OCR pages, CER rose from 0.0072 to 0.0082 with the blur, and to 0.0091 at 200 dpi. On stamped-scans page 1, it rose from 0 to 0.021. So the softening belongs on pages that are not scans. That is inferred: softening only those pages has not been tested.
- **The real samples have such pages:** pages 69–72 of the 110-page contract, whose text layer cannot be trusted, and all five pages of the agreement printed to PDF with its text drawn as shapes. How many lines they lose has not been counted.

**Decided with the user (2026-10-25, grilling ticket 14)**
- **A ticket of its own, done before ticket 14.** The cause is the rendering, not tables. Ticket 14's check on real table pages needs every line there.
- **Scope:** OCR pages that are not scans. Scans keep today's image, unless the samples show that real scans lose lines the same way. The samples' scans are 300-dpi JPEGs, sharper than the corpus's.
- **How:** soften the image of those pages before it is read. Which softening is the implementer's choice, made with the harness. Lowering `box_thresh` is the alternative; measure the junk boxes it adds.

**To do**
- [x] A synthetic corpus document with OCR pages that are not scans: one with a wrong ToUnicode map, one with text drawn as shapes. Each holds a line that is lost today, and has reference text.
- [x] A real-OCR test (`pytest -m ocr`) that reads that line.
- [x] Run the harness on `corpus/synthetic` and `corpus/degraded`. No scan page may change.
- [x] Pages must take no longer to read.
- [x] Final check on the local samples, with permission asked at /implement:
  - count the lines lost on pages 69–72 and on the agreement's pages, before and after the fix;
  - check whether the samples' scans lose lines too.
  - Nothing of them is committed or put in a ticket, apart from counts.

**Also seen, not decided here.** On these pages, 14 of 15 small junk boxes, such as "ญ ญ", "ว ญ 9" and "e A", are upper marks. The detector boxed each one apart from the line below it, and that line's reading already holds the marks. They are marked uncertain today. They land inside table cells too, so the grilling of ticket 14 takes them up.

## Comments

**2026-10-26, implemented on branch `fix/lost-lines-on-crisp-pages`**

- **What changed**
  - An OCR page that is not a scan is blurred before it is read: a Gaussian blur with a standard deviation of 1.5 pixels at 300 dpi.
  - Which pages are scans is decided by the same test kept images uses: judged by the text a reader sees, the page would be read with OCR, and what it shows outside that text lies mostly in its images. It is now `reading._is_scan`, and runs for every OCR page, not only with images kept.
  - The test runs before an untrusted text layer is dropped.
    - A searchable scan whose hidden text cannot be trusted is still a scan, and is not blurred.
    - With images kept, every scan is kept, so every page read with OCR is blurred.
  - OpenCV is now a direct, pinned dependency (4.10.0.84, Apache-2.0). PaddleOCR already installed it, so nothing new is installed.
- **Why 1.5 (measured)**
  - On a contract page of eight lines, the fifth was lost with no blur, with a blur of 1.0, and when the page was rendered at 200 dpi. A blur of 1.5 or 2.0 read every line, and left no junk box.
  - Lowering `box_thresh` to 0.5 or 0.3 brought the line back, but added 3–6 junk boxes a page.
  - On the grilling's table pages, a blur of 1.0 or 1.5 read every line, but 2.0 lost lines again:

    | Blur | CER, untrusted / drawn table pages |
    | --- | --- |
    | none | 0.216 / 0.210 |
    | 1.0 | 0.053 / 0.050 |
    | 1.5 | 0.048 / 0.045 |
    | 2.0 | 0.181 / 0.129 |

  - 10-pt text read with one more error at 1.5 than with no blur: CER 0.008 against 0.004.
  - **The likely mechanism (inferred, not measured):** the detector shrinks a 300-dpi A4 page about 2.7 times without smoothing it first, so thin strokes alias. Smoothing before such a shrink needs a standard deviation of about 1.1–1.4 pixels.
  - **Larger pages:** a page larger than A4 is shrunk more, and may need more blur. That has not been tested.
- **The "line just above a table" was not about tables.** A plain page of clauses lost a line too. Whether a line is lost depends on where it falls: the five clauses alone lost none.
- **Corpus**
  - `wrong-unicode-map` gained a second page: the clauses with the line that was lost.
  - The new document `text-drawn-as-shapes` holds the same page, drawn as shapes.
  - Harness results:

    | Page | CER |
    | --- | --- |
    | `wrong-unicode-map` page 1 | 0.016 before, 0.0040 now; its junk box "9e" is gone too |
    | `wrong-unicode-map` page 2 | 0.0025 |
    | `text-drawn-as-shapes` | 0.0050 |

  - Every scan in `corpus/synthetic` read exactly as before.
  - `corpus/degraded`, all scans, also read as before: CER 0.0121, 14 uncertain stretches, 62% of errors unmarked, as ticket 11 recorded.
- **Time:** the blur took 16–21 ms a page, and judging whether a page is a scan 1–62 ms. A page takes 1–5 s to read.
- **Tests**
  - **`test_ocr_pages.py`, with `FakeEngine`:**
    - a page with an untrusted text layer, and a page drawn as shapes, reach the engine softened, with images read or kept: no step between neighbouring pixels over 100 grey levels;
    - a scan, a searchable scan whose hidden text is wrong, and a scan over wrong text it hides, reach it sharp: a step over 150.
  - **`test_paddle.py`:** every line of the eight-line page is read, in both forms.
  - **Checked by breaking the code on purpose:**
    - with no blur, the PaddleOCR tests and the softening tests fail;
    - with every page blurred, the scan tests fail.
- **Checks:**
  - Windows: pytest (550), mypy, `pytest -m ocr` (17) and the harness.
  - The Linux image, with `src`, `tests`, `corpus` and `scripts` mounted: the same, all passing, with the same CER to the last digit.
- **The local samples,** converted on this machine with the user's permission. Each OCR page was read both as rendered and blurred, and every row that one reading had and the other lacked was checked by eye. The outputs were deleted after.
  - **The nine OCR pages that are not scans** (the agreement's five, and pages 69–72 of the contract) lost no line, either way: 156 rows each way on the agreement, and 141 against 140 on pages 69–72.
    - The one difference on pages 69–72 is a junk "i" read from a hatched cell, which the blur removes.
    - The agreement's only differences are its signatures read as junk.
    - So the fault did not show in the samples. The fix changes nothing there but junk.
  - **Scans, which are not blurred:**
    - Read blurred, three of the contract's scanned pages gained 3, 3 and 2 whole lines that lie under a diagonal watermark. That is ticket 25's fault, not a crisp render, so scans keep today's image here; ticket 25's Comments have the numbers.
    - The other differences on scans were the same text grouped into rows differently, in tables and diagrams.
  - **Time:** the agreement's pages took 4.5 s each as rendered and 4.2 s blurred; pages 69–72 took 7.4 s and 7.7 s. Another job was running at the same time, so these are rough.
- **Scans stay as they are, confirmed by the user on 2026-10-26.** The ticket's rule was that scans keep today's image unless the samples show they lose lines the same way. On the samples, the scans' lost lines come from a watermark, not from a crisp render. Blurring every scan would change how all of them read, so the watermark goes to ticket 25.

**2026-10-26, after code review (two axes)**

- **Standards:** no rule broken. Fixed:
  - the tests take the page from the corpus generator (`CRISP_PAGE`) instead of copying it;
  - a name that meant two things in one test;
  - the thresholds in the softening tests now cite what was measured: 68 grey levels softened, 255 for a 300-dpi scan, 172 for the corpus's 200-dpi scans;
  - `_kind`'s docstring now points to `_is_scan` instead of repeating it;
  - the corpus README's new line describes what is drawn.
  - Left as it is: the two test files each build an untrusted page and a drawn page in one line of their own.
- **Spec:** implemented as asked. Added:
  - the softening test also runs with images kept;
  - the scan test also covers a scan drawn over wrong text that it hides;
  - the run on `corpus/degraded`, recorded above.
- **Left as it is:** without images kept, judging whether an OCR page is a scan renders the page at 50 dpi a second time. It costs 1–62 ms a page.
