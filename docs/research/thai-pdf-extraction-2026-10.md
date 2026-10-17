# Thai PDF extraction: research and benchmarks (October 2026)

This is the evidence behind the decisions in `GLOSSARY.md` and `docs/adr/`. It combines desk research with two benchmarks run locally on 2026-10-17.

## Setup

**Hardware and software:** Windows 11, AMD Ryzen AI 7 350 (8 cores / 16 threads), 32 GB RAM, CPU only, Python 3.13.

**Sample files:** both are real signed contracts, kept out of the repo (one is marked confidential). Nothing was sent to an external service.

- **Thai grant contract, 110 pages, exported from Word.** Fonts are TH Sarabun PSK. It is a mixed PDF:
  - About 22–25 pages have a real text layer.
  - About 85 pages are scans whose only text layer is a stamped header line ("เอกสารปกปิด…", "หน้าที่ x/y").
  - On pages 69–72 the text layer itself is wrong: the font's ToUnicode map turns sara aa into sara am, so "การ" comes out as "กำร".
- **English agreement, 5 pages, made with "Microsoft: Print To PDF".**
  - Pages 1–4 are image-only.
  - Pages 1–3 also carry 2.4k–3.6k vector paths each. That makes pdfminer-based tools very slow: 16–31 s for 5 pages, against 0.18 s for PyMuPDF.

## Findings that shape the design

1. **No extractor gives clean Thai out of the box.** Every tool mapped glyphs to Unicode correctly (no PUA, no U+FFFD). Thai broke in each tool's layout logic. We therefore need our own Thai repair step after extraction.
2. **PyMuPDF `get_text()` is the best base:** Thai-correct and the fastest. It also honours /ActualText, which pdf.js and pdfminer drop. Its licence is AGPL (ADR 0002).
3. **pdf.js, which is what in-browser extraction would use, inserts spaces inside Thai words and has no table detection** (ADR 0001).
4. **Decide text page or OCR page per page, and not by character count.** A stamped header can hide a scanned body. Our probe used "fewer than 300 text characters and images covering more than half the page".
5. **A broken text layer can be detected.** The share of Thai tokens that are dictionary words (PyThaiNLP `word_tokenize` + `thai_words()`) was 74–89% on the broken pages 69–72. OCR of the same pages scored at least 97%.
6. **Header page counters ("หน้าที่ x/y") restart in each appendix.** They cannot be used as real page numbers.

## Text-layer extractors

All 110 pages of the Thai contract were extracted. "Orphan marks" are Thai combining marks at the start of the text, after whitespace, or after a non-Thai character. "Extra spaces" are spaces between Thai letters where the PyMuPDF baseline has none; each one is classified by PyThaiNLP as inside a word or between words.

| Tool | Orphan marks | Extra spaces (inside word / between words) | Thai similarity to PyMuPDF | Line handling | Tables | Seconds per page |
|---|---|---|---|---|---|---|
| PyMuPDF `get_text` (baseline) | 0 | — | 1.000 | Hard break at every line | None | 0.002 |
| pymupdf4llm, layout mode | 54 | 3 / 49 | 0.961 | Joins lines into paragraphs, but adds a space at 121 of 162 Thai line joins | 9 Markdown tables: ruled tables merged, words cut across cells | 0.25 |
| pymupdf4llm, legacy mode | 18 | 0 / 8 | 0.950 | Hard breaks | 14 tables, vowels lost inside cells | 0.14 |
| pdfplumber | 122 | 120 / 38 | 0.963 | Hard breaks | Cells contain only numbers, no Thai | 0.058 |
| pypdf | 0 | 19 / 21 | 0.9995 | Hard breaks; 36 joins with a space | None | 0.030 |
| MarkItDown | 122 | 108 / 45 | 0.963 | Hard breaks | 99 tables, 78 of them fake (built from header lines) | 0.062 |
| pdf.js (`str` + `hasEOL`) | 0 | 68 / 27 | 0.9995 | 36 joins with a space | None | 0.008 |
| pdf2docx, read back with python-docx | 0 | 1 / 8 | 0.962 | Joins paragraphs correctly (155 of 168) | 30 DOCX tables, merged cells kept | 0.52 |

### How Thai breaks during extraction

| Cause | Tools | Example |
|---|---|---|
| Glyphs sorted by x position, so marks detach from their base consonant | pdfplumber, MarkItDown | "ให้ทุน" → "หท้ ุน" |
| Spaces inserted at gaps in justified text | pdf.js, pypdf | "หรื อ" |
| Text clipped to table-cell boxes, so above and below marks are lost | PyMuPDF `find_tables` extraction | "งวดท 1" |
| A space added when Thai lines are joined | pymupdf4llm layout mode | — |

