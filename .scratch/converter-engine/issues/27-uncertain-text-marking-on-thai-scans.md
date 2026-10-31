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

**Status:** done

**Branch:** `fix/thai-uncertain-marks`

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

**2026-10-31, what was measured (grilling)**

**All the marks on the Thai contract,** converted again locally with ticket 23's rules. There are 1,395 marks:

| What marked it | Marks |
|---|---|
| a Thai word that the word list does not hold, alone | 996 |
| a box read with confidence below 0.85, alone | 135 |
| a misread shape (ticket 23), alone or with others | 187 |
| more than one of these | the rest |

The segmenter cuts transliterated words and names it does not know into pieces, and only the pieces it cannot place are marked. So "ลิ**ก**โนเซลลูโลสิ**ก**" has two one-letter marks, and a misread word is often marked on one piece of it.

**200 marks, labelled against the page images:** 200 marks were drawn at random. Each was shown above a crop of the line it was read from, and labelled by Claude.

| Label | Marks |
|---|---|
| a misread, or not text, such as a signature or a tick | 149 |
| correct text | 46 |
| unclear | 5 |

Several marks that looked correct in the crops were misreads with a stray or swapped mark, such as "สื้น" for "สิ้น" or "กรั้ม" for "กรัม". The 46 marks on correct text:

| Kind | Marks | Examples |
|---|---|---|
| transliterated words cut into pieces | 20 | "ฟอร์มัล\|ดีไฮด์" 13 times, "แบคทีเรีย", "มอดุลัส" |
| names | 7 | "ณัช\|ชา", "รังษีสันติวานนท์" |
| "ณ" | 7 | "ณ วันที่" |
| abbreviations with full stops | 7 | "บพข.", "ส.", "ผพว." |
| a box read with low confidence | 4 | a page number "- 2 –", years on a chart |
| a letter in parentheses | 1 | "(ค)" |

**Prototypes, on the 200 labelled marks:**

| Accepting | Correct marks removed | Misreads lost |
|---|---|---|
| "(ก)", abbreviations with full stops, "ณ" | 14 of 46 | 0 |
| and PyThaiNLP's names list | 16 | 6: short names accept pieces such as "ร" |
| and the Volubilis dictionary | 17 | 5 |
| and words in the text layer of the same file | 14 | 3 |
| and Thai Wikipedia titles of 5 letters or more, matched against pieces joined to their neighbours | 30 | 0 |
| the same, of 4 letters or more | 31 | 2: "ตั้ว", "ลั่ว" |

Joining pieces and looking the result up in a set gave the same result as re-segmenting with the bigger list. It loads in 0.2 s, against 20 s and hundreds of MB for a segmenter dictionary.

**Checked on marks outside the sample:** these rules unmark 156 of the 1,395 marks. 40 of the unmarked ones, outside the labelled sample, were checked against the images:
- 36 were correct text;
- 1 was unclear;
- 2 or 3 were misreads:
  - "กุ**ณ**ภาพ" for "คุณภาพ", unmarked by the "ณ" rule; requiring a space either side keeps it marked;
  - "บพย." for "บพข.", unmarked by the abbreviation rule;
  - a correct piece, "ทรอนิกส์", inside a garbled stretch.

Estimate for the whole file: about half the marks on correct text go, and about 5–8% of the marks removed were misreads.

**2026-10-31, decided with the user**

- **Scope:** too many marks only. Misreads that are left unmarked, such as ช read as ซ or a lost tone mark that leaves a real word, are ticket 35.
- **How to judge:** on the labelled sample, since no checked reference text of a Thai scan exists. A rule may lose at most 1 misread for every 10 correct marks it removes.
- **Join, then judge whole words.** Pieces of a word that the segmenter cut are joined to their neighbours. If the joined stretch is accepted, none of it is marked. If not, the whole stretch is marked, not one piece of it.
- **Accept, on OCR text read with confidence:**
  - **a joined stretch of 5 Thai letters or more that is a Thai Wikipedia title,** from the list PyThaiNLP ships, under CC BY-SA 4.0, credited in the README's licence section;
  - **a single Thai letter in parentheses,** "(ก)";
  - **1 to 4 Thai consonants followed by a full stop,** "บพข.", "ส.", "ปร.ด.": a misread inside such an abbreviation, as "บพย." for "บพข.", goes unmarked;
  - **"ณ" with a space or the edge of the text on either side.**
