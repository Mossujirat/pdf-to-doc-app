# 02: The layout model finds the pictures

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decisions 2 and 6 of its comment of 2026-11-12.

**What to build:** Real conversions find pictures in scans with PaddleX's PP-DocLayout_plus-L, so the placeholders of ticket 01 appear on real scanned documents, on the CLI and on the web.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/pictures-inside-scans`

**The model**
- [x] **Pinned as the OCR models are:** its name, its Hugging Face commit, and the SHA-256 of each file. It is Apache-2.0, published by PaddlePaddle.
- [x] **`pdf-to-doc-models` fetches it** with the OCR models.
  - A conversion never downloads anything.
  - A missing model fails the same way a missing OCR model does.
- [x] **Loaded fresh for each conversion,** as the OCR engine is, so it keeps nothing of the conversion before. Paddle's online model check and its own log lines stay off.
- [x] **Its classes:**
  - "image", "chart" and "seal" regions are pictures;
  - every other class is ignored;
  - the score threshold is the model's own, unless the corpus shows a reason to change it. Record it in Comments.
- [x] **The Docker image and CI fetch it too.** Record how much it adds to the image.

**Corpus**
- [ ] ~~**A new synthetic document:** a signing page, scanned, with reference text.~~ Moved to ticket 03 by the user; see Comments. It holds:
  - a photo;
  - a signature in blue ink beside a row to sign on;
  - a red stamp;
  - a logo at the top.

  The pictures the generator already draws will do.
- [x] **The corpus's existing files do not change,** and the harness reports on them as before. Record the new document's figures in Comments.

**Cost**
- [x] **Time:** record the seconds per scanned page with and without the finder, on this machine and in the Linux image. Grilling measured about +1.3 s.
- [x] **Memory:** measure the peak of a conversion in the sandbox, with OCR and the finder in one process, on the 110-page sample.
  - Do this on this machine only.
  - If the peak passes 2 GiB, raise the sandbox's memory limit to 3 GiB. That reaches production through staging, as usual, and the user is asked before the deploy.

**Tests**
- [x] Real-model tests (`pytest -m ocr`):
  - ~~the new document gives `[ลายเซ็น]`, `[ตราประทับ]` and `[รูปภาพ]` where its reference has them;~~ a colour scan built in the test gives `[รูปภาพ]` and `[ตราประทับ]`; the signature moved to ticket 03 with the document;
  - the corpus's other scans get no placeholder their reference does not have.
- [x] A fast test that a missing layout model is reported as the OCR models are.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

## Comments

**2026-11-12, implemented on branch `feat/pictures-inside-scans`**

- **The model:**
  - **Pinned:** `ocr_models.LAYOUT`, PP-DocLayout_plus-L at Hugging Face commit `aa52b85`, its four files pinned by SHA-256. The large file's hash matches Hugging Face's own; the three small files were hashed here. `MODELS` holds it, so `pdf-to-doc-models` fetches it and skips the models already there.
  - **The finder:** `paddle.PaddleLayoutFinder` uses PaddleOCR's `LayoutDetection` on the CPU, with the engine's thread setting. It shares the engine's settings that keep Paddle offline and quiet (`_quiet_and_offline`). It hands the image over blue first, as Paddle takes an array, and keeps the regions labelled "image", "chart" or "seal".
  - **The threshold** is the model's own, `draw_threshold: 0.5` in its `inference.yml`. The corpus gave no reason to change it.
  - **Which finder:** the finder goes with the engine. `convert` uses the layout model beside PaddleOCR, and none beside an engine passed in `ocr`, such as the tests' fakes. The CLI, the sandbox and the harness pass no engine, so they all use the model.
  - **A missing model:** `default_picture_finder` checks the model's files before Paddle is imported, and raises `ModelsMissing`. The CLI's exit code 9, its advice to run `pdf-to-doc-models`, and the sandbox's `ModelsMissing` event then follow, as for the OCR models.
- **In the image:** the model adds 125 MB, beside 12.5 MB for the OCR models. The image is 2.86 GB.
- **A fault the corpus found, fixed:**
  - On page 5 of `damaged-english-scans`, the model took the whole scan for one "image". That is the page behind the text, which gets no placeholder, but ticket 01 still dropped the unsure text in it.
  - Junk is now dropped only from a picture a placeholder will stand for: a ring in colour, or one with fewer than three rows over it. Page layout and OCR share that rule (`layout.stands_in`).
  - A fast test covers it.
