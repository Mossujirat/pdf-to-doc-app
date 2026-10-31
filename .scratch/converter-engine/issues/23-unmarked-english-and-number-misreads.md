# 23: English and number misreads are not marked

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, misreads in English words and in numbers reach the output without being marked as uncertain text:
- **Digits read as letters.** A contract amount's zeros came out as the letter o, in the form "12,ooo.oo", and so did the zero of a percentage.
- **Capitals read as small letters,** inside an abbreviation, a budget code and a proper name.
- **"I" read as "l".**

In a contract these are amounts, codes and names, where a wrong character changes the meaning. The reader and the AI are not warned.

**Blocked by:** none

**Status:** done

**Branch:** `fix/english-and-number-misreads`

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

**2026-10-31, how these misreads are found (decided with the user)**

**Scope.** This ticket only. Ticket 27, on Thai words, gets its own grilling afterwards, though both change the same marking.

**A third signal: the shape of a word.** No English word list is used. The misreads seen are letters in numbers, case and "l" for "I", which a word list would not catch, while names, company names and abbreviations in contracts would be marked wrongly. Instead, OCR text read with confidence is uncertain where a word or number has the shape of a typical misread. Each rule marks the whole word or number:
- **A letter in a number.** A word that holds at least one digit, and becomes a number when each o, O, l and I in it is read as 0 or 1, such as "12,ooo.oo" or "1o%". S, B and Z count only between two digits. Codes such as "A4", "S1" and "COVID-19" are not marked.
- **A small letter inside a word in capitals.** A word with at least two capitals that holds a small letter shaped like its capital (c, o, s, u, v, w, x, z, k, p) or an l, such as "BKk" or "THAlLAND". Not marked: "PhD", "iPhone", a plural s at the end ("PDFs") and "Hz" ("MHz").
- **A lone "l".**
- **Thai and Latin letters in one word.** A single Thai letter or Thai digit inside a Latin word, or joined to one, such as "Bนs" or "c๐de". Thai text joined to an English name on purpose, such as "บริษัทABC", is not marked.
- **Thai and Arabic digits in one number,** such as "๑5".

**Never changed.** The text is only marked. The converter does not invent text.

**Still a known gap.** Numbers misread as other numbers: a year that lost a digit, an extra digit, a footnote marker joined to the number before it, "x/y" read as one number, a range that lost its dash. Their shape does not show it. The spec's known gap names them.

**Spec to update.** The spec says, from ticket 08, that the Thai recogniser reads English on the same line correctly. That held on the English sample, but on the Thai scans Latin words were read with Thai look-alikes. Note this beside it.

**Measuring.** An English contract page with amounts, percentages, codes, abbreviations and names goes into `corpus/degraded/`, damaged at the same five levels as the Thai page. With real PaddleOCR the harness reports the errors left unmarked and the correct text marked, before and after. Fast tests cover each rule with the fake engine.

**2026-10-31, built**

**The rules,** in `misreads.py`, marked through `uncertain_spans` beside unknown Thai words. Two changes from the plan, both from measuring:
- **"l" alone became any word spelt only with l and I that holds an l.** The damaged English page read "Schedule II" as "Il" or "ll" on three of five pages, which a lone "l" missed. "Ill" is the one English word spelt so, and is left alone. Decided with the user.
- **An o between capitals is not marked,** as in "ToR" and "MoU", where it stands for "of". The GIZ sample writes "ToR" so, and it was the only correct text the rules marked on the samples. The cost: "TOR" misread as "ToR" goes unmarked.

**Left as known gaps,** which the spec's known gap names:
- a digit read in place of a letter, "Is0" for "ISO", left with the user, since codes such as "A0" and "B10" have the same shape;
- a change of case that leaves a normal word, "Iso" or "NO.".

**The harness, real PaddleOCR, `corpus/degraded`:**

| Pages | Errors left unmarked, before | After | Correct text marked |
|---|---|---|---|
| English, five levels of damage | 94–100% | 28–50% | none |
| Thai, five levels | the same marks as before | | none |
| All ten | 83% | 47% | none |

What the English pages still leave unmarked: "NO." for "No.", "Iso" or "Is0" for "ISO", "ToR" for "TOR", and lost full stops.

`corpus/synthetic` gives the same report as before, page by page.

**The real samples,** converted locally with the user's standing permission. Marks that hold a word or number shaped like a misread:

| Sample | Marks | Seen |
|---|---|---|
| SSFA, 5-page English agreement | 4 | all misreads: "43,ooo.oo", "O0100" for the postcode 00100, "SsFA", "lIB" |
| GIZ supplement, English scans | 98; 102 before "ToR" was left alone | misreads such as "GlZ" for GIZ (42 times), "MsMEs" and "ScP", checked against the page image, "900,00o.00", "321,O00.00", "BMUKkN", "UNFccC"; and "ToR"/"ToRs", correct, now left alone |
| 110-page Thai contract | 187 | English words read with Thai look-alikes, such as "Viscoรity", "adheรive", "Ruptนre", "พHO"; Thai years with Arabic digits, such as "๒56๒"; "DccE" for DCCE |

**2026-10-31, after code review**

**Fixed:**
- **A number is matched whole or not at all.** "1O1A" had its "1O" marked, because the match stopped short of the code's end. Now a code such as "1O1A" is left alone, like "B2B".
- **A Roman numeral before a clause's number is not a misread,** as in "Annex I.2" or "Part II.3": look-alike letters at the start, followed by a full stop or comma, are not read as digits. "O0100" is still marked.
- **One definition of a digit, a Thai letter, mai yamok and paiyannoi:** `misreads.py` takes them from `thai.py` and `words.py`, and builds its look-alike letters from its own tables. The two damaged documents in `corpus/generate.py` come from one helper.
- **The glossary** names one example of a misread shape, not the list of rules.

**Recorded, not changed:**
- **The small-letter rule marks a word only when every small letter in it is shaped like its capital.** Read literally, the plan would mark "McDonald"; this way it does not, but "THAlLANd" goes unmarked.
- **Correct text it can still mark:** names written in mixed case with a look-alike small letter, such as "PwC" and "AusAID"; "O2"; "5l" for five litres; a one-letter Thai word joined to English, such as "ณBangkok". None of them was in the samples.
- **The "of" exemption** also leaves "VoIP" and "SoW" alone, which is right for them.

**Checked after the fixes:** `corpus/degraded` and `corpus/synthetic` give the same reports as before them. On the samples, the only marks that changed are the four "ToR"/"ToRs" left alone. pytest: 682 passed, 1 skipped; `pytest -m ocr`: 27 passed; mypy clean.