- **Not done:**
  - **No names rule.** Names from the text layer lost misreads, and PyThaiNLP's names list added nothing beyond Wikipedia.
  - **The 0.85 confidence threshold stays.** Low-confidence boxes on correct text were 4 of the 46.
- **Measuring after the change:** the same 200 labelled marks and 40 checked ones, with the same scripts, kept with the samples under `docs/example_pdf/`, which is git-ignored. Fast tests cover each rule with the fake engine. `corpus/degraded` must keep marking every misread it marks now. A harness measure of marks on correct text waits for real Thai scans with reference text (tickets 16 and 17).

**2026-10-31, built**

**In `words.py`,** through the same `unknown_word_spans` that uncertain text calls.
- **Pieces joined into a title:** pieces join with up to 3 neighbours either side, and the join must be Thai letters only.
- **The rules for text written so on purpose** follow the plan.
- **Where an unknown piece is marked,** the syllables of one consonant right beside it are marked with it.
  - Many of the pieces a word is cut into are syllables the word list holds, such as "ลิ", "โน" and "สี". So joining only unknown pieces would still have marked a piece of the word.
  - A syllable of one consonant beside an unknown piece is taken as part of the same word, so "ลิกโนเซลลูโลสิก" is marked whole.
  - Common words of one consonant, such as "ที่", "จะ", "ได้" and "ผู้", stand apart. They come from PyThaiNLP's list of common words, which is CC0. None of the pieces seen, such as "ลิ" and "โน", is in it.
  - A syllable of two consonants also stands apart: "หก" in "ทุกหกเคือน" stays out, and so does "ภาพ", which leaves "กุณภาพ" marked as "กุณ".

**After code review:**
- **Common words stand apart.** At first every syllable of one consonant was pulled in, so "ที่อืนจะ" was marked whole. The older tests now expect "ผู้<mark>อืน</mark>" again, as before this ticket.
- **An abbreviation does not end a word.** "กข" in "ระบบกข." was taken for an abbreviation, as would a misread ending a sentence, such as "ธนาคร." for "ธนาคาร.".
  - At first this left marked two list letters that OCR had joined to the word before them, "ทั้งสิ้นข." and "โครงการข.", the only two in the file.
  - A single consonant before a full stop is now accepted after a word the word list holds. "ระบบกข." and "ธนาคร." stay marked.
- **Smaller fixes:**
  - the tokens are a small named type, so they are not confused with the OCR pieces in `uncertain.py`;
  - PyThaiNLP's own cache of the titles is used;
  - the README states the AGPLv3 section 13 step.

**Measured on the Thai contract:**

| Check | Before | After |
|---|---|---|
| Marks on the whole file | 1,395 | 1,169 |
| Marks set by an unknown Thai word alone | 996 | 770 |
| Labelled sample, correct text marked | 46 of 200 | 18: 28 unmarked |
| Labelled sample, misreads unmarked | | none |
| 40 checked marks the plan unmarks | | 38 unmarked; among them "บพย." for "บพข.", as expected, and the borderline "ทรอนิกส์" |

Two of the 40 checked marks stay marked: "กุณภาพ", and a "ณ" that OCR joined to the next word.

**Left for ticket 35,** which needs the same table of Thai letters that look alike:
- "บพย." for "บพข." goes unmarked;
- "กุณภาพ" is marked as "กุณ", not as the whole word.

From the sample, about 1 mark in 11 now falls on correct text, against nearly 1 in 4 before. The sample comes from this one file, and Claude labelled it.

**The corpus:**
- `corpus/synthetic` gives the same report as before, page by page.
- On `corpus/degraded` every page gives the same report as before, and the Thai page's marks are the same.

**Run:**
- pytest: 689 passed, 1 skipped; after the list-letter fix, 690;
- `pytest -m ocr`: 27 passed;
- mypy clean.

The scripts and labels are in `docs/example_pdf/reference/uncertain-marks/`; `check_labels.py` repeats the check on the labelled marks.