- **Corpus, with and without the model, on this machine:**
  - every page of `corpus/synthetic` and `corpus/degraded` comes out the same either way;
  - no scan got a placeholder.
- **The signing scan moved to ticket 03.** On a synthetic signing scan in colour:
  - **found:** the photo and the red stamp;
  - **a signature whose foot touches the signer's name:** no region at all;
  - **a signature a blank line above the name:** found, but its box hugs the ink, 29 points tall where the picture is 45, so it lay 16.4 points from the row, more than the row's 14.7. Ticket 24's rules then gave `[รูปภาพ]`;
  - **a gradient box drawn as a logo at the page's head:** no region at all.

  The page then scored a CER of 0.065, over the corpus's bound of 0.05 for OCR pages. The user chose to move the document to ticket 03, where coloured ink beside the row finds the signature, and to leave the synthetic logo out: real logos are measured on the samples in ticket 05.
- **Time:**
  - **this machine:**
    - the finder took 1.36 s per scan at the median, 2.52 s at most, over the corpus's 43 scans;
    - over the corpus's 56 OCR pages, each file converted whole, 2.31 s a page without the model and 4.16 s with it. Each file loads the model once, and most hold a page or two, so this counts the load nearly once a page;
  - **the Linux image, 4 CPUs and 4 threads, as on the server:** the 110-page sample, 91 scans, took 579 s with the model and 426 s without, so +1.7 s a scan. About 10 minutes in all, within the 30-minute limit.
- **Memory,** the sandbox's process on the 110-page sample in the Linux image, under Docker's own runtime, not gVisor, which Docker Desktop lacks:
  - with no limit, it peaked at 2.19 GiB with the model, and 2.07 GiB without it;
  - held to 2 GiB with no swap, it still ended, at 1.94 GiB.

  The first figure passes 2 GiB, and the third leaves about 60 MB spare before gVisor's own use. So the sandbox's limit is now 3 GiB (`web/docker.py`), and ADR 0004 records it.
  - **Before deploying:** three sandboxes may run at once, which could now take 9 GiB of gmt's memory, against 6 GiB before. Check gmt's free memory on staging.
- **Tests:**
  - **Fast:** a missing layout model raises `ModelsMissing`, and text read unsurely in a picture found behind the text stays.
  - **Real model** (`-m ocr`):
    - a colour scan with a photo and a stamp gives `[รูปภาพ]` and `[ตราประทับ]`, at a CER under 0.05;
    - a colour scan of text alone gives no placeholder;
    - no OCR page of `corpus/synthetic` or `corpus/degraded` gets a placeholder its reference does not have.

**2026-11-12, after code review (two axes)**

- **Spec found a real fault:** text could be lost under a picture that has text-layer rows over it.
  - **How:** OCR counted only the lines it read surely over a picture, while page layout also counts the text layer's rows. So a picture under three typed rows had its unsure text dropped, and then got no placeholder.
  - **Fix:** the rows over a picture now count the text-layer rows too.
  - **Shared rule:** the rule itself is one function, `layout.stands_in`, which both `_placeholder` and OCR call. This also answers Standards' point about the rule written twice.
  - **Test:** a new fast test covers it, and fails when the text-layer rows go uncounted.
- **Spec also found:**
  - **Time without the model on this machine** was missing. It is now in Comments above.
  - **The memory measurement** did not say it ran without gVisor. Comments and ADR 0004 now say so.
  - **Ticket 03:**
    - it now waits for 02 as well;
    - it records the moved document's figures.
  - **The missing-model test** checks the exception only. The CLI's exit code and the sandbox's event come from `ModelsMissing` itself, as the OCR models' tests already show.
- **Standards, fixed:**
  - `standing` is renamed `placeheld`;
  - the nested ternary in `convert` is now `_finder`;
  - the `ModelsMissing` message names the layout model;
  - `_box` has a docstring;
  - ADR 0004 and the test say GiB;
  - the Dockerfile's comments name the layout model and its size.
- **Standards, left:** "layout model" is not in GLOSSARY.md. It names a piece of software, not something in a reader's document.
