# Converter engine and CLI (v1)

Status: ready-for-agent

## Problem Statement

Thai office workers turn PDFs and Word files into text for two jobs: pasting the content into an AI chat, and editing it in Word. Existing converters break Thai text:
- Vowels and tone marks float loose, go missing, or turn into odd characters.
- Spaces appear inside words.
- Sentences are cut at every printed line.
- Thai inside table cells loses its marks.
- Scanned pages come out empty.

Real documents make this worse:
- A signed contract is often mostly scans with a few text pages, in the same file.
- Some PDFs carry a text layer that is itself wrong, such as "กำร" where the page shows "การ".

The user cannot trust any output, so they re-read or retype it. An AI chat that gets broken text gives wrong answers with confidence.

The documents are often confidential, so the user also needs to know the file goes nowhere else.

## Solution

A converter that turns a source file (PDF or DOCX) into an output (Markdown or DOCX) whose text reads exactly as the original. It works page by page:

- **Text pages:** text is taken from the text layer and passed through a Thai repair step.
- **OCR pages:** text is read from the page image. These are scans, and pages whose text layer cannot be trusted.

Everything is collected into one document model, and both output formats are rendered from it.

Where the converter cannot confirm that it read text correctly, it marks that text as uncertain text instead of hiding the problem. Each output starts with a summary of which pages were read by OCR and how much text is uncertain.

**Delivery order.** v1 is a command-line tool, built around one conversion function. It comes with a quality harness that measures broken text against reference text, and a Docker image for running the tests on Linux. The public web service is a separate spec that wraps the same function. It launches once uncertain text (ticket 11) is done; the quality gate measures the converter but does not hold the launch back (decided 2026-10-21).

## User Stories

