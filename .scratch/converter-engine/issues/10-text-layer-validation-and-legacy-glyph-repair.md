# 10: Text-layer validation + legacy glyph repair

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Pages whose text layer is itself wrong no longer leak broken text into the output. An example is a font whose ToUnicode map turns "การ" into "กำร". The converter first repairs what it can: legacy fonts that put shifted vowels and tone marks in the Private Use Area are mapped back to Thai. A page whose text layer still fails validation is routed to OCR, and the summary says why.

**Blocked by:** 08

**Status:** ready-for-agent

**Branch:** `feat/ocr`

**Legacy glyph repair**
- [ ] Map Private Use Area glyphs from legacy Thai fonts back to standard Thai: the Windows range U+F700–F71A and the Mac U+F88x range. Use HarfBuzz's Thai shaper tables as the reference mapping.

**Validation**
- [ ] A text layer fails validation when any of these hold:
  - a low share of Thai tokens are dictionary words (PyThaiNLP word segmentation and its Thai word list)
  - it contains Private Use Area characters that cannot be mapped
  - it contains replacement characters
  - it shows sara-am anomalies
- [ ] Set the dictionary threshold from the corpus. In the benchmark, broken pages scored 74–89% and good OCR scored 97% or more.

**Routing and summary**
- [ ] A page that fails validation becomes an OCR page.
- [ ] The summary marks such pages, for example: "text layer untrustworthy, read by OCR".

**Tests**
- [ ] Synthetic fixtures cover a legacy PUA-font PDF (repaired without OCR) and a PDF with a wrong ToUnicode map (routed to OCR). The fake engine verifies the routing.
- [ ] The harness shows zero "กำร"-style errors.
