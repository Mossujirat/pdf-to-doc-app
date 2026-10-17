# 09: Placeholders

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Content the converter deliberately does not transcribe shows up as a short Thai placeholder, both in Markdown and in DOCX. The reader then knows something was there, and nothing is invented. This covers images, signatures and stamps. The document model gains a placeholder block with a kind.

**Blocked by:** 07

**Status:** ready-for-agent

**Branch:** `feat/docx`

**Placeholder kinds**
- [ ] Image objects on text pages become `[รูปภาพ]` placeholders at their position in reading order.
- [ ] Where an image can be identified as a signature or a stamp, it becomes `[ลายเซ็น]` or `[ตราประทับ]`. For example: a small image next to signature-line text, or a round coloured mark.
- [ ] When the kind is unclear, use the generic image placeholder rather than guessing.
- [ ] The placeholder kinds the spec defines for later tickets (handwriting, incomplete table) exist in the document model and both renderers.

**Rendering and summary**
- [ ] Placeholders appear in both Markdown and DOCX outputs.
- [ ] The summary counts placeholders by kind.

**Tests**
- [ ] Synthetic fixtures with an embedded image and a signature-line image cover placeholder output in both formats.