1. As a document user, I want to convert a PDF to Markdown, so that I can paste it into an AI chat and get answers based on the real content.
2. As a document user, I want to convert a PDF to DOCX, so that I can edit the content in Word.
3. As a document user, I want to convert a DOCX to Markdown, so that Word documents I receive can also go into an AI chat cleanly.
4. As a document user, I want every Thai vowel and tone mark attached to the right consonant, so that each word reads as it does in the original.
5. As a document user, I want no spaces inside Thai words, so that words are not split in two.
6. As a document user, I want lines that wrap in the PDF joined back into paragraphs without a space between Thai words, so that sentences are not cut at every printed line.
7. As a document user, I want Thai and English text joined with a single space where a line wraps between them, so that mixed-language sentences read naturally.
8. As a document user, I want sara am (ำ) always output as one character, so that search and AI models treat the word correctly.
9. As a document user, I want scanned pages read automatically with OCR, so that I never get an empty output for a scan.
10. As a document user, I want a file that mixes text pages and scanned pages handled page by page, so that each page uses the right method.
11. As a document user, I want a page whose text layer is wrong (such as "กำร" for "การ") detected and read with OCR, so that errors inside the file do not reach my output.
12. As a document user, I want headings kept as headings, so that the AI and I can see the document's structure.
13. As a document user, I want numbered and bulleted lists kept as lists, so that clauses and items stay separate.
14. As a document user, I want tables kept as tables, with the Thai text inside each cell intact, so that budgets and schedules stay readable.
15. As a document user, I want merged table cells preserved, so that complex tables keep their meaning. In Markdown this means an HTML table; in DOCX, real merged cells.
16. As a document user, I want repeated page headers, footers and page numbers removed, so that they do not interrupt the text or waste AI tokens.
17. As a document user, I want a page marker between pages in Markdown, so that the AI can tell me which page a fact came from.
18. As a document user, I want images, signatures, stamps and handwriting replaced by short placeholders such as `[ลายเซ็น]`, so that I know something was there without getting invented text.
19. As a document user, I want uncertain text marked where it appears, so that I know exactly which words to double-check.
20. As a document user, I want a summary at the top of each output listing the OCR pages and the number of uncertain spots, so that I can judge how much to trust the output before reading it.
21. As a document user, I want uncertain text in DOCX highlighted yellow, with the summary on the first page, so that I can find and clear it in Word.
22. As a document user, I want Thai text in DOCX set in TH Sarabun New with the correct complex-script font settings, so that it displays properly in Word on any machine.
23. As a document user, I want Thai digits kept as Thai digits and English text kept as written, so that the output matches the original.
24. As a document user, I want English documents converted to the same standard as Thai ones, so that I can use one tool for both.
25. As a document user, I want to choose Accurate mode for an important document, so that I get better OCR in exchange for a much slower conversion.
26. As a document user, I want to give the password for a password-protected PDF, so that I can still convert my own protected files.
27. As a document user, I want a clear message when a PDF forbids copying text, explaining why it will not be converted, so that I understand the refusal.
28. As a document user, I want a clear message when I give a legacy .doc file, telling me to save it as .docx first, so that I know how to proceed.
29. As a document user, I want a clear message when a file is over 50 MB or 150 pages, so that I know why it was rejected.
30. As a document user, I want to see progress while a long file converts (such as "OCR page 23/85"), so that I know how long to wait.
31. As a document user, I want conversion to work fully offline with no network calls, so that my confidential file never leaves the machine running the converter.
32. As a document user, I want no copy of my source file or output left behind after conversion, except the output I asked for, so that confidential content does not linger.
33. As a developer, I want one conversion function with the CLI as a thin wrapper, so that the future web service can reuse it unchanged.
34. As a developer, I want the OCR engine behind a swappable interface, so that I can change or add engines without touching the rest of the converter.
35. As a developer, I want a fake OCR engine for tests, so that page routing, uncertain-text marking and placeholders can be tested quickly and deterministically.
36. As a maintainer, I want one command that runs the converter over the test corpus and reports broken text by category, so that I can tell whether a change helps or hurts.
37. As a maintainer, I want a test corpus of synthetic and public documents committed to the repo, so that anyone can run the quality checks without confidential files.
38. As a maintainer, I want to point the quality harness at a local folder of confidential reference text, so that real documents are measured without entering the repo.
39. As a maintainer, I want synthetic test PDFs generated from known text in several fonts, including a legacy font that produces Private Use Area glyphs, and with simulated scans, so that every known Thai failure mode has a fixture with exact reference text.
40. As a maintainer, I want a quality gate of zero broken text on text pages and a recorded OCR baseline, so that the converter's quality has an objective measure.
41. As a maintainer, I want the test suite to run in a Linux Docker container, locally and in CI, so that results match the future server and not only Windows.
42. As a quality reviewer, I want a per-page report (page kind, OCR engine, character error rate against reference text, broken-text counts by category, uncertain count), so that I can see where quality is lost.
43. As a self-hoster, I want to run the converter from a Docker image, so that I can use it on my own machine, as the AGPL licence intends.
44. As a document user, I want text that an OCR engine adds on its own (such as image descriptions) dropped in favour of placeholders, so that the output never contains invented content.
45. As a document user, I want a 110-page mixed document to convert in default mode within roughly 15 minutes on an ordinary CPU, so that conversion is practical without a GPU.

## Implementation Decisions

### Shape

- **Python**, targeting Python 3.13; this matches the benchmarks.
- **Licence:** AGPL-3.0 for the whole project (ADR 0002). Every dependency must be AGPL-compatible.
- **The conversion function is the main seam.**
  - **Inputs:** a source file, the output format (Markdown or DOCX), the mode (default or Accurate) and an optional password.
  - **Returns:** a conversion result holding the output bytes and a summary. The summary lists each page's kind (text page or OCR page), the OCR engine used, and the number of uncertain spots.
  - **Errors:** typed errors for password required, copy restricted, unsupported format (legacy .doc) and too large.
  - **Progress:** an optional callback receives progress (stage, current page, total pages). The web service will use this later for its progress display.
- **The CLI is a thin wrapper.** It takes a source path, the output format, an Accurate-mode flag, an optional password and an output path. It prints progress and the summary, and exits with distinct codes for each error type.
- **The OCR engine interface is the only other seam.** An engine reads one page image for the given languages. It returns text blocks with positions and confidence scores, plus any table structure it can produce. There are three implementations:
  - PaddleOCR: the default.
  - Typhoon OCR: Accurate mode.
  - A fake engine: tests only.
