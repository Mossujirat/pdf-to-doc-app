# 12: The "how it works" section

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A section of the home page explains a conversion with pictures, in plain Thai, for readers with no technical background. It shows what the converter actually does, so that a visitor understands why the output can be trusted, and where their file goes. The pictures are inline SVG and HTML, in the look from ticket 11.

**Blocked by:** 11

**Status:** done

**Branch:** `feat/web-design`

**What it shows**
- [x] **The file is checked:** its type is read from its content, and the limits are applied.
- [x] **Each page is read in one of two ways:** from the file's own text when there is any and it can be trusted, otherwise with OCR. OCR is needed for a scan, for text drawn as shapes, and for a page whose own text is wrong.
- [x] **How wrong text is caught,** using the example "กำร" where the page shows "การ":
  - characters that cannot be read
  - sara am in the wrong place
  - fewer than 95% of the words found in the dictionary
- [x] **The Thai repair:**
  - marks put back in order
  - sara am made one character
  - legacy-font characters mapped back
  - no spaces inside words
  - printed lines joined back into paragraphs
- [x] **Structure and placeholders:**
  - headings, lists and tables kept
  - repeated headers and page numbers removed
  - signatures, stamps and images replaced by placeholders, never by invented text
- [x] **One document model, two outputs,** with uncertain text marked in both.
- [x] **Where the file goes:** encrypted all the way to our server, converted in a throwaway container with no network, and deleted after 10 minutes or on request.

**Rules**
- [x] Every fact matches the converter as it is. The limits shown (50 MB, 150 pages, 10 minutes, 95%) come from the same settings the service and the converter use.
- [x] Every example is synthetic, never taken from a real document.
- [x] Each picture has a text alternative, and the section reads well at phone width.
- [x] The converter spec's notes say that a change to any rule shown here updates this section in the same ticket.

**Tests**
- [x] The limits shown on the page match the settings.
- [x] The page loads no image from another site.

## Comments

**2026-10-22, from ticket 11**

The home page already has the start of this section, under "แปลงอย่างไร", in the layout the user approved:
- three numbered steps: drop or pick a file, wait, then copy or download
- the "กำร → การ" example, as one worked case of wrong text being caught

Build the full section from these, in the same look (`DESIGN.md`), rather than adding a second one beside them.

**2026-10-22, built**

**The section:**
- "แปลงอย่างไร" keeps its three steps, now side by side.
- A new part, "ข้างในทำอะไรกับไฟล์ของคุณ" (`_inside()` in `pages.py`), follows it: six rows, each with plain Thai beside a picture.
- **This departs from the note above:** a second part was added, rather than growing the first. Six topics each need a picture, and one column of steps could not hold them. The three steps therefore moved side by side, and the "กำร → การ" example moved into row 3. The user is shown this before the commit.
- The pictures are drawn in HTML and CSS, with the page's own type and no image files: miniature pages, word boxes, a document card and a route.
- **The rows:**
  1. **The file is checked:** the file's type is read from its content, and its limits are applied.
  2. **Each page is read one of two ways:** from its own text or with OCR, with a picture of three pages.
  3. **Wrong text is caught:** the three checks, with the "กำร → การ" example from ticket 11 moved here.
  4. **The Thai repair:** a made-up example shows a space before mai ek removed, and two printed lines joined with no space between them.
  5. **Structure is kept, and nothing unreadable is guessed:** a picture shows a page number cut, a heading and a list kept, and placeholder chips.
  6. **Where the file goes,** as a route of four stops.

**Checked against the converter's code:**
- **The dictionary check:** it applies only to a page with at least 20 Thai words (`validation.py`). The page says so, so that the 95% is not overstated.
- **The sara am check** does not catch "กำร": sara am there follows a consonant. "กำร" is caught by the dictionary check, and the page says it that way.
- **OCR pages:** they give no headings and no tables (`model.py`, `ocr.py`), and the page says so.
- **Placeholders:** they come from images inside the file. Nothing yet makes a handwriting placeholder or a placeholder for an incomplete table, so the page names only images, signatures and stamps. On a scan, what OCR cannot read clearly is marked uncertain instead (`uncertain.py`).
- **Deletion:** the source file is deleted when its conversion ends, and the results within 10 minutes, or at once on request (converter spec). The route says both.
- **Refusals:** the file check names the ones the web gives: legacy Word, locked by password, and copying forbidden.

**Code:**
- **Shared thresholds:** `validation.py`'s two thresholds are now public, as `MIN_DICTIONARY_SHARE` and `MIN_WORDS_TO_JUDGE`. The page reads them, with `MAX_BYTES`, `MAX_PAGES` and the setting for how long results are kept.
- **The converter spec's notes:** they now say that a change to a rule shown here changes the section in the same ticket.
- **Tests:** `tests/test_web_home.py` checks two things:
  - **The limits:** the section shows numbers built from the constants (`MAX_BYTES`, `MAX_PAGES`, `MIN_DICTIONARY_SHARE`, `MIN_WORDS_TO_JUDGE`) and from settings the test changes (how long results are kept, pages per day). It looks only inside the section.
  - **Nothing from elsewhere:** the page and its stylesheet load nothing from another site but Turnstile's script, and use no image file.

**Checked:**
- **Screenshots:** the home page was rendered and photographed in headless Edge at 1440 px and at 390 px. The first shots showed two problems, both fixed:
  - the before box of the repair picture wrapped its two printed lines into four
  - the Markdown sample broke across lines

  Both pictures now stack vertically.
- **The impeccable detector:** it found nothing.

**2026-10-22, after code review**

**Six sentences said more than the converter does. They now match the code:**
- **The "กำร" example:** the note said most of the page's words fail the dictionary. Broken pages still score 0.78 to 0.91, so the note now says fewer than 95% of the words are found.
- **Placeholders:** they come only on pages read from the file's own text. OCR pages get none (`ocr_page()`; converter spec: "OCR pages are images themselves and get none"), and the page now says so.
- **Spaces:** a space is removed only before an above or below vowel, a tone mark or sara am. It is not removed from every place inside a word, so the claim "จึงไม่มีช่องว่างกลางคำ" is gone from this section.
- **The repair heading:** it promised that no character is deleted, while invisible characters are. It now says that no visible character is deleted.
- **Tables:** they are kept from DOCX files, and from PDFs only where the table has ruled lines (`_ruled_tables()`).
- **The outputs example:** it marked a number as uncertain. OCR marks uncertain text mainly through Thai words outside the word list, so the example now marks a Thai word.

**Also changed:**
- **Removed:** the sentence that Cloudflare's check never sees the file. Its script runs inside the page, so the claim was too broad. The privacy page (ticket 13) will word it with care.
- **Tidied:**
  - DESIGN.md and the sidecar now match the CSS: the route's dotted line, the amber and red rules, the scan colours, the Subsection type and the corner scale
  - the repeated CSS for the boxes inside a picture is merged
  - the ticked list and the miniature pages are helpers (`_ticked()`, `_sheet()`)
- **Tests:** the limits test now builds its numbers from the constants and looks only inside the section. The pictures test checks that no `<img>` is used.

**Kept:** results can outlive "ภายใน 10 นาที" by up to the 15 seconds between sweeps for expired results. The wording is ticket 05's, used everywhere on the site, and was left as it is.
