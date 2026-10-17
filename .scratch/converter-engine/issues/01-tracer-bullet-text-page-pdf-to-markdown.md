# 01: Tracer bullet: text-page PDF → Markdown

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user runs the CLI on a PDF whose pages all have a correct text layer and gets Markdown in which the Thai text reads exactly as on the page. This first slice runs end to end:

- the conversion function, which is the main seam, and the CLI as a thin wrapper over it
- text-layer extraction with PyMuPDF into a minimal document model (paragraphs and page boundaries)
- the core Thai repair rules
- the Markdown renderer

It also sets up the project skeleton every later ticket builds on.

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/text-pages`

**Project skeleton**
- [x] A Python 3.13 package with pinned dependencies, an AGPL-3.0 licence file, a `.gitattributes` forcing LF line endings, and a test runner that runs with one command.

**Conversion function and CLI**
- [x] The conversion function takes a source file and an output format. It returns the output bytes and a summary that lists each page as a text page.
- [x] The CLI takes a source path and an output path, writes the Markdown, and prints the summary.

**Thai repair**
- [x] Wrapped lines are rejoined into paragraphs:
  - Thai + Thai: no space.
  - Thai + Latin: one space.
  - Latin + Latin: normal English joining, including rejoining hyphenated words.
- [x] Sara am is always one character, and NFKC is never applied anywhere.
- [x] Vowels and tone marks are reordered with PyThaiNLP's normaliser.
- [x] Spaces and zero-width characters that sit before a Thai combining mark are removed.
- [x] PyMuPDF's gap-based space insertion is avoided where its flags allow, and /ActualText is honoured.

**Markdown output**
- [x] An HTML comment page marker sits between pages.
- [x] A short summary block sits at the top.

**Tests**
- [x] Tests call only the conversion function, with small synthetic PDFs built from known text, and cover:
  - justified Thai paragraphs
  - a Thai–English line wrap
  - text that contains sara am

  Each output has zero broken text against the known text.
- [x] Before committing a synthetic Thai font file as a test asset, check that its licence allows redistribution.

## Comments

**2026-10-17, implementation notes**

- **PyMuPDF's space insertion is kept on purpose.**
  - Measured with characters spread 2–12 pt apart: PyMuPDF inserts no spaces between Thai letters, and does insert them between English words that have no space glyphs.
  - `TEXT_INHIBIT_SPACES` would glue such English words together ("Helloworld"), so it is not used.
  - /ActualText is honoured because `TEXT_IGNORE_ACTUALTEXT` is not set. There is no fixture for it yet, because PyMuPDF cannot write /ActualText.
- **PyThaiNLP's `normalize` deletes letters.**
  - On "เพิ ่ม" it removed the tone mark: `remove_spaces_before_marks` only handles a consonant before the space, and `remove_dangling` then drops the mark.
  - Thai repair therefore uses only PyThaiNLP's `reorder_vowels`, plus our own rules (see the review notes below).
- **Test font:** Sarabun (Google Fonts) under the SIL OFL 1.1, which allows redistribution with software when the licence file is included (`OFL.txt` sits beside it).
- **Run on the real 110-page contract (local only):**
  - 4.6 s.
  - No NUL or PUA characters, no decomposed sara am, no orphan marks.
  - The remaining structure problems are recorded on ticket 03.

**2026-10-17, changes after code review**

- **Hyphens.**
  - A hyphen at a line break is now kept, and the word is rejoined without a space ("long-term", "COVID-19", "2567-2568").
  - Only a soft hyphen (U+00AD) is dropped.
  - Why: Word does not hyphenate automatically, but it does break lines after hyphens that belong to the word. Dropping the hyphen ("conversion" from "conver-sion") would delete real letters far more often than it would fix auto-hyphenation.
- **Thai and Latin on one line.** PyMuPDF never inserts a space at a Thai/Latin boundary. The extractor now reads characters with their positions, and adds a space where a Thai character and a non-Thai character are set more than 0.2 em apart.
- **Spaces before marks.** Spaces (any whitespace) are removed only before marks above and below a consonant, and before sara am. A space before sara aa, sara a or lakkhangyao is kept ("สระ า").
- **Character repair.**
  - Sara aa stored before nikhahit is recomposed into sara am.
  - All zero-width characters and soft hyphens are removed: U+200B–U+200D, U+2060, U+FEFF and U+00AD.
- **Line joining.**
  - Leading spaces on a line are dropped, so an indented paragraph no longer becomes a Markdown code block.
  - Zero-width characters at line edges no longer cause an extra space.
- **Output format.** An output format that is not supported yet raises `ValueError`.
- **Real contract.** Rerunning it shows no text change; only 187 empty paragraphs are gone.

