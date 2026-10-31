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
