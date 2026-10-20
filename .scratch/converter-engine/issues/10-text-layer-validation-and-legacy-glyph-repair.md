# 10: Text-layer validation + legacy glyph repair

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Pages whose text layer is itself wrong no longer leak broken text into the output. An example is a font whose ToUnicode map turns "การ" into "กำร". The converter first repairs what it can: legacy fonts that put shifted vowels and tone marks in the Private Use Area are mapped back to Thai. A page whose text layer still fails validation is routed to OCR, and the summary says why.

**Blocked by:** 08

**Status:** done

**Branch:** `feat/ocr`

**Legacy glyph repair**
- [x] Map Private Use Area glyphs from legacy Thai fonts back to standard Thai: the Windows range U+F700–F71A and the Mac U+F88x range. Use HarfBuzz's Thai shaper tables as the reference mapping.

**Validation**
- [x] A text layer fails validation when any of these hold:
  - a low share of Thai tokens are dictionary words (PyThaiNLP word segmentation and its Thai word list)
  - it contains Private Use Area characters that cannot be mapped
  - it contains replacement characters
  - it shows sara-am anomalies
- [x] Set the dictionary threshold from the corpus. In the benchmark, broken pages scored 74–89% and good OCR scored 97% or more.

**Routing and summary**
- [x] A page that fails validation becomes an OCR page.
- [x] The summary marks such pages, for example: "text layer untrustworthy, read by OCR".

**Tests**
- [x] Synthetic fixtures cover a legacy PUA-font PDF (repaired without OCR) and a PDF with a wrong ToUnicode map (routed to OCR). The fake engine verifies the routing.
- [x] The harness shows zero "กำร"-style errors.

## Comments

**2026-10-17, finding from ticket 01 (corrected in review):**
- A glyph with no Unicode mapping comes out as U+0000 under PyMuPDF's default text flags, because they include `TEXT_CID_FOR_UNKNOWN_UNICODE`.
- The text-layer extractor now clears that flag, so such glyphs come out as U+FFFD instead.
- Validation should count U+FFFD. It should also guard against U+0000, in case the flags change again.

**2026-10-20, implementation notes**

- **Legacy glyphs.**
  - `repair()` maps both Private Use Area ranges back to Thai before any other step: the Windows range U+F700–F71A and the Mac range U+F884–F89E, 27 code points each.
  - The table is HarfBuzz's Thai shaper table (`src/hb-ot-shaper-thai.cc`, last changed 2026-02-20), copied as numbers and reversed. It covers marks shifted down, down and left, or left, and yo ying and tho than without their lower part.
  - Because the mapping is part of `repair()`, it applies to OCR text too.
- **Validation** (`validation.py`) runs on the repaired text of every page that is not already an OCR page. The text layer fails when:
  - it holds U+FFFD, NUL, or a Private Use Area character the table does not map;
  - sara am follows anything but a consonant or a tone mark, or another mark follows it;
  - it has at least 20 Thai words, and fewer than 95% of them are in PyThaiNLP's word list (newmm segmentation).
- **How the thresholds were set, from the real contract (local, numbers only):**
  - The 19 good text pages scored 0.982–1.000. The four pages with the broken ToUnicode map, 69–72, scored 0.781–0.910. The threshold, 0.95, falls in the gap.
  - The smallest real text page has 101 Thai words. Every synthetic page scores 1.000.
  - Under 20 words, a page is not judged by the dictionary. Names can fall outside the word list ("ภรณ์", "พัฒน์"), though PyThaiNLP splits most names into words it knows.
  - The sara am checks never fire on the good pages. They do not catch the contract's map either, since "กำร" has sara am after a consonant; the dictionary catches that. They are there for other broken fonts.
  - A pattern of a leading vowel, consonants and sara am was tried and dropped: it matches across word boundaries in correct text, such as "ไปทำ".
- **Routing.**
  - A page that fails becomes an OCR page. Its text layer passes nothing on, not even stamps, because none of it can be trusted.
  - `Page` and `PageSummary` carry `untrusted_text_layer`. The headline adds, for example, "(หน้า 69–72 ข้อความในไฟล์ไม่น่าเชื่อถือ จึงอ่านด้วย OCR)".