**A table workaround that looks promising:** use `find_tables` only for the cell grid, then assign each word to the cell that contains the word's centre. This produced 0 orphan marks, and "งวดที่" was found 24 times against 8 with `to_markdown`. It is a quick prototype; full cell coverage has not been checked.

### Thai repair rules from research and testing

- **Never apply NFKC.** It decomposes sara am (U+0E33) into nikhahit + sara aa.
- **Recompose sara am and reorder marks** with PyThaiNLP `normalize` / `reorder_vowels`. This also fixes reordered marks from Word exports, such as "กฬีา".
- **Joining lines:**
  - Thai + Thai: join without a space.
  - Thai + Latin: join with one space.
  - Thai spaces separate phrases, not words. Use word segmentation only to check, never to insert spaces.
- **Remove a space that sits before a combining mark.** The sample also had zero-width spaces before ำ.
- **Map legacy Private Use Area glyphs back to Thai.** Windows fonts use U+F700–F71A and Mac fonts U+F88x; HarfBuzz's Thai shaper tables give the mapping. None appeared in our samples, but they are a known failure mode.
- **Treat a page whose text layer fails validation as an OCR page.**

**DOCX font slot:** Thai text needs its font set in the complex-script slot (`w:rFonts/@w:cs`, plus `w:szCs` for size). pdf2docx writes neither, and python-docx's `font.name` does not set them.

## OCR engines (CPU only)

**Pages tested:**
- Rendered at 300 dpi with PyMuPDF. The scans are embedded at about 220 dpi.
- Reference pages: 2, 5 and 9, which have correct text layers. The CER below is measured against them. These are clean renders, so treat the CER as optimistic.
- Real scans: 12, 13 and 82, plus the broken pages 69–72. These have no reference text, so only the dictionary-word share was measured.

| Engine | Seconds per page | CER, overall / Thai only | Dictionary-word share, real scans / broken pages | Orphan marks | Table structure | Model size | Peak RAM |
|---|---|---|---|---|---|---|---|
| PaddleOCR, tuned (settings below) | 4.6 | 5.4% / 4.0% | 98.1% / 97.2% | 0 | Plain lines | 13 MB | 1.4 GB |
| PaddleOCR, Thai defaults (server detector, full resolution) | 20.2 | 17.8% / 11.8% | 93.5% / 90.1% | 4 | Plain lines | 96 MB | 6.1 GB |
| Tesseract 5.5 `tha+eng` | 4.4 | 7.7% / 5.7% (3.2% after recomposing ำ) | 94.4% / 89.4% | 3 | Plain lines | 1.1 MB | ~150 MB |
| Typhoon OCR 1.5 2B, GGUF Q8_0 | 234 | 3.3% / 1.9% | 100% / 97.4% | 0 | HTML tables, checkboxes | 2.65 GB | 5.1 GB |
| Typhoon OCR 1.5 2B, transformers bf16 | over 600 (stopped) | 1.3% / 0.7% on the part produced | not run | — | — | 4.26 GB | 5.2 GB |

**Observations:**
- **Sara am:** every OCR engine fixed it on pages 69–72 ("กำร" appears 0 times).
- **English:** all engines read it well; they agree 99% with each other on SSFA page 1.
- **Typical PaddleOCR errors:**
  - Skipped lines.
  - Dropped or confused marks: เพิ่ม→เพิม, ขึ้น→ซึ้น, ฏ→ฎ.
- **Typical Tesseract errors:** dropped tone marks (ทั่ว→ทัว, ชื่อ→ชือ), and bullets read as "¢".
- **Typhoon:**
  - Every page costs about 2 minutes of image processing before text starts.
  - A 100% dictionary share cannot rule out fluent hallucinations, i.e. a wrong word that is still a valid word.

**CPU time for about 85 scanned pages:**

| Engine | Time |
|---|---|
| PaddleOCR, tuned | about 4 minutes |
| Tesseract | about 5 minutes |
| Typhoon GGUF | about 4 hours |

### Settings that matter

**PaddleOCR 3.7.0**
- **Version pin:** use `paddlepaddle==3.2.2`. Version 3.3.1 failed at inference with a oneDNN/PIR `NotImplementedError`.
- **Models:**
  - Detector: `PP-OCRv5_mobile_det`.
  - Recogniser: `th_PP-OCRv5_mobile_rec` for Thai, `en_PP-OCRv5_mobile_rec` for English.
