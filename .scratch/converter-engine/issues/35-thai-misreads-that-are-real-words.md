# 35: Thai misreads that leave real words are not marked

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, a Thai misread that leaves a word the word list holds is not marked as uncertain text. Examples:
- a dropped tone mark or vowel, as in "ที" for "ที่" and "เล็ก" for "เลิก";
- ช read as ซ;
- text that splits into real words.

The reader and the AI are not warned. These are the spec's known gap of "a misread that is itself a word". On the Thai contract among the local samples, five reviewers found them unmarked (ticket 27).

**Blocked by:** none

**Status:** needs-triage

**Split from:** ticket 27, on 2026-10-31. Ticket 27 cuts marks on correct text first, so that the marks a reader sees can be trusted before more are added.

**To decide at triage**
- **The signal:** a word that is rare, beside a look-alike that is far more common, such as one with ช for ซ or with a tone mark added. PyThaiNLP ships word frequencies from the Thai National Corpus under CC0. The question is how many marks on correct text such a check adds.
- **Measuring it:** the labelled sample of marks from ticket 27 counts only marks. This also needs misreads that went unmarked, so it needs real Thai scans with reference text (tickets 16 and 17).

**Also left from ticket 27.** Both need a table of Thai letters that look alike, such as ก/ค, ข/ค/ย and ช/ซ, which this ticket needs anyway:
- **An abbreviation misread as another goes unmarked.**
  - The case: "บพย." for "บพข.", since up to 4 consonants before a full stop are taken for an abbreviation.
  - On the Thai contract, "บพข." appears 19 times, "บพย." twice and "บพค." once.
  - The idea: mark an abbreviation that differs by one look-alike letter from one far more frequent in the same document.
  - The risk: "บพค." may be a real agency of its own. A mark only asks the reader to check, so the harm is small.
- **A misread is marked on its unknown piece only.**
  - The case: "กุณภาพ" for "คุณภาพ" is marked as "กุณ", since "ภาพ" is a syllable of two consonants and is not pulled in.
  - The idea: swap look-alike letters in the stretch around the unknown piece; if that makes a word the list holds, such as "คุณภาพ", mark that whole stretch.
  - Pulling in syllables of two consonants instead would also mark correct words, such as "หก" in "ทุกหกเคือน".
