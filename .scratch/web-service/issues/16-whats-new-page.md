# 16: What's new page

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A page in plain Thai, มีอะไรใหม่, tells a visitor with no technical background what each recent **release** improved, and which **known limitations** they should still check for themselves. A visitor who had a poor result before learns whether to try again.

**Blocked by:** none

**Status:** done

**Branch:** `feat/whats-new`

**Decided:** 2026-11-02, by the user, in grilling. The terms are in `GLOSSARY.md`, under "Web service".

## The page

- [x] Route `/whats-new`, titled มีอะไรใหม่. It is a page to read: the same card as the privacy page (`.card.prose`), as DESIGN.md's "A page to read" describes.
- [x] Order:
  1. The `h1` and a Body large opening.
  2. **ข้อจำกัดที่ควรรู้:** one list of the known limitations as they are now. Each item says what goes wrong and what to do instead, where there is something to do. With no known limitation left, the section is left out.
  3. The latest 3 releases, newest first. Each is an `h2` with its date as the privacy page writes dates ("31 ตุลาคม 2569", in a `<time>`), then a list of what improved. The newest carries a plain chip, ล่าสุด.
  4. One primary button back to converting, แปลงไฟล์.
- [x] No amber anywhere on the page: amber is only for text to check against the original (DESIGN.md, the Amber Means Check Rule). The limitations are a plain section.
- [x] Every page's footer links to it, between ซอร์สโค้ด and แจ้งปัญหา. Nothing else links to it: no banner, no popup, no line on the home page.
- [x] Plain Thai for readers with no technical background: no PR numbers, ticket numbers, commit hashes, or words such as OCR or DOCX where a plain word serves (ไฟล์ Word, อ่านหน้าสแกน).

## The content

- [x] Held as Python data in a module of its own in `src/pdf_to_doc/web/`, not a Markdown file: type-checked, tested, and with no parser.
- [x] **Releases:**
  - **22 ตุลาคม 2569:** one item, เปิดให้ใช้งานครั้งแรก.
  - **31 ตุลาคม 2569:** what PRs #12–#18 improved. Start from the plain-language summary written on 2026-11-02: turned, sideways and upside-down scans, two columns, tables on scans, keeping scans as images, uncertain text that marks misread numbers and marks fewer correct Thai words, text under a diagonal watermark, and a wrapped clause number that no longer starts a false clause.
- [x] **Known limitations:** only what goes wrong without uncertain text or a placeholder to warn the reader. Each one stands for an open ticket:
  - converter-engine 20 and 36: highlights and notes are not carried into the text (with images kept, scans show them);
  - converter-engine 22: page numbers, headers and footers of scans are left in the text;
  - converter-engine 26: ticked boxes on scans are lost;
  - converter-engine 29: sideways text inside an upright page, such as a table's column headers, is lost;
  - converter-engine 32: signature blocks and side panels beside other text are read across;
  - converter-engine 34: diagonal text on scans is not read;
  - converter-engine 35: a Thai misread that happens to be a real word is not marked.

  Check each against its ticket before writing it; drop any that a release has fixed.
- [ ] **Wording:** Claude drafts every item from the tickets and PRs; the user approves the wording before staging.

## The rules for later releases

- A release gets an entry: a deploy that visitors can tell apart from the one before. A change to the server alone, or a hotfix visitors cannot see, does not.
- The entry's date is the day it goes to production. It is written before staging. If the deploy moves to another day, the date is corrected and staging runs again.
- The release that closes a ticket behind a known limitation drops the limitation and lists the fix among its improvements.
- A rollback is a revert on `main`, which takes the reverted release's entry off the page with it.

## The deploy

- [x] `scripts/deploy.sh`, deploying production: when the files the server uses differ from what production runs, but the what's-new content does not, it prints a warning and goes on. It never refuses, so a hotfix needs no entry.
- [x] `docs/DEPLOY.md`: writing the entry is a step before staging.

## Documents

- [x] DESIGN.md: the page under "A page to read", and the footer's four links.
- [x] PRODUCT.md: the footer links to the what's-new page too.

## Tests

- [x] The page shows the known limitations first, then the latest 3 releases, newest first, with the chip on the newest alone.
- [x] With no known limitation, the section is left out.
- [x] Releases are kept newest first, with no two on the same date.
- [x] Every page's footer links to `/whats-new`.
- [x] The deploy script has no tests. Check its warning by hand on pairs of commits: server files changed with the content unchanged warns; with the content changed, or no server file changed, it does not.

## Comments

**2026-11-02, implemented on `feat/whats-new`**

- **Known limitations, checked against each ticket:**
  - Left out: converter-engine 29 (sideways text inside an upright page). Its ticket says the junk it leaves is marked uncertain, so the reader is warned.
  - Added after review: converter-engine 24. Signatures, stamps and pictures inside scans come out as junk or vanish, with no placeholder, so the output of a signed contract never says it was signed.
  - Added: tables-on-ocr-pages 10 (row labels beside a ruled table): the labels are read apart from their rows, with nothing to say so.
  - Highlights (20 and 36) are one limitation.
- **The button** says กลับไปแปลงไฟล์, as the privacy page's does.
- **The ticket test** (`test_every_known_limitation_stands_for_open_tickets`) reads `.scratch/`, which the image leaves out, so it is skipped there and in CI. It runs on a developer's machine. Marking ticket 26 done made it fail, as it should.
- **The deploy warning:** `scripts/deploy.sh check` prints it too, so it can be tried without deploying. `check 864c68c 31d52d5` warns (server files changed, no releases file); `check 31d52d5 f56f38c` does not (no server file changed).
- **Seen at 1280 px and 520 px** in headless Edge. At 390 px headless Edge cuts the privacy page the same way, so it is the browser's smallest window, not this page.
- **The wording** of the 31 October release and of the limitations waits for the user's approval before staging.

**2026-11-02, code review**

- **The 31 October release overstated three fixes,** so its wording now says what the tickets measured:
  - tables: only tables ruled into cells become tables (tables spec);
  - uncertain text: numbers with letters among their digits, such as 12,ooo.oo; numbers misread as other numbers are still a known gap (ticket 23);
  - watermarks: text under them is lost less often, not never (ticket 25: 33 boxes gained, 3 lost).
- **Kept images** show highlights on scans only (ticket 20), and the item says so.
- **Watermarks in two places:** the limitation now says the watermark's own slanted text is not read, so it no longer reads as contradicting the release.
- **Still open, for the user:** numbers misread as other numbers (a lost or extra digit) are not marked, and no open ticket stands for them, so they are not a known limitation yet.
- **The wording box** stays unticked until the user approves the wording, before staging.
