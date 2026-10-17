# 11: Uncertain text

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Users can see exactly which words to double-check. OCR text that falls below a confidence threshold is marked as uncertain text: wrapped in a `<mark>` element in Markdown and highlighted yellow in DOCX. The summary counts uncertain spots per page and explains what the marking means. Handwriting that cannot be identified as handwriting is caught here, as low-confidence text, instead of being output silently.

**Blocked by:** 07, 08

**Status:** ready-for-agent

**Branch:** `feat/ocr`

**Marking**
- [ ] Text runs in the document model carry an uncertain flag, set from OCR confidence.
- [ ] Neighbouring uncertain words merge into one marked span.

**Threshold**
- [ ] Choose the confidence threshold with the harness. Aim to mark most wrong characters while marking as few correct ones as practical.
- [ ] The harness reports the share of wrong characters that end up unmarked, which feeds the quality gate in ticket 17.

**Rendering and summary**
- [ ] Markdown wraps uncertain text in `<mark>…</mark>`.
- [ ] DOCX highlights uncertain text yellow.
- [ ] The summary in both formats states the count, and that marked text needs checking.

**Tests**
- [ ] Fast tests use the fake engine with fixed confidences to cover marking, merging and both renderers.