- **Detector input:** `text_det_limit_type="max"` and `text_det_limit_side_len=1280`.
  - At full resolution the detector splits Thai marks into tiny boxes, and merges or skips whole lines.
  - This value was chosen from 7 settings on the same 3 reference pages, so it may be slightly over-fitted.
- **Off:** `use_doc_orientation_classify`, `use_doc_unwarping`, `use_textline_orientation`.

**Typhoon OCR 1.5 2B**
- **Build:** GGUF Q8_0 + mmproj f16 (mradermacher), run with `llama-cpp-python` 0.3.36 (CPU wheel).
- **Context and speed:** `n_ctx=16384`, `flash_attn=True`. Flash attention cut page 9 from 374 s and 10.1 GB to 248 s and 5.1 GB.
- **Sampling:** temperature 0.1, top_p 0.6, repeat_penalty 1.1.
- **Input image:** longest side resized to 1800 px.
- **Prompt:** the one from the model card.
- **Caveat:** the model card warns that GGUF builds may lose accuracy.

## Licences (for a public web service)

- **AGPL-3.0 or a commercial licence:** PyMuPDF, pymupdf4llm, pymupdf-layout, MuPDF.js. Also pdf2docx in practice, because it is built on PyMuPDF.
- **Model-weight restrictions:**
  - Surya/Marker: free only below $5M revenue or funding.
  - Chandra: free only below $2M, and not for uses that compete with Datalab's API.
- **Attribution required:** MinerU (online services must show a "uses MinerU" notice).
- **GPL:** pandoc. Obligations apply when distributing it.
- **Permissive:**
  - Extractors and libraries: pdf.js, pdfminer.six, pdfplumber, pypdf, Docling, MarkItDown, PyThaiNLP.
  - OCR: Tesseract, PaddleOCR / PaddleOCR-VL, Typhoon OCR 1.5 weights (Apache-2.0).

## Desk research highlights

**Docling:** open bug (Oct 2026) in which the default parser strips Thai tone marks and vowels [1].

**Published Thai OCR benchmarks.** All are small; treat them with caution.
- ThaiOCRBench (IJCNLP-AACL 2025), fine-grained text recognition score: Gemini 2.5 Pro 0.499, GPT-4o 0.254, Claude Sonnet 4 0.214. Tesseract and EasyOCR were the weakest baselines [2].
- Typhoon OCR 1.5 vendor test set, average edit distance: 0.251 for Typhoon against Gemini 2.5 Pro 0.289 [3].

**Cloud OCR with Thai:**
- **Thai supported:** Azure Document Intelligence v4.0 (printed and handwritten) and Google Document AI.
- **No Thai:** AWS Textract [4][5][6].

**Libraries and features we rely on:**
- PyThaiNLP `normalize` / `reorder_vowels` handles sara am and mark ordering [7].
- The HarfBuzz Thai shaper has the PUA reverse mapping [8].
- The browser's `Intl.Segmenter('th')` segments Thai words, if ever needed client-side [9].

**Sources**

[1] https://github.com/docling-project/docling/issues/3170
[2] https://arxiv.org/html/2511.04479
[3] https://huggingface.co/scb10x/typhoon-ocr1.5-2b
[4] https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/language-support/ocr
[5] https://docs.cloud.google.com/document-ai/docs/languages
[6] https://docs.aws.amazon.com/textract/latest/dg/limits-document.html
[7] https://pythainlp.org/docs/5.1/api/util.html
[8] https://flutter.googlesource.com/third_party/harfbuzz/+/HEAD/src/hb-ot-shaper-thai.cc
[9] https://web.dev/blog/intl-segmenter

Further sources:
- pdf.js ignores /ActualText: https://github.com/mozilla/pdf.js/issues/12237
- pdfminer.six ignores /ActualText: https://github.com/pdfminer/pdfminer.six/issues/1288
- PyMuPDF text flags: https://pymupdf.readthedocs.io/en/latest/vars.html
- pdf2docx maintenance status: https://github.com/ArtifexSoftware/pdf2docx
- MinerU licence: https://raw.githubusercontent.com/opendatalab/MinerU/master/LICENSE.md

## Not measured yet

- **CER on real scans.** This needs reference text, which is being prepared locally.
- **Typhoon on a GPU, and Typhoon's English output.**
- **PaddleOCR's table model (PP-StructureV3).**
- **Behaviour in a Linux container.** Every number above comes from Windows.
- **Legacy PUA-font PDFs.** None of the samples had them.
