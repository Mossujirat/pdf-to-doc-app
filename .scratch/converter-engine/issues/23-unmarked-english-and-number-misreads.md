# 23: English and number misreads are not marked

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, misreads in English words and in numbers reach the output without being marked as uncertain text:
- **Digits read as letters.** A contract amount's zeros came out as the letter o, in the form "12,ooo.oo", and so did the zero of a percentage.
- **Capitals read as small letters,** inside an abbreviation, a budget code and a proper name.
- **"I" read as "l".**

In a contract these are amounts, codes and names, where a wrong character changes the meaning. The reader and the AI are not warned.

**Blocked by:** none

**Status:** ready-for-agent

**Seen on:** a five-page English agreement among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission. It was printed to PDF with its text drawn as shapes, so every page is read with OCR. All four uncertain spots the converter marked are handwriting, and none of them is a misread.

**More of it on Thai scans:** a 110-page Thai contract among the same samples, with scans pasted into Word pages, was converted on 2026-10-23 with the user's permission. None of the following was marked.
- **Numbers:**
  - a footnote marker joined onto the number before it, which gained a digit;
  - a day in Thai digits read as Arabic digits of another value;
  - a year that lost its last digit;
  - a page count "x/y" read as one number;
  - a range that lost its dash;
  - a count dropped from five of seven table rows;
  - an extra digit in a tax amount.
- **Latin words inside Thai lines,** read with Thai letters that look alike: s as ร, n as ท, u as น, o as ๐. Only some of these were marked. This puts in question ticket 08's finding that the Thai recogniser reads English on the same line correctly. That held on the English sample's scans, but not on these.

**Why they pass:** uncertain text (ticket 11) has two signals:
- a Thai word that the word list does not hold;
- a box read with confidence below 0.85.

English words and numbers meet only the second signal, and these misreads were read with confidence. The spec's known gap already lists lost digits. Letters in place of digits are a gap of their own, and they are easier to catch.

**To decide at triage**
- **Numbers:** mark a number that holds a letter OCR often reads in place of a digit, such as o, O, l, I or S between digits, as uncertain. Never silently change it: the converter does not invent text.
- **English words:** whether to check them against an English word list, as Thai words are, and which list, since it must be AGPL-compatible.
- **Case:** whether a word whose case changes in the middle, such as "aBC", should be marked.
- **Measuring it:** synthetic English scans in the corpus with amounts and codes, so that the harness measures this.

## Comments

**2026-10-30, triage**

- **In the next deploy:** the user chose this ticket among the 6 to be done before it. See `.scratch/next-deploy.md`.
- **Next:** `/grill-with-docs`, then `/implement`.
