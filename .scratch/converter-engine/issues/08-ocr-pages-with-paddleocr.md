# 08: OCR pages with PaddleOCR

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Scanned pages are read automatically, so a user never gets an empty output. A file that mixes text pages and scans is handled page by page. While OCR runs, the CLI shows progress such as "OCR page 23/85". This ticket introduces three things:
- the OCR engine interface, the second seam
- the PaddleOCR adapter as the default engine
- a fake engine for tests

**Blocked by:** 06

**Status:** done

**Branch:** `feat/ocr`

**Page classification**
- [x] Each PDF page is classified as a text page or an OCR page.
- [x] Character count alone never decides. A page with a stamped header line over a scanned body is an OCR page; image coverage and body-text coverage decide.

**PaddleOCR adapter**
- [x] Pin paddlepaddle 3.2.2; version 3.3.1 crashed at inference.
- [x] Use the PP-OCRv5 mobile detector, with the detector input limited to a longest side of 1280 px.
- [x] Use the Thai and English mobile recognisers.
- [x] Turn off orientation and unwarping.
- [x] Bake the models into the Docker image.

**OCR output**
- [x] OCR text goes through the same Thai repair as text pages.
- [x] Lines are grouped into paragraphs, and stamped headers on scans are removed as in ticket 03.

**Summary and progress**
- [x] The summary lists the OCR pages and the engine used.
- [x] The conversion function accepts a progress callback (stage, current page, total pages), and the CLI shows it.

**Mixed Thai–English lines**
- [x] Find out whether the Thai recogniser reads English words and digits on the same line correctly.
- [x] If it does not, choose and implement a strategy (for example, running both recognisers and choosing per line), and record the finding in the ticket's comments.

**Tests**
- [x] Fast tests use the fake engine to cover page routing for: a text page, an image-only page, a stamped header over a scan, and a mixed file.
- [x] Corpus tests run real PaddleOCR in the container on synthetic simulated scans with known text, and record CER.
- [x] A 110-page mixed document converts in default mode within roughly 15 minutes on an ordinary CPU. Record the measured time, and whether it was measured on Windows or Linux.

## Comments

**2026-10-19, implementation notes**

- **Seams.**
  - `convert(..., ocr=engine, progress=callback)`.
  - The engine interface, `OcrEngine`, has one method: `read(image, languages)`. It returns `TextBox`es, each with text, a box in image pixels and a confidence. Table structure comes with ticket 14.
  - `tests/fake_ocr.py` holds `FakeEngine`, which lays out the lines it was given the way `pdf_builder` draws them, and `BlankEngine`, which reads nothing.
  - The default engine is PaddleOCR. It is loaded when the first page needs OCR, and kept for the rest of the process. Start-up takes about 8 s: 7 s to import Paddle and 0.8 s to load the models.
- **Which pages are OCR pages.**
  - The body is the page outside the 10% edge bands.
  - A page is an OCR page when its text layer covers less than 5% of the page in the body, and the body shows more ink outside the text layer's rows than the text itself covers. Ink is measured on a 50 dpi grey render: any pixel darker than 245 counts.
  - A scan holding a single word is still read. A blank page is not. A scan made searchable has a text layer covering its body, so it is read from that layer.
  - Image coverage alone did not work on the real files:
    - The contract's scans cover only 50–60% of the page, because the scan sits inside margins.
    - The English sample's OCR pages contain no images at all. Their text is drawn as 223–2,633 vector paths.
  - Result on the real contract: the text pages are exactly 1–11, 65–67, 69–74, 79–80 and 87. Pages 68 and 75 are OCR pages: each is a large image with a line or two of text.
  - On the English sample, all five pages are OCR pages. Page 5's text layer holds 5 rows, and those are kept exactly. OCR adds 18 boxes from the rest of the page, 16 of them long lines read with confidence 0.92–1.0. That printed text is not in the text layer at all. The other 2 boxes are 2 characters each, read at about 0.36 from signatures: placeholders (ticket 09) and uncertain text (ticket 11) will deal with those.
