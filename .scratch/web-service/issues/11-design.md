# 11: Design: name, look and every page state

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** Working with the impeccable skill, the service gets its name and its look, recorded in the repo's first `DESIGN.md`. Every state a visitor can meet is then designed and built:
- the home page with its upload area
- waiting, with the place in the queue
- converting, with progress
- the result
- each refusal and failure message
- the expired page

All of it works at phone width.

The approach is Chatbot's: plain HTML, CSS and JavaScript with no build step, and its readability rules. The colours are the service's own, never NSTDA's. Fonts are served by the service itself.

**Needs the user:** the user chooses the name and the visual direction during this ticket.

**Blocked by:** 04, 05, 06

**Status:** done

**Branch:** `feat/web-design`

**Design**
- [x] The user has chosen a name and a direction, and `DESIGN.md` records them: tokens, type, components.
- [x] Every page state above is designed and built.
- [x] Readability:
  - Thai text at least 13 px, and inputs at least 16 px
  - WCAG AA contrast
  - touch targets at least 44 px
- At phone width, moved to ticket 14, to check on a real phone through staging:
  - the file picker and dropping both work
  - the copy button works in mobile browsers
- [x] Fonts are served by the service, under a licence such as the OFL. The page requests nothing from other sites except Turnstile.

**Checks**
- [x] The main states are checked in a real browser engine at phone and desktop widths, with screenshots in this ticket's comments, and the user tried the local server.
- The main flow on a real phone moved to ticket 14.

## Comments

**2026-10-22, built**

**Chosen by the user:**
- **Name:** ครบคำ, on 2026-10-21. It replaced เป๊ะ, the first choice that day.
- **Type:** loopless Thai (ตัวไม่มีหัว).
- **Look:** on 2026-10-22 the user dropped the first direction, a boarding pass in a departure hall, for a plain converter layout, with pdfguru's PDF to Word page as the reference:
  - a white page with a centred title
  - one big green drop area with a "+" circle
  - three numbered steps
- **Colour:** dark green, #0F6B55.

**What was built:**
- **Pages:**
  - Every page is rendered by `src/pdf_to_doc/web/pages.py`.
  - The styles are in `static/site.css`, and the one script is `static/app.js`.
  - Prompt 400, 500 and 600 are subset from google/fonts and served from `static/fonts/` under the OFL.
- **Home:** choosing or dropping a file sends it at once. Without the script, a "แปลงไฟล์" button shows instead.
- **Conversion page:** one card.
  - While the conversion waits or runs, the card shows its steps. The current step has a progress bar during OCR, and a step that changes is tinted for a moment.
  - The result shows the copy button, the downloads, and a table of how each page was read, with an amber "ตรวจ" tag on each page to check.
  - A conversion that ended with no result lists what became of the file.
- **The state JSON:** while a conversion waits or runs, it also carries the steps' HTML, as `steps`, for the page to update in place.
- **Records:**
  - `PRODUCT.md`
  - `DESIGN.md` and its sidecar, `.impeccable/design.json`
  - the surface brief in `.impeccable/surfaces/`

  The skill's working files, in `.impeccable/review/` and `.impeccable/questions/`, are git-ignored.
- **The home page's "แปลงอย่างไร":** three numbered steps and the "กำร → การ" example. These were part of the layout the user approved. Ticket 12 builds the full section from them.

**Review:**
- **The impeccable detector** flagged a pulsing dot on the current step, which is now still. Its "cramped padding" flags on the card and the pages table were false: the card's padding is a `clamp()`, and the table's cells have their own padding.
- **The finish review** passed contrast. Every text pair is 5.4:1 or more. It found five fixes, all made:
  - On a phone, the pages table no longer scrolls inside a box of its own, which hid the last pages, including pages to check.
  - "แปลงไฟล์อื่น" under a result is now a full-size button.
  - The wordmark is now at least 44 px tall.
  - The status is written only when it changes, so a screen reader announces it once.
  - A number no longer wraps away from its unit.

**Checked:**
- **Tests:** after the code review fixes, `uv run pytest` passed on Windows (415, 1 skipped) and in the Linux image (416). `uv run mypy` is clean.
- **Screenshots:** every state was rendered with synthetic data.
  - **Photographed:** home, waiting, OCR, finished, refused, not found and deleted, in headless Edge at 1440 px and, inside a 390 px frame, at phone width.
  - **Not photographed:** the other states use the same card and notice templates.
  - **Kept in `11-screenshots/`:**
    - `home-desktop.png`, `home-mobile.png`
    - `waiting-mobile.png`, `ocr-desktop.png`
    - `finished-desktop.png`, `finished-mobile.png`
    - `refused-mobile.png`, `not_found-desktop.png`
- **The user's approval:** the user approved the design on 2026-10-22, once `pdf-to-doc-web --dev` was running for them to try.
- **Not checked yet:** a phone cannot reach that local server. Picking, dropping and copying on a real phone move to ticket 14's smoke test on staging.

**2026-10-22, after code review**

**Fixed:**
- **A lit step lost its tint at the next poll,** about 2 seconds later, before its fade could start. The script now updates each step in place.
- **The count of pages to check included pages whose own text was wrong.** It now counts only pages with uncertain text, as the converter's summary does. Such a page still says, in its note, that it was read with OCR.
- **OCR showed as done for a file with no page that needed it.** A conversion now records whether any page was read with OCR, and its steps show OCR as skipped ("ไม่ต้องใช้").
- **Mixed-up deletion times:** the line under the drop area said the file is deleted within 10 minutes. It now says the source file is deleted as soon as its conversion ends, and the results within 10 minutes.
- **A cancel while waiting listed a sandbox thrown away,** though none had started. That fact now shows only for a conversion that started.
- **The no-result facts claimed no IP address was recorded,** but the daily allowance holds addresses in memory. They now say only that the logs hold no content, file name or link.
- **The limits line:** the drop area now shows the daily allowance beside the size and page limits.
- **Tidied:**
  - the unused queue chip is gone
  - CSS repeats now use tokens (`--ease`, `--on-brand`, `--gutter`)
  - `DESIGN.md`, `PRODUCT.md` and the sidecar now match the build

**New tests:** `tests/test_web_pages.py` covers the skipped OCR step and the cancel that never had a sandbox.

**Kept:** the step code still branches on the stage in `status()`, `steps()` and `_step_at()`. The review called this a judgement call.
