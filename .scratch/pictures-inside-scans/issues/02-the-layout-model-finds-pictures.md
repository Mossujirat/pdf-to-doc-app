# 02: The layout model finds the pictures

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decisions 2 and 6 of its comment of 2026-11-12.

**What to build:** Real conversions find pictures in scans with PaddleX's PP-DocLayout_plus-L, so the placeholders of ticket 01 appear on real scanned documents, on the CLI and on the web.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/pictures-inside-scans`

**The model**
- [ ] **Pinned as the OCR models are:** its name, its Hugging Face commit, and the SHA-256 of each file. It is Apache-2.0, published by PaddlePaddle.
- [ ] **`pdf-to-doc-models` fetches it** with the OCR models.
  - A conversion never downloads anything.
  - A missing model fails the same way a missing OCR model does.
- [ ] **Loaded fresh for each conversion,** as the OCR engine is, so it keeps nothing of the conversion before. Paddle's online model check and its own log lines stay off.
- [ ] **Its classes:**
  - "image", "chart" and "seal" regions are pictures;
  - every other class is ignored;
  - the score threshold is the model's own, unless the corpus shows a reason to change it. Record it in Comments.
- [ ] **The Docker image and CI fetch it too.** Record how much it adds to the image.

**Corpus**
- [ ] **A new synthetic document:** a signing page, scanned, with reference text. It holds:
  - a photo;
  - a signature in blue ink beside a row to sign on;
  - a red stamp;
  - a logo at the top.

  The pictures the generator already draws will do.
- [ ] **The corpus's existing files do not change,** and the harness reports on them as before. Record the new document's figures in Comments.

**Cost**
- [ ] **Time:** record the seconds per scanned page with and without the finder, on this machine and in the Linux image. Grilling measured about +1.3 s.
- [ ] **Memory:** measure the peak of a conversion in the sandbox, with OCR and the finder in one process, on the 110-page sample.
  - Do this on this machine only.
  - If the peak passes 2 GiB, raise the sandbox's memory limit to 3 GiB. That reaches production through staging, as usual, and the user is asked before the deploy.

**Tests**
- [ ] Real-model tests (`pytest -m ocr`):
  - the new document gives `[ลายเซ็น]`, `[ตราประทับ]` and `[รูปภาพ]` where its reference has them;
  - the corpus's other scans get no placeholder their reference does not have.
- [ ] A fast test that a missing layout model is reported as the OCR models are.
- [ ] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.
