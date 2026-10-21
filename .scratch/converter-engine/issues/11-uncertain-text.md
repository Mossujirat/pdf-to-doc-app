# 11: Uncertain text

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Users can see exactly which words to double-check. OCR text that falls below a confidence threshold is marked as uncertain text: wrapped in a `<mark>` element in Markdown and highlighted yellow in DOCX. The summary counts uncertain spots per page and explains what the marking means. Handwriting that cannot be identified as handwriting is caught here, as low-confidence text, instead of being output silently.

**Blocked by:** 07, 08

**Status:** done

**Branch:** `feat/ocr`

**Marking**
- [x] Text runs in the document model carry an uncertain flag, set from OCR confidence. They are paragraphs' and list items' uncertain stretches, set from unknown words and from low confidence (see the comments).
- [x] Neighbouring uncertain words merge into one marked span.

**Threshold**
- [x] Choose the confidence threshold with the harness. Aim to mark most wrong characters while marking as few correct ones as practical.
- [x] The harness reports the share of wrong characters that end up unmarked, which feeds the quality gate in ticket 17.

**Rendering and summary**
- [x] Markdown wraps uncertain text in `<mark>…</mark>`.
- [x] DOCX highlights uncertain text yellow.
- [x] The summary in both formats states the count, and that marked text needs checking.

**Tests**
- [x] Fast tests use the fake engine with fixed confidences to cover marking, merging and both renderers.

## Comments

**2026-10-21, how uncertain text is found (decided with the user)**

**Confidence alone is not enough.** PaddleOCR gives one score per detected box, which is usually a whole printed line, and one wrong mark barely moves it. The test used 20 synthetic Thai and English lines, scanned at six levels of damage (300 dpi clean down to 75 dpi with heavy grain and skew), giving 123 boxes:

| Box | Score |
|---|---|
| one or two wrong characters | 0.93–0.96 |
| no errors | 0.945–0.96 |
| read as nonsense ("9" for a whole line) | 0.64 and 0.75 |

Marking whole boxes below 0.95 marked 11% of the text and caught almost none of the small misreads. Catching most of them would have meant marking about a third of the text.

**Unknown words do much better.** These are Thai words that PyThaiNLP's word list does not hold, the same check that text-layer validation uses. On the same boxes, they:
- marked 1.2% of the text
- marked no box that was read correctly
- flagged 25 of the 41 boxes with errors, pointing at the misread word: "อืน", "เพิม", "กรัณี", "ใข้", "เคือน"

**Decision.** Both signals are used:
- unknown words in OCR text
- whole boxes below 0.85, which sits between the nonsense boxes and the lowest good ones

Text from a text layer is never marked.

**On the synthetic corpus with real PaddleOCR:**
- 1 uncertain stretch, the nonsense box "9e" on the wrong-ToUnicode page
- no correct text marked
- 60% of the OCR pages' edits left unmarked

What stays unmarked is mostly a dropped tone mark that leaves another real word: "ที" for "ที่".

**Known gaps,** for ticket 17 to measure on real scans:
- a misread that is itself a word ("ที" for "ที่", "ทาก" for "หาก")
- lost digits
- punctuation and spacing

PaddleOCR keeps per-character scores inside its decoder. Reaching them would mean patching Paddle's internals, and Typhoon has no scores at all. The unknown-word check works for both engines.

**2026-10-21, after code review**

The review found three faults, all now fixed:
1. **Text from the text layer was marked when it shared a block with OCR text.** An example is a name stamped as text just below the scanned body.
2. **When a low-confidence box could not be found in the block's text, the whole block was marked.** An example is a list item, whose bullet is taken off. A repeated box such as "9" was also marked at its first occurrence, not where it was read.
3. **The Markdown summary held a real `<mark>` element.**

**The fixes:**
- Each row now records the pieces it was read from: OCR boxes with their confidence, and text-layer text. The pieces are found in the block's text in reading order.
- Only OCR pieces can be uncertain.
- A piece that cannot be found takes only the gap between its neighbours.
- The summary writes the tag as code.

**Measuring with the harness.** The damaged scans used to choose the threshold are now `corpus/degraded/`, made by the generator and kept outside the gate, so that the harness can measure the marking. `uv run pdf-to-doc-eval corpus/degraded` with real PaddleOCR gave:

| Measure | Result |
|---|---|
| CER | 1.2% |
| Uncertain stretches | 14, every one on a real error ("นี", "อืน", "ผู", "เพิม", "ชือ", "็ใข", "ด6" for "๑๒") |
| Correct text marked | none |
| Errors left unmarked | 62% |

What stays unmarked is misreads that are words ("ทันที่", "เล็ก" for "เลิก"), and spaces.