- **No other seams.** Thai repair, page classification, the document model and the renderers are tested through the conversion function.

### Modules

**Source intake**
- Detects the source type from the file content, not the file name.
- Refuses legacy .doc.
- Enforces 50 MB and 150 pages.
- Opens encrypted PDFs with the user's password, and refuses PDFs whose permissions forbid copying.

**Page classifier**
- Decides text page or OCR page for every PDF page.
- **Never decide from character count alone.** A stamped header line can sit on top of a scanned body. Use body-text coverage and image coverage.
- **Validate the text layer.** It fails when any of these hold:
  - The share of Thai tokens that are dictionary words is low. In the benchmark, broken pages scored 74–89% and good OCR scored 97% or more; set the threshold from the corpus.
  - It contains Private Use Area characters that cannot be mapped.
  - It contains replacement characters.
  - It shows sara-am anomalies.

  A page whose text layer fails becomes an OCR page.

**Text-layer extractor**
- **Library:** PyMuPDF, honouring /ActualText. Disable PyMuPDF's gap-based space insertion where its flags allow.
- **Input:** character and word positions.
- **Tables:** use PyMuPDF's table finder only for the cell grid. Assign each word to the cell that contains the word's centre. Never clip text to the cell box, because that drops vowels above and below the line.

**Thai repair**
- Applies to text from both text pages and OCR pages.
- **Character fixes:**
  - Never apply NFKC.
  - Recompose sara am.
  - Reorder vowels and tone marks with PyThaiNLP's normaliser.
  - Map legacy Private Use Area glyphs back to Thai.
  - Remove spaces and zero-width characters that sit before a combining mark.
- **Line joining:**
  - Thai + Thai: no space.
  - Thai + Latin: one space.
  - Latin + Latin: normal English rules, including rejoining hyphenated words.
- **Word segmentation:** use it only to check text, never to insert spaces.

**Header and footer removal**
- Remove lines that repeat in the same position across pages, including stamped header lines on scans.
- Page counters such as "หน้าที่ x/y" restart in each appendix. They are removed, never used as page numbers.

**OCR adapters**

- **PaddleOCR (default)**
  - Pin paddlepaddle 3.2.2; version 3.3.1 crashed at inference.
  - Models: PP-OCRv5 mobile detector; the Thai mobile recogniser. It reads English words and digits on the same line correctly, and on the English sample's scans it agrees with the English recogniser on 99.3–99.8% of characters, so the English recogniser is not used (ticket 08). On the Thai scans of a real contract, though, it read some English words inside Thai lines with Thai letters that look alike, such as s as ร; uncertain text marks these (ticket 23).
  - Detector input limited to a longest side of 1280 px. Defaults split Thai marks into separate boxes and were far worse: CER 11.8% instead of 4.0%, at four times the time.
  - Orientation and unwarping off.
  - Scanned table structure: found from the rules in the page image, through the OCR engine interface, on every OCR page (spec `.scratch/tables-on-ocr-pages/`). PP-StructureV3 was measured and rejected. A table whose text cannot be placed in its cells with certainty is an incomplete table: its printed lines one by one, after the label `[ตารางอาจไม่สมบูรณ์]`, which is not a placeholder. A table with no rules comes out one line per row, with no label.
- **Typhoon OCR 1.5 2B (Accurate mode)**
  - The GGUF Q8 build through llama-cpp-python, with flash attention on, and the prompt from the model card.
  - It outputs HTML tables, which feed the document model's tables.
  - It writes descriptions of images; these are replaced by placeholders.

