# 12: Conversion leaves nothing behind

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user can rely on two guarantees. A conversion never touches the network. Nothing from their file outlives it except the output they asked for. These are the runtime half of ADR 0001's privacy promise, verified by tests.

**Blocked by:** 08

**Status:** ready-for-agent

**Branch:** `feat/ocr`

**No network**
- [ ] Conversion runs with all network access blocked and still succeeds, in default mode with real PaddleOCR. No model or resource is fetched on first use.

**No leftovers**
- [ ] Temporary files, such as rendered page images, go into a private temporary directory. It is removed when a conversion ends, whether it succeeds, fails partway, or raises an intake error.

**No content in logs**
- [ ] Logs and error messages never contain document text or page images. They may contain page numbers, counts and timings.

**Tests**
- [ ] One test blocks sockets and converts a mixed fixture.
- [ ] One test checks that the temp area is empty after success and after a forced failure.
- [ ] One test captures log output from a full conversion and confirms that no reference-text fragment appears in it.

## Comments

**2026-10-19, handed over from ticket 08 (OCR pages)**

- PaddleX writes working files (`func_ret`, `locks`, `temp`) under `PADDLE_PDX_CACHE_HOME`: `~/.paddlex` by default, `/tmp/paddlex` in the image. The leftovers check should include that folder.
- Pages are rendered in memory, and no image file is written. The engine is kept between conversions in one process, so nothing of a document should stay in it; check that too.
- The models download separately (`pdf-to-doc-models`, or at image build). The no-network test should run with them in place.
