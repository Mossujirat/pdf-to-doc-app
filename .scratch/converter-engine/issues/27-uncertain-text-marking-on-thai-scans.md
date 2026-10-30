# 27: Uncertain-text marking on Thai scans is off in both directions

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On the Thai scans of a real contract, uncertain text (ticket 11) marks a great deal of correct text and misses common misreads:
- **Marked though correct:** transliterated loanwords, such as chemical names; abbreviations with dots, such as academic degrees; abbreviations of agency names; one-letter words and list letters such as "(ก)"; and people's names.
- **Missed:**
  - a dropped tone mark or vowel that leaves another real word, or text that splits into real words;
  - ช read as ซ;
  - the known gap of misreads that are words.
- **Misplaced:** a mark sometimes sits on the character next to the error, or covers only part of a garbled word.

The file got 1,319 marks over 91 OCR pages, about 14 a page. When many marks fall on correct text, readers learn to ignore them, and the misreads they miss go unchecked.

**Blocked by:** none

**Status:** ready-for-agent

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`, whose attachments are scans pasted into Word pages, converted on 2026-10-23 with the user's permission. Five reviewers compared every page with its image.

**To decide at triage**
- **Words to accept:** which words the check should accept beyond the word list:
  - loanwords;
  - abbreviations with dots;
  - single letters in parentheses;
  - names that the text layer of the same file spells the same way.
- **Joining segments:** whether to judge a word after joining segments that the segmenter split, so that a misread splitting into real words is caught.
- **Measuring it:** the harness should measure how many marks fall on correct text, besides the share of errors left unmarked, which ticket 17 records. Both need real Thai scans with reference text (tickets 16 and 17).

## Comments

**2026-10-30, triage**

- **In the next deploy:** the user chose this ticket among the 6 to be done before it. See `.scratch/next-deploy.md`.
- **Next:** `/grill-with-docs`, then `/implement`.