**Uncertain text** (ticket 11)
- Only text that OCR read can be uncertain. Text taken from a text layer never is.
- Three signals mark it, decided with the user on 2026-10-21 and 2026-10-31:
  - **A Thai word that the word list does not hold.** A misread mark or letter usually leaves one, such as "ผู้อืน" for "ผู้อื่น". The word is marked, not its whole line. This works for any engine, Typhoon included, which gives no confidence at all.
  - **A word or number shaped like a misread** (ticket 23). English words are not looked up in a word list, since a contract's names, codes and abbreviations would fill it with false alarms. The whole word or number is marked:
    - a number with letters read in place of its digits, such as "12,ooo.oo": it becomes a number when each o, O, l and I is read as 0 or 1, and S, B and Z between two digits as 5, 8 and 2. A code such as "1O1A" is not, nor a Roman numeral before a clause's number, such as "I.2";
    - a word in capitals whose every small letter is shaped like its capital, such as "BKk" or "THAlLAND", but not a plural s ("PDFs"), "Hz", or an o between capitals that stands for "of" ("ToR", "MoU");
    - a word spelt only with l and I that holds an l, such as "Il" for the Roman numeral II, but not "Ill";
    - a Latin word holding or joined to a single Thai letter or digit, such as "Teamร";
    - a number in both Thai and Arabic digits, such as "๑5".
  - **A box the engine read with a confidence below 0.85.** The whole box is marked.
- The confidence alone could not be the signal. PaddleOCR scores a whole line, and one wrong mark barely moves the score. On synthetic scans at six levels of damage, lines with one or two wrong characters scored 0.93–0.96, as did lines with none, while lines read as nonsense scored 0.64–0.75. Catching small misreads by confidence would have meant marking about a third of all text.
- Neighbouring uncertain words, with only whitespace between them, are marked as one stretch.
- **Known gap:** a misread that is itself a word is not marked, such as "ที" for "ที่" or "ทาก" for "หาก". Neither are punctuation, a digit read in place of a letter ("Is0" for "ISO"), a change of case that leaves a normal word ("Iso", "NO."), or a number misread as another number: a lost or extra digit, a footnote marker joined to the number before it, "x/y" read as one number, a range that lost its dash. The harness reports the share of errors left unmarked, so that ticket 17 can measure it on real scans.
- `corpus/degraded/` holds scans damaged on purpose, outside the quality gate, for measuring this with the harness.
- Handwriting is not transcribed:
  - Where it can be identified, it becomes a placeholder: Typhoon tags it, and it can be an image object on a text page.
  - Otherwise, low-confidence handwriting becomes uncertain text, never silent output.

**Placeholders** (ticket 09)
- Images on text pages become placeholders where they sit in reading order. OCR pages are images themselves and get none.
- A round coloured mark is a stamp, wherever it is pressed. A small image on a row to sign on ("ลงชื่อ", "ลายมือชื่อ", "Signature") is a signature. Anything else is an image: the converter does not guess.
- Not placeholders: images too small to be pictures (rules, bullets), the page behind the text (a scan made searchable, a watermark), and page furniture: images of the same size in about the same place at an edge of two or more pages.
- An image inside a table cell is placed right after the table.
- The summary counts placeholders by kind.

**Document model** (ADR 0003)
- **Block kinds:**
  - headings with a level
  - paragraphs made of text runs, each run flagged if uncertain
  - list items
  - tables with cells, row spans and column spans
  - incomplete tables, with their printed rows, each a line with its uncertain text
  - placeholders with a kind (image, signature, stamp, handwriting, scan)
  - page boundaries with the original page number
- Every block records its source page.
- The summary is built from the model.

**DOCX reader**
- Reads DOCX structure straight into the document model:
  - headings by style
  - lists, with the numbers Word draws worked out as Word counts them (ticket 13)
  - tables with merges
  - images as placeholders
- DOCX text is already Unicode, but it still passes through the character-level Thai repair.
- Pages are where Word's last layout broke them, as Word records on saving; a file without those records breaks pages at typed breaks (ticket 13).
- The 150-page limit counts those pages. A DOCX that unpacks to more than 200 MB is refused as a zip bomb, and a password-locked Office file is recognised and refused (ticket 13).
- A list within a list keeps its depth: list items carry a level, and Markdown indents them (ticket 13).
- DOCX-to-DOCX is refused with its own error.