- **From boxes to text.**
  - A page is rendered at 300 dpi. The engine's boxes are grouped into printed lines.
  - Each line becomes a row shaped like a text-layer row, so the paragraph, list and page-furniture rules of tickets 01–03 apply unchanged. Thai repair applies through them.
  - The font size is the box height divided by 1.5, one size per page. A line at least 1.2 times taller than usual keeps its own size, so a title stays apart from the paragraph below it.
  - Headings are not detected on OCR pages: an estimated size cannot tell them apart. Heading levels come from text pages only.
- **Text over a scan.**
  - On an OCR page, every text-layer row is kept, because it holds its text exactly: a stamped header, a note stamped in the body, or a caption. The engine's boxes that cover a text-layer row are dropped, one box at a time.
  - The furniture rules of ticket 03 then remove a stamped header.
  - In the tests, the engine misreads a stamp, and the exact stamp still comes out. The scan's own letterhead on the same printed line as a stamp is kept.
  - A page whose text layer fails validation (ticket 10) must pass no text-layer rows here.
- **Pages fed in askew.** The adapter turns the detector's boxes back by the page's slant, the median slant of the wide boxes' top edges, before taking their bounds. Without that, a scan 3° askew came out with its lines out of order (CER 0.71, found in review). A real-OCR test now reads scans at −3° and +3° in order.
- **Thai and English on one line.**
  - The Thai recogniser read English words, digits and brackets on the same line correctly on synthetic scans.
  - On the English sample's scans, it agrees with the English recogniser on 99.3–99.8% of characters.
  - The English recogniser cannot read Thai at all.
  - So only the Thai recogniser is used, for both languages. The English model is not shipped.
  - This departs from the spec's "Thai and English mobile recognisers". The user accepted it on 2026-10-19, and the spec's OCR adapter section now says so.
- **Models.**
  - The detector and the Thai recogniser come from Hugging Face (`PaddlePaddle/<model>`, Apache-2.0), pinned to a commit, and each file is checked against its SHA-256. Together they are 13 MB.
  - `pdf-to-doc-models` fetches them into `~/.cache/pdf-to-doc/models`, or into `$PDF_TO_DOC_MODELS`.
  - A conversion never downloads. If the models are missing, the CLI says how to fetch them and exits with code 9.
  - PaddleX's check that its model hosts are online is turned off. Paddle's own log lines and its ccache warning are kept out of the output. Only on Windows, importing Paddle still prints "INFO: Could not find files for the given pattern(s)."
- **Docker.**
  - The models are fetched at build time into `/opt/pdf-to-doc/models`.
  - The image adds OpenCV's system libraries and OpenMP.
  - PaddleX keeps its working files in `/tmp/paddlex`.
  - The image grew from 116 MB to 566 MB.
- **Harness.**
  - The engine column is filled in.
  - Totals are reported for all pages, for text pages and for OCR pages.
  - `--max-cer` and `--max-broken` now gate text pages only, matching the spec's "zero broken text on text pages". OCR pages are measured, and their gate comes with ticket 17.
- **Tests.**
  - The fast suite uses the fake engine. It covers a text page, an image-only page, a header stamped over scans, a note stamped in a scan's body, a letterhead beside a stamp, a mixed file, a scan made searchable, a blank page, Thai repair and paragraphs on OCR text, a larger title, progress, the summary, the CLI's progress and missing models.
  - Real PaddleOCR tests are marked `ocr`. They are left out of the default run and run with `pytest -m ocr`, in CI too.
  - CER on the corpus scans: `scanned-page` 0.69% (0.90% on Thai only; "ที่" read as "ที"), and 0 on the other three pages. The results are identical on Windows and Linux. The test fails any OCR page above 5%.
- **Corpus.**
  - Three documents with four scanned pages, drawn as 200 dpi grey JPEGs, turned 0.4°, with grain of 6 grey levels. They add about 1 MB.
  - Generated on Linux, they are byte-identical to the Windows files.
