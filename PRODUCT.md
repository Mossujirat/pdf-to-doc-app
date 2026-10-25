# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Thai office workers who receive contracts, official letters and forms as PDF, often through a chat app, or as DOCX. They want the text in an AI chat or in Word. They are not technical. They use a desktop at work or a phone. The documents are often confidential: names, ID numbers and addresses.

## Product Purpose

The web service of pdf-to-doc converts one PDF or DOCX into Markdown, to paste into an AI chat, and DOCX, to edit in Word. The Thai and English text reads exactly as it does in the original. It is free and needs no sign-up. Success is a visitor who gets text they can use without fixing it, and who knows where their file went.

## Positioning

The service makes two promises, with equal weight:

- **Thai text, exactly.**
  - No floating or missing vowels and tone marks, and no spaces inside words.
  - Printed lines are joined back into paragraphs.
  - A page whose own text is wrong (such as "กำร" where the page shows "การ") is caught and read with OCR.
  - What cannot be confirmed is marked as uncertain, never silently guessed.
- **The file is safe.**
  - It travels encrypted to our own server, with no third party on the path.
  - It is converted in a throwaway container with no network.
  - It is deleted 10 minutes after the conversion ends, or at once on request.
  - Nothing of it is logged.

## Operating Context

**A conversion:**
1. Choose whether scans are read with OCR, the default, or kept as images in the DOCX; then drop or pick a file, and an invisible bot check runs.
2. The page shows the file's place in the queue, then its progress, such as "OCR หน้า 23/85".
3. The result shows the summary, a button that copies the Markdown, and a DOCX download.
4. The visitor deletes the result, or lets it expire.

**While it runs:** a conversion with OCR pages takes minutes. Visitors switch tabs or lock the phone, and come back by the same link.

**Limits:**
- one file at a time per browser
- 50 MB and 150 pages per file
- 500 pages a day per client address
- results kept for 10 minutes

## Capabilities and Constraints

**Every page state is designed:**
- the home page with its upload area
- waiting, with the place in the queue
- converting, with progress
- the result, and deleted
- every refusal and failure, in the command line's Thai wording from one shared table (`src/pdf_to_doc/refusals.py`)
- the web's own messages:
  - queue full, and one file at a time
  - the bot check failed, and a request from another site
  - over the daily allowance, and timed out
  - expired, deleted or lost to a restart

**Stack and page rules:**
- Plain HTML, CSS and JavaScript with no build step, served by the FastAPI app in `src/pdf_to_doc/web/`. Pages are rendered in Python (`pages.py`), with one script (`static/app.js`).
- The Content-Security-Policy allows this site, and Cloudflare Turnstile's script and frame, and nothing else. There is no inline script or style.
- Fonts are served by the service, under a licence such as the OFL.
- No analytics, tracking or advertising.

**Readability:**
- Thai text at least 13 px, inputs at least 16 px
- WCAG AA contrast, touch targets at least 44 px
- works at phone width: the file picker and dropping both work, and the copy button works in mobile browsers

**Language:** Thai only for now. English comes later.

**How it works:** the home page explains what the converter does with a file, in six rows with pictures, under "ข้างในทำอะไรกับไฟล์ของคุณ" (ticket 12). Its facts are the converter's as it is.

**Privacy and source:** the privacy page (`/privacy`, ticket 13) names the operator and the contact, and says what becomes of a file, of an address and of the one cookie, what Cloudflare's bot check sees, and the visitor's rights under the PDPA. Every page's footer links to it, to the source at the commit the server runs (AGPL), and to GitHub Issues.

## Brand Commitments

- **Name:** ครบคำ, chosen by the user on 2026-10-21. It replaced เป๊ะ, the first choice that day. The repository keeps its own name, pdf-to-doc.
- **Thai type** is loopless (ตัวไม่มีหัว), at the user's explicit request.
- **Colours** are the service's own, never NSTDA's. Its primary colour is dark green, #0F6B55, chosen by the user on 2026-10-22.
- **Layout:** the plain, centred layout that people already know from online converters, with one big drop area. On 2026-10-22 the user chose this over a more distinctive look, with pdfguru's PDF to Word page as the reference.
- **It must not feel like** any of these:
  - a free converter full of ads, invented numbers or upsell
  - an old government website
  - a startup selling something
  - something too playful to trust with a contract

## Evidence on Hand

- **Synthetic documents** in `corpus/synthetic/` may serve as demonstrations, labelled as examples.
- **The real contracts** in `docs/example_pdf/` are confidential, and never appear in any design.
- **Nothing to invent:** there are no testimonials, user counts or benchmarks.
- **The operator** is Sujirat Attawibulkul, as an individual. Personal-data contact: sujirat.attawibulkul@gmail.com. The source is AGPL, on GitHub.

## Product Principles

1. **Text you can trust.** Show which pages were read with OCR and what is uncertain; never hide doubt.
2. **Privacy is part of how it works.** Where the file goes is shown plainly, not as small print.
3. **One task, no detours.** Drop a file, get the text.
4. **Plain Thai** for readers with no technical background.
5. **Nothing from elsewhere.** The page loads nothing from other sites but the bot check.

## Accessibility & Inclusion

- WCAG AA, Thai text at least 13 px, inputs at least 16 px, touch targets at least 44 px.
- Works at phone width.
- The conversion's status is announced as it changes (`aria-live`).