**Markdown renderer**
- GitHub-flavoured Markdown.
- Tables:
  - HTML tables when any cell is merged.
  - Otherwise, Markdown tables.
- An HTML comment page marker between pages.
- Uncertain text wrapped in an HTML `<mark>` element. Most viewers highlight it, and AI models understand it.
- Placeholders in Thai square brackets, such as `[ลายเซ็น]`.
- A short summary block at the top, explaining what `<mark>` means.

**DOCX renderer**
- Uses python-docx.
- Thai font is TH Sarabun New, set in the complex-script slot with its matching size; python-docx's plain font name does not set that slot. English text uses TH Sarabun New too, at the same size (ticket 07).
- Runs that hold Thai are marked complex script, so Word breaks their lines between words. English words get runs of their own without the mark, or Word would proof them as Thai (ticket 07).
- Each page of the original starts a new page, at its own first paragraph (ticket 07).
- Headings use Word heading styles.
- Bulleted list items use Word's bullets. Items that keep their own number or letter go in a Word list that shows nothing before them (ticket 07).
- Tables have real merged cells.
- Uncertain text is highlighted yellow.
- The summary goes on the first page.

**Privacy at runtime**
- No network access while converting: models are downloaded at install or build time, never on first use.
- A conversion writes no temporary files: pages are rendered in memory and handed to the OCR engine as arrays (ticket 12).
- Each conversion loads its own OCR engine and drops it when it ends, because Paddle keeps the last page it read in its predictors (ticket 12).
- File content is never logged.

**Packaging**
- Pinned dependencies.
- A Dockerfile that builds a Linux image with the default-mode models baked in, used to run the tests and the CLI.
- A `.gitattributes` that forces LF line endings, because the working machine converts to CRLF.
- An AGPL-3.0 licence file.

**Quality harness**
- A CLI command that converts every source file in a corpus folder and compares each page against its reference text.
- **Normalisation before comparing:**
  - collapse whitespace
  - apply NFC
  - never apply NFKC
- **Reports, per page and in total, in JSON and as a readable table:**
  - character error rate, overall and Thai-only
  - broken text by category (orphan marks, spaces inside words, PUA characters, decomposed sara am, missing text)
  - page kind
  - engine
  - uncertain count
- **Corpora:**
  - the committed corpus
  - any local folder given on the command line, such as the confidential reference pages kept outside git

**Test corpus**
- A generator for synthetic sources:
  - known Thai and English text written to DOCX, then exported to PDF in several fonts, including a legacy font that produces Private Use Area glyphs
  - justified paragraphs
  - tables with merged cells
  - stamped headers
  - mixed text and scanned pages, made by rendering pages to images at about 200 dpi with mild noise and rotation
- Public Thai government documents whose licence allows redistribution, with hand-checked reference text.
- Confidential real pages stay local. The user is preparing reference text from 12 Typhoon drafts.

## Testing Decisions

- **A good test calls the conversion function with a real source file.** It asserts only on what a user would see: the output text, parsed back from Markdown or read from the DOCX, and the summary. It never asserts on internal structures, intermediate text or which helper ran.
- **Fast tests** are deterministic and run on every change. They use small synthetic fixtures. They use the fake OCR engine wherever OCR is involved, which isolates:
  - page routing
  - text-layer validation
  - uncertain-text marking
  - placeholder rendering
  - summary content
- **Each broken-text failure mode gets at least one fixture that reproduces it:**
  - justified Thai text where naive extraction inserts spaces
  - marks reordered by a Word export
  - legacy Private Use Area glyphs
  - a wrong ToUnicode map (the "กำร" case)
  - Thai inside table cells
  - merged cells
  - a stamped header over a scanned body
  - a Thai–English line wrap
- **DOCX output checks:**
  - Read the file back and confirm the complex-script font and size, the yellow highlight on uncertain text, merged cells and heading styles.
  - Once per milestone, open the file in real Word and check that Thai renders correctly; automated checks cannot see glyph rendering.
