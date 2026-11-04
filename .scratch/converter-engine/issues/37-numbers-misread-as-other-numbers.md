# 37: Numbers misread as other numbers are not marked

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, a number misread as another number reaches the output without being marked as uncertain text, because its shape does not show the misread. Seen on a 110-page Thai contract among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission (ticket 23):
- an extra digit in a tax amount;
- a footnote marker joined onto the number before it, which gained a digit;
- a year that lost its last digit;
- a day in Thai digits read as Arabic digits of another value;
- a page count "x/y" read as one number;
- a range that lost its dash;
- a count dropped from five of seven table rows.

In a contract these are amounts, dates and counts, where one digit changes the meaning. The reader and the AI are not warned.

**Blocked by:** none

**Status:** done

**Why it is a ticket of its own:** ticket 23 marked numbers with letters among their digits, such as "12,ooo.oo", and left these as the spec's known gap: "Numbers misread as other numbers". Grilling the what's-new page on 2026-11-02 found that no open ticket stood for them, so they could not be a known limitation. The user chose to open this one, so that the page names the gap (`.scratch/web-service/issues/16-whats-new-page.md`). The release that closes it rewords the limitation, which stays for ticket 40 (triage, 2026-11-03).

**To decide at triage**
- Which signals could catch them without marking every correct number: the engine's confidence per character, a total that does not add up, a date that cannot be, a number unlike its neighbours in the same column.
- Whether a number that cannot be checked should be marked at all, or only counted in the summary.

## Comments

**2026-11-03, triage**

- **In this round,** with 24, 26 and 32.
- **Scope:**
  - **Rules,** as ticket 23 added in `misreads.py`: a date that cannot be (a year of three digits after พ.ศ., ค.ศ. or ปี, or in a date; a day over 31), and comma groups that are not three digits, such as "1,2345". A number is marked only when a rule finds it wrong; numbers that cannot be checked are not marked.
  - **A measurement of per-character confidence.** PaddleX works out a score per character and keeps only their mean (its text-recognition decoder). Patch it on this machine only, run the 110-page contract, and see whether misread digits score lower than correct ones. Record the result here; whether to use it is decided then, in ticket 40.
- **Left for ticket 40:** totals that do not add up, numbers unlike their column, and per-character confidence if the measurement favours it.
- **The known limitation stays for good,** pointing to ticket 40 once this one closes: some misreads leave no trace, so readers must always check amounts and dates. The release that closes this ticket lists the rules and rewords the limitation to fit what is left.
- **Estimate:** small for the rules. The measurement is a spike of a day or so.

**2026-11-04, built**

**The rules,** in `misreads.py`, beside ticket 23's misread shapes. Only the wrong number is marked, never changed:
- **Commas out of place:** a group of four digits or more after a comma, or, in an amount (with decimals or another group of three), a group of one or two, or a first group of four or more. "1,2" alone may list two clauses and is left.
- **A year of three digits, or of five or more,** after พ.ศ., ค.ศ. or ปีงบประมาณ, after a day and its month, or after "March 15,".
- **A day its month does not have,** before a full Thai or English month or an abbreviated Thai one: 0, over 31, 31 in a 30-day month, over 29 in February.
- **A month is part of a date only after a day of one or two digits.** Abbreviated months also name agencies (ก.พ.), and a budget sheet sets amounts after full ones ("งวดมกราคม 500"). So "มีนาคม 256" with no day is left.
- **Not built:** a date whose day and year mix Thai and Arabic digits. An existing test holds such a date to be written so on purpose.
- **Narrower than triage: no year after a bare "ปี".** Triage named "after พ.ศ., ค.ศ. or ปี", but "ปี" is followed by numbers that are not years, as in "ระยะเวลา 1 ปี 180 วัน". Only "ปีงบประมาณ" counts.

**Checked:**
- **The corpus's reference text,** every `*.reference.md` file: no line has a number the rules would mark.
- **The 110-page Thai contract,** converted on this machine with the user's standing permission. The rules add 5 marks, and each is a misread, checked against the page image: "5,00.000" for 5,000.00; "39 พฤษภาคม" for ๓๑; "254" for 2542, the year that lost its last digit in this ticket's list; "255ว" for ๒๕๖๖; "๒๕๖" before a marked "ต", which now marks the whole year.

**The measurement of per-character confidence.** `docs/example_pdf/reference/number-misreads/` (git-ignored, beside the sample) holds the script that patches PaddleX's decoder to keep each character's score, the boxes it recorded, and contact sheets of low-scoring digits. On the contract's 6,045 boxes and 11,853 digits:

| Score below | Digits | Of them in a box already below 0.85 |
| --- | --- | --- |
| 0.3 | 91 (0.8%) | |
| 0.5 | 288 (2.4%) | 228 |

The 60 digits below 0.5 in confident boxes, labelled against the page images:
- **About 12 misread a value:** cells of a sideways table read as junk, bullets read as 0 or ๑, "39" for ๓๑, "255ว", "๑๕๖" for ๑๔๖, ID-card numbers under a watermark.
- **About 9 are misreads ticket 23's rules already mark,** such as Thai zero for o in "bamb๐๐".
- **About 39 are correct:** amounts such as 235,400.00 and 50,000.00, the contract number C04F690076 (on most pages), years.
- **Below 0.3, all 4 are misreads,** two of them caught by the date rules. Marks that no rule already gives: 2 below 0.3, 3 below 0.35, 9 below 0.4 (some correct), 50 below 0.5.
- **The misreads the rules caught scored:** the 9 of "39" 0.22, the second 5 of "255ว" 0.23, the zeros of "5,00.000" 0.56–0.99, and "254" 0.95 on its last digit, since a lost digit has no score.

**Result:** the signal is real but narrow on this document. Below about 0.3 it is precise and adds 2 marks, both on text that is junk anyway; any threshold that catches more marks correct amounts. Whether to use it is ticket 40's to decide.

**The known limitation stays,** now pointing to ticket 40 alone, reworded to fit what is left. The release that deploys this lists the rules.

**2026-11-04, after code review**

**Fixed:**
- **A number before an agency abbreviated like a month was marked as a day,** as in "ข้อ 31 ก.พ.ร." or "หนังสือที่ 45 ก.พ. กำหนด". An abbreviated month now counts only with a year after it, as "31 ธ.ค. 67".
- **"วันที่ 1 เดือนเมษายน 256"** was missed: the word เดือน may now stand between the day and the month.
- **The date rules are named predicates,** like the file's other rules.
- **`docs/DEPLOY.md` and the glossary** said a release that closes a ticket drops its known limitation. They now say a limitation that another open ticket still stands for is reworded instead, as this one is.
- **The draft release line** says no more than the rules do: a year in a date, and commas that do not part an amount in threes.

**Left, recorded:**
- **A number before a full month that is not a day,** such as "Section 31 June", is marked. Rare.
- **Not caught:** dates written with slashes ("15/3/256"), English abbreviated months, and two-digit groups with no decimals ("12,50 บาท"), which "1,2" listing clauses shares.

**Checked after the fixes:** the same 5 marks on the contract and none on the corpus's reference text. pytest: 708 passed, 1 skipped. `pytest -m ocr`: 27 passed, run before the review's fixes, which touch only the date rules the fake-engine tests cover. mypy clean.
