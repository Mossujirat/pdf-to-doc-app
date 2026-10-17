# 01: Tracer bullet: text-page PDF → Markdown

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user runs the CLI on a PDF whose pages all have a correct text layer and gets Markdown in which the Thai text reads exactly as on the page. This first slice runs end to end:

- the conversion function, which is the main seam, and the CLI as a thin wrapper over it
- text-layer extraction with PyMuPDF into a minimal document model (paragraphs and page boundaries)
- the core Thai repair rules
- the Markdown renderer

It also sets up the project skeleton every later ticket builds on.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Branch:** `feat/text-pages`

**Project skeleton**
- [ ] A Python 3.13 package with pinned dependencies, an AGPL-3.0 licence file, a `.gitattributes` forcing LF line endings, and a test runner that runs with one command.

**Conversion function and CLI**
- [ ] The conversion function takes a source file and an output format. It returns the output bytes and a summary that lists each page as a text page.
- [ ] The CLI takes a source path and an output path, writes the Markdown, and prints the summary.

**Thai repair**
- [ ] Wrapped lines are rejoined into paragraphs:
  - Thai + Thai: no space.
  - Thai + Latin: one space.
  - Latin + Latin: normal English joining, including rejoining hyphenated words.
- [ ] Sara am is always one character, and NFKC is never applied anywhere.
- [ ] Vowels and tone marks are reordered with PyThaiNLP's normaliser.
- [ ] Spaces and zero-width characters that sit before a Thai combining mark are removed.
- [ ] PyMuPDF's gap-based space insertion is avoided where its flags allow, and /ActualText is honoured.

**Markdown output**
- [ ] An HTML comment page marker sits between pages.
- [ ] A short summary block sits at the top.

**Tests**
- [ ] Tests call only the conversion function, with small synthetic PDFs built from known text, and cover:
  - justified Thai paragraphs
  - a Thai–English line wrap
  - text that contains sara am

  Each output has zero broken text against the known text.
- [ ] Before committing a synthetic Thai font file as a test asset, check that its licence allows redistribution.
