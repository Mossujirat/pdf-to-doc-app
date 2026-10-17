# Every output comes from one document model

pdf2docx produced the best DOCX in our benchmark: Thai text intact and merged table cells kept. A quick design would use it for DOCX and a separate path for Markdown. We rejected that design:

- It cannot handle OCR pages, so those would need a second path anyway.
- The two outputs could disagree about the text.
- Artifex no longer maintains pdf2docx.
- It writes no complex-script font settings, so Thai renders in the wrong font.

Instead, each source file is extracted and its Thai text repaired once, into a single document model. Both DOCX and Markdown are rendered from that model, so fixes to broken text apply to every output.
