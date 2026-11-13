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

**2026-11-12, a candidate to measure against Typhoon**

The user found `iapp/OpenThai2.0-OCR-Markdown` on Hugging Face, released on 2026-11-09. Its card was read on 2026-11-12; the model was not downloaded or run.
- **What it is:** iApp Technology's Thai fine-tune of NVIDIA Nemotron 3.5 Parse, 0.63B parameters, 2.5 GB of float32 weights. A page image goes in, and Markdown comes out, with tables as HTML and a box and a class for every block, pictures included.
- **Its own figures:** a little ahead of Typhoon OCR V2 2B on Thai text and tables (an average of 88.3 against 85.8), and 1.6 s per page against 15.8 on an H100. The test sets are mostly government documents and the Royal Gazette. Nobody has measured it on contracts.
- **Why it could serve this ticket:** it is about a third of Typhoon's size, and its picture blocks would give this mode signatures and pictures without ticket 38's finder.
- **Before choosing it:**
  - **Speed:** it is built for an NVIDIA GPU through vLLM. Neither this machine nor the web server has one, so its speed on CPU has to be measured.
  - **Uncertain text:** like Typhoon, it gives no confidence for each character, so this mode still needs its own rule for uncertain text.
  - **The licence:** OpenMDW-1.1. Read the full terms before shipping it beside the AGPL code (ADR 0002).
  - **Its hosted API is out:** iApp's API sends the file to their server, against ADR 0001.