- **Time on the real 110-page contract, default mode, CPU only** (Ryzen AI 7 350, 16 logical CPUs; local, never uploaded):

  | Where | Total | OCR pages | Per OCR page |
  |---|---|---|---|
  | Windows | 360 s (6.0 min) | 87 | 4.1 s |
  | Linux container (Docker Desktop on the same machine, no network, read-only) | 353 s (5.9 min) | 87 | 4.0 s |

  Both outputs are 210,005 characters. Measured after the review changes; an earlier run of the same machine gave 380 s and 306 s. The 5-page English sample takes 41 s on Windows and 43 s on Linux. Its output grew from 319 to 11,365 characters.
- **Broken text on the real contract.**
  - The output has 18 orphan marks, all after a character that is not a Thai consonant: a Latin letter (8), a dash or punctuation (4), a digit (1), or a space after one of those (5).
  - In a 10-page sample, no box starts with a mark. So these marks come from the engine misreading the consonant, not from how boxes and lines are joined.
  - Marking such text is ticket 11. Measuring OCR quality is ticket 17.
- **Left open:**
  - Headings on OCR pages (see above).
  - Progress covers the OCR stage only.
  - PaddleX writes working files to `~/.paddlex` (locally) or `/tmp/paddlex` (in the image). Ticket 12 must clear them.
  - CI builds take longer, because they install Paddle.

**2026-10-19, changes after code review**

- **A scan with a note stamped in its body was read as a text page.** Two text-layer lines in the body passed the old 1% rule, and the scan itself was lost. Now a page needs a text layer covering 5% of the page, or ink outside its text no greater than the text, to stay a text page.
- **The stamp rule dropped real scan text.** It dropped a whole printed line when one box on it overlapped a stamp. Now each box is checked on its own, and every text-layer row on an OCR page is kept, not only those in the edge bands.
- **Scans fed in askew** are straightened in the adapter (see above).
- **Tidying.**
  - The page check is called `_needs_ocr`, following the glossary: an OCR page need not be a scan.
  - `models.py` is renamed `ocr_models.py`, apart from `model.py`, the document model.
  - The default engine and its cache moved to `paddle.py`, and `PaddleOcrEngine` takes the models folder.
  - The body-text measure moved to `layout.py`. Furniture and the body now share one definition of the edge bands.
  - A page's kind is held in `PageRows.kind`, not in a flag.
  - The three copies of the UTF-8 console setup became `console.thai_safe_output`.
  - `ModelsMissing` is exported.
- **Not changed:**
  - Tests still check what the fake engine was asked to read, because the engine is one of the two agreed seams.
  - Thai marks in the new tests are written with `chr()`, which the file tools cannot mangle.
  - The harness gate on text pages stays. Without it, CI would fail as soon as an OCR page held broken text, while the spec's gate is zero broken text on text pages.

**2026-10-19, CI runs less often**

- With Paddle in the image, a CI run takes several minutes, and this private repository has a monthly quota of Actions minutes. At the user's request, CI now runs for pull requests and for pushes to `main` only. A newer push to the same pull request cancels the run in progress.
- While a ticket is in progress, the same checks run locally in the image. That supersedes ticket 06's "each push and pull request".

**2026-10-20, changed in ticket 10**

- A line whose boxes were at least 1.2 times the usual height got a font size of its own, to keep titles apart. On 15 of the contract's scanned pages, 19% of body lines were that tall, because of marks above and below the letters. Each of them started a new paragraph, cutting sentences in two.
- Every line of an OCR page now gets the page's one size, and paragraphs on OCR pages are split by spacing alone. A title with no extra space below it runs into the paragraph under it.

**2026-10-20, changed in ticket 12**

- The PaddleOCR engine is no longer kept for the rest of the process. Its predictors held the last OCR page and what was read from it until the next page was read.
- Each conversion now loads its own engine when its first OCR page needs one, and drops it when the conversion ends. Loading again takes under a second; importing Paddle still happens once per process.