- **A U+FFFD now sends a whole page to OCR,** as the ticket asks. The ticket 01 test for a glyph without a Unicode mapping now checks that routing, with the fake engine.
- **Fixtures.**
  - `pdf_builder.remapped` rewrites each font's ToUnicode map, reading both `bfchar` and `bfrange` entries. The page still looks right; only its text layer changes.
  - One builder makes both the legacy-font fixture (marks reported as U+F701, U+F713 and so on) and the wrong-map fixture (sara aa reported as sara am, which turns "การ" into "กำร" exactly as on the contract).
  - Two corpus documents use it. `legacy-font` comes out as a text page with CER 0. `wrong-unicode-map` is routed to OCR; with real PaddleOCR its CER is 1.6% (0.4% on Thai only), with no broken text and no "กำร".
- **Real contract, local.**
  - Pages 69–72 are read with OCR. Their text layer held "กำร" 18 times; the output now holds it 0 times.
  - 91 OCR pages, converted in 435 s on Windows.
  - As the user chose, the budget tables on those pages come out as lines of text until ticket 14. Ticket 14 has a note on reusing the PDF's own grid.
- **Found and fixed while building the corpus fixture:** paragraphs on OCR pages were cut in two wherever a line's boxes were a fifth taller than usual, which happens on 19% of real scanned lines. Ticket 08's comments have the details. Every OCR line now gets the page's one font size.
- **Left open:**
  - A short page (under 20 Thai words) with a broken map is not caught by the dictionary.
  - A single unmapped symbol, such as a bullet from a symbol font, sends its whole page to OCR.

**2026-10-20, changes after code review**

- **"ๆ" and "ฯ" no longer count as misspelt words.** PyThaiNLP gives them tokens of their own ("เร็ว" + "ๆ"), and no word list has them. A correct page with "เร็วๆ", "ชัดๆ" and "กรมฯ" scored 0.871 and went to OCR. Tokens made only of these marks are left out, and a word with one at its end counts as known when the rest of it is.
- **A scan's text layer is checked too.** Text laid over a scan is kept on the OCR page, and a broken stamp leaked straight into the output (U+FFFD, a Private Use Area character, or "กำร"). Now:
  - Every page's text layer is validated, scans included. If it fails, it passes nothing on and the page is marked untrusted.
  - A text-layer row too short to judge is still checked against the engine's reading of the same place. If the engine's reading holds fewer words outside the word list, it replaces the row. This catches a stamp whose font reports "การ" as "กำร". A stamp the engine misreads keeps its exact text-layer reading, as in ticket 08.
- **Symbol-font bullets.** Word draws bullets with the Symbol and Wingdings fonts, which report them as Private Use Area characters in U+F000–F0FF; U+F0B7 is the usual one. At the user's choice, that range is not counted as damage, and a row that starts with one of them is a bulleted list item, like "•".
- **Tidying.**
  - `trustworthy` is renamed `trusted`, to match `untrusted_text_layer`.
  - The sara am rule reuses `THAI_CONSONANT`.
  - The tests import `CLAUSES` from the generator.
  - The test of a glyph the font cannot name moved to the validation tests.
  - The array form of `bfrange`, which PyMuPDF never writes, was dropped from the builder.
  - `docs/agents/triage-labels.md` now says what `done` means.
  - Ticket 08's font-size change went into its own commit.
- **Real contract, rerun after these changes:** the same result. Only pages 69–72 are untrusted; the scans' stamps pass the checks and keep their exact text. The output is unchanged at 206,503 characters, with no "กำร", converted in 408 s.
- **Not changed:**
  - `untrusted_text_layer` stays a flag beside the page kind, rather than becoming a reason value. The summary is its only reader.
  - "สระ ำ" (sara am written on its own after a space) loses the space in `repair`, by ticket 01's rule, so it trips the sara am check. Text that names the vowel on its own is rare.
  - A page dense with names outside the word list ("ภรณ์", "พัฒน์") can still fall below 0.95 and be read with OCR.

