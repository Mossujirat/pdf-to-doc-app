# 15: Accurate mode (Typhoon)

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** For an important document, a user can choose Accurate mode and get much better OCR, in exchange for a far slower conversion: about 4 minutes per OCR page on CPU. OCR pages are then read by Typhoon OCR 1.5 2B through the OCR engine interface. Its HTML tables become real tables, and its image descriptions are replaced by placeholders, so no invented text reaches the output.

**Blocked by:** 04, 08, 09

**Status:** ready-for-agent

**Branch:** `feat/ocr`

**Choosing Accurate mode**
- [ ] The conversion function accepts Accurate mode, and the CLI exposes it as a flag.
- [ ] The summary names the engine used.

**Typhoon adapter**
- [ ] Use the GGUF Q8 build with its vision projector, through llama-cpp-python, with flash attention on.
- [ ] Use the prompt from the model card.
- [ ] Generation settings: temperature 0.1, top_p 0.6, repeat_penalty 1.1.
- [ ] Resize the input image so its longest side is 1800 px.
- [ ] Models are downloaded by an explicit setup step, never on first use.

**Turning Typhoon output into the document model**
- [ ] HTML tables become table blocks with spans.
- [ ] `<figure>` image descriptions are dropped and become placeholders.
- [ ] Page-number tags are dropped.
- [ ] Checkbox characters are kept.
- [ ] Typhoon gives no per-word confidence. Choose a rule for uncertain text in this mode (for example, words that fail a dictionary check) and record it.

**Progress and reporting**
- [ ] Progress reports each OCR page, because pages take minutes.
- [ ] Measure Typhoon's English output quality on simulated English scans, and record the result.

**Tests**
- [ ] These tests are excluded from CI and run on demand.
- [ ] Fast tests feed recorded Typhoon outputs through the fake engine to cover the table, figure and page-number handling.

## Comments

**2026-10-25, from grilling ticket 14 (scanned tables)**

- **Default mode will not rebuild unruled tables.** It gives them one line per row, and gives ruled tables their grid from the page image. PaddleOCR's table models were measured and rejected: too much memory for the sandbox, and unreliable on unruled tables. The user chose Accurate mode as the way to get unruled tables' structure, so Typhoon's HTML tables carry more weight here.
- **Uncertain text in table cells** is added by ticket 14: cells are marked, and the summary counts them, through the same accessor as paragraphs. Typhoon's tables can use it for this mode's rule on uncertain text.
- **Ticket 14 finds ruled grids where OCR pages are read, through the `OcrEngine` interface.** It needs the engine's text boxes. Typhoon gives none, so in this mode the tables come from Typhoon's HTML alone.
