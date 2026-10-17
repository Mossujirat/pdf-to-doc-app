# 08: OCR pages with PaddleOCR

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Scanned pages are read automatically, so a user never gets an empty output. A file that mixes text pages and scans is handled page by page. While OCR runs, the CLI shows progress such as "OCR page 23/85". This ticket introduces three things:
- the OCR engine interface, the second seam
- the PaddleOCR adapter as the default engine
- a fake engine for tests

**Blocked by:** 06

**Status:** ready-for-agent

**Branch:** `feat/ocr`

**Page classification**
- [ ] Each PDF page is classified as a text page or an OCR page.
- [ ] Character count alone never decides. A page with a stamped header line over a scanned body is an OCR page; image coverage and body-text coverage decide.

**PaddleOCR adapter**
- [ ] Pin paddlepaddle 3.2.2; version 3.3.1 crashed at inference.
- [ ] Use the PP-OCRv5 mobile detector, with the detector input limited to a longest side of 1280 px.
- [ ] Use the Thai and English mobile recognisers.
- [ ] Turn off orientation and unwarping.
- [ ] Bake the models into the Docker image.

**OCR output**
- [ ] OCR text goes through the same Thai repair as text pages.
- [ ] Lines are grouped into paragraphs, and stamped headers on scans are removed as in ticket 03.

**Summary and progress**
- [ ] The summary lists the OCR pages and the engine used.
- [ ] The conversion function accepts a progress callback (stage, current page, total pages), and the CLI shows it.

**Mixed Thai–English lines**
- [ ] Find out whether the Thai recogniser reads English words and digits on the same line correctly.
- [ ] If it does not, choose and implement a strategy (for example, running both recognisers and choosing per line), and record the finding in the ticket's comments.

**Tests**
- [ ] Fast tests use the fake engine to cover page routing for: a text page, an image-only page, a stamped header over a scan, and a mixed file.
- [ ] Corpus tests run real PaddleOCR in the container on synthetic simulated scans with known text, and record CER.
- [ ] A 110-page mixed document converts in default mode within roughly 15 minutes on an ordinary CPU. Record the measured time, and whether it was measured on Windows or Linux.