- **Corpus tests run real PaddleOCR in the Linux container, in CI and locally.**
  - The quality gate is zero broken text on text pages.
  - For OCR pages, the first run records a baseline (CER and the share of errors left unmarked). Later runs flag regressions against it.
  - The numeric OCR target is set after the baseline has been measured on real scans (decision Q27).
- **Accurate mode (Typhoon) tests stay out of CI.** The model is 2.6 GB and takes about 4 minutes a page on CPU. They run on demand on a developer machine.
- **Prior art:** there is no code in the repo yet. The local benchmark scripts kept beside the confidential reference pages show the CER method and normalisation already used. The research notes in `docs/research` record the numbers to compare against.

## Out of Scope

- The public web service: upload page, queue and progress page, output retention, hosting, GPU. It gets its own spec.
- Converting legacy .doc files, and DOCX-to-DOCX.
- Transcribing handwriting.
- Languages other than Thai and English.
- Layout-faithful DOCX that reproduces the original's page positions.
- Any third-party AI or cloud OCR service.
- Converting PDFs whose permissions forbid copying.

## Further Notes

**Decided for the web spec, recorded here so they are not lost:**
- Conversion runs on our server (ADR 0001).
- The source file is deleted when conversion ends; the outputs are held for 10 minutes after it ends, or until the user deletes them (changed 2026-10-21, ADR 0001).
- No content logging and no third-party AI.
- Free with no login; starts on a CPU-only server.
- Limits: 50 MB and 150 pages.
- Progress display and a queue, one file per user at a time.
- Thai UI first, English later.
- The web page explains, with pictures, how a conversion works: each page read from its text layer or with OCR, how an untrustworthy text layer is caught, the Thai repair, placeholders, one document model for both outputs, and where the file goes and when it is deleted. Its examples are synthetic, never taken from real documents (added 2026-10-21).
- That section, "ข้างในทำอะไรกับไฟล์ของคุณ" in `src/pdf_to_doc/web/pages.py`, states the converter's rules as they are. A change to any rule it shows changes the section in the same ticket. The rules it shows are:
  - intake and its limits
  - when a page is read with OCR
  - the three checks of a text layer and their thresholds
  - the Thai repair
  - structure, page furniture and placeholders
  - uncertain text in both outputs

  Its numbers come from the code that applies them: `MAX_BYTES`, `MAX_PAGES`, `MIN_DICTIONARY_SHARE` and `MIN_WORDS_TO_JUDGE` (added 2026-10-22, ticket 12 of the web service).
- The Docker container runs with no network and in-memory scratch space.
- The GitHub repo becomes public before the web service launches (AGPL).

The web-service grilling on 2026-10-21 settled the rest, including the sandbox (ADR 0004) and the public entry (ADR 0005). The web spec records it.

**Delivery branches.** Tickets are grouped into branches. Each ticket is a commit on its branch, and each branch merges into `main` through a PR once all of its tickets are done.

| Branch | Tickets |
|---|---|
| `feat/text-pages` | 01–06 |
| `feat/docx` | 07, 09, 13 |
| `feat/ocr` | 08, 10–12, 14, 15 |
| `chore/quality-gate` | 16, 17 |

`feat/ocr` merges in three PRs, at the user's choice:
1. **08, 10 and 12** (2026-10-20), so that `feat/docx` starts from a `main` that already reads OCR pages.
2. **11 alone** (2026-10-21), because the web service launches once it is in.
3. **14 and 15.**

Tickets 11, 14 and 15 need 07 and 09 from `feat/docx`.

**Glossary.** Domain terms follow `GLOSSARY.md`: source file, document model, output, conversion, Accurate mode, broken text, uncertain text, placeholder, reference text, text layer, text page, OCR page.

**Open questions to settle during implementation:**
- Does PaddleOCR's Thai recogniser handle English words and digits on the same line, or does a page need both recognisers?
- Whether PP-StructureV3 gives usable scanned tables on CPU.
- Whether speed and results on Linux match the Windows benchmarks.
- How multi-column layouts behave. This was not discussed, and the samples are single-column.
- How well Typhoon handles English.
- Whether placeholders and the summary should switch to English for English-only documents.
