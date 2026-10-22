---
name: ครบคำ
description: A plain, centred PDF and DOCX converter that gives back Thai text exactly as printed.
colors:
  brand: "#0f6b55"
  brand-hover: "#0b5747"
  brand-tint: "#e6f2ee"
  brand-line: "#8fc4b4"
  ink: "#14201c"
  muted: "#4e5d58"
  line: "#dce4e1"
  soft: "#f4f7f6"
  page: "#ffffff"
  warn-bg: "#fef3c7"
  warn-ink: "#7c4405"
  danger: "#a8231a"
typography:
  display:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "clamp(1.875rem, 4.4vw, 3rem)"
    fontWeight: 600
    lineHeight: 1.3
  headline:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "clamp(1.625rem, 3.6vw, 2.25rem)"
    fontWeight: 600
    lineHeight: 1.35
  headline-section:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 3vw, 2.125rem)"
    fontWeight: 600
    lineHeight: 1.35
  wordmark:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 600
    lineHeight: 1.3
  title-drop:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 600
    lineHeight: 1.4
  title:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.5
  body-large:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.7
  body:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.7
  label-small:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.6
    fontFeature: "tnum"
  button:
    fontFamily: "Prompt, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 500
    lineHeight: 1.3
rounded:
  focus: "4px"
  button: "0.75rem"
  word: "0.875rem"
  panel: "1rem"
  surface: "1.25rem"
  frame: "1.75rem"
  pill: "999px"
  circle: "50%"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "0.75rem"
  base: "1rem"
  lg: "1.5rem"
  xl: "1.75rem"
  gutter: "clamp(1rem, 3vw, 2rem)"
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.page}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "0.625rem 1.5rem"
    height: "3rem"
  button-primary-hover:
    backgroundColor: "{colors.brand-hover}"
    textColor: "{colors.page}"
  button-secondary:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "0.625rem 1.5rem"
    height: "3rem"
  button-danger:
    backgroundColor: "{colors.page}"
    textColor: "{colors.danger}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "0.625rem 1.5rem"
    height: "3rem"
  drop-area:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.page}"
    typography: "{typography.title-drop}"
    rounded: "{rounded.surface}"
    padding: "2rem 1.5rem"
    height: "clamp(15rem, 34vw, 19rem)"
  drop-area-hover:
    backgroundColor: "{colors.brand-hover}"
  card:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "clamp(1.25rem, 4vw, 2.25rem)"
    width: "44rem"
  chip:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.muted}"
    typography: "{typography.label-small}"
    rounded: "{rounded.pill}"
    padding: "0.25rem 0.75rem"
  chip-warn:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn-ink}"
  example-panel:
    backgroundColor: "{colors.soft}"
    rounded: "{rounded.surface}"
    padding: "clamp(1.25rem, 3vw, 2rem)"
  facts-panel:
    backgroundColor: "{colors.soft}"
    rounded: "{rounded.panel}"
    padding: "1rem 1.25rem"
---

# Design System: ครบคำ

## Overview

**Creative North Star: "The Familiar Converter"**

ครบคำ looks the way people already expect an online converter to look, so nothing stands between the file and the text. A white page, a slim top bar with the green wordmark, a centred title, and one big dark green drop area. Every other page (a conversion's progress, its result, every refusal and notice) is a single white card in the middle. The user chose this layout on 2026-10-22, over a more distinctive direction, with pdfguru's PDF to Word page as the reference for its simplicity; it takes that simplicity and leaves out what such sites add: no ads, no invented numbers, no testimonials, no upsell.

The tone is calm and trustworthy enough for a confidential contract: flat surfaces, one green, generous Thai line height, and plain Thai words beside every icon. The name ครบคำ was chosen by the user on 2026-10-21; the dark green #0F6B55 on 2026-10-22.

Everything is served by the site itself. The Content-Security-Policy forbids inline script and inline style and anything from other sites except Cloudflare Turnstile. So all styling lives in one stylesheet (`src/pdf_to_doc/web/static/site.css`, no build step), the one script is `static/app.js`, the fonts are self-hosted, and icons are inline SVG written in `pages.py`.

**Key Characteristics:**
- One plain, centred task per page; home is title, drop area, privacy line, then how it works.
- One dark green for the drop area, the one primary button and steps done; amber only for pages to check.
- Prompt, loopless Thai, in three weights (400, 500, 600) for everything.
- Flat: borders and pale fills, not shadows.
- Readable by rule: Thai text at least 13 px, inputs at least 16 px, WCAG AA, touch targets at least 44 px, works at phone width.

## Colors

One dark green on white, a pale green tint for "now", amber only for "check this", and a deep red only for deleting.

### Primary
- **Contract Green** (brand, #0f6b55): the drop area, the one primary button per page, the marks of steps done, the wordmark, links, focus rings, the icons beside the privacy line and facts. White on it is 6.45:1; it is 6.45:1 on white, 5.99:1 on Soft Mist and 5.62:1 on Pale Leaf.
- **Deep Contract Green** (brand-hover, #0b5747): hover for the drop area, primary buttons and links. White on it is 8.51:1.
- **Pale Leaf** (brand-tint, #e6f2ee): the current step's mark, a just-changed step's brief tint, the progress track, the how-it-works numbers, text selection. Ink on it is 14.6:1.
- **Sage Line** (brand-line, #8fc4b4): the dashed frame around the drop area and the dotted line joining the how-it-works steps. Decorative only (1.96:1 on white); never text.

### Secondary
- **Check Amber** (warn-bg #fef3c7 with warn-ink #7c4405): only the "ควรตรวจ" and "ตรวจ" chips for pages with uncertain text, as the converter's summary names them. A page whose own text was wrong, and so was read with OCR, says so in its note without the chip. 7.02:1.
- **Delete Red** (danger, #a8231a): the delete button's text and hover border, and the crossed-out wrong word in the example. 7.19:1 on white, 6.67:1 on Soft Mist.

### Neutral
- **Ink** (#14201c): all body text and headings. 16.76:1 on white, 15.55:1 on Soft Mist.
- **Muted Slate** (muted, #4e5d58): subtitles, notes, step details, chips, table headers. 6.93:1 on white, 6.43:1 on Soft Mist.
- **Hairline** (line, #dce4e1): card, table, steps and secondary button borders, the top bar's rule. Structural, not text (1.29:1).
- **Soft Mist** (soft, #f4f7f6): the example panel, the facts panel, the sticky table header, plain chips.
- **Paper** (page, #ffffff): the page and every card. `color-scheme: light`; there is no dark theme.
- Notes on the drop area use white at 88% opacity: 5.39:1 on Contract Green, 7.01:1 on hover.

### Named Rules
**The One Green Rule.** Contract Green fills only the drop area, the single primary button on a page, and the marks of a conversion's progress: finished steps, the current step's dot and the progress bar. Every other green is a line, an icon or text.

**The Amber Means Check Rule.** Amber appears only where a page of the result should be checked against the original. It never decorates, warns about limits or marks errors of the service.

## Typography

**Display Font:** Prompt (with system-ui, sans-serif)
**Body Font:** Prompt (with system-ui, sans-serif)

**Character:** Prompt is a loopless (ตัวไม่มีหัว) Thai face, chosen at the user's request; one family in three weights reads modern and clear without feeling playful.

Fonts are self-hosted woff2 subsets in `static/fonts/` (Regular 400, Medium 500, SemiBold 600; Regular and SemiBold are preloaded), under the OFL (`Prompt-OFL.txt`). They were subset from google/fonts at commit 45e3d5269e4a17d823f6d84470bc084dc5ae46f6 with `uvx --from fonttools==4.60.1 --with brotli==1.1.0 pyftsubset`, flavor woff2, unicodes `U+0020-007E,U+00A0-00FF,U+0E00-0E7F,U+2010-2027,U+2030-2044,U+2190-2193,U+2212`. A new character outside these ranges falls back to the system font: re-subset the same way rather than adding another font.

### Hierarchy
- **Display** (600, clamp(1.875rem, 4.4vw, 3rem), 1.3, balanced wrap): the home page's title only.
- **Headline** (600, clamp(1.625rem, 3.6vw, 2.25rem), 1.35): a card's status or notice heading, the page's `h1`.
- **Section headline** (600, clamp(1.5rem, 3vw, 2.125rem), 1.35): the "แปลงอย่างไร" heading on home.
- **Wordmark** (600, 1.625rem, 1.3, Contract Green): ครบคำ in the top bar.
- **Drop title** (600, 1.375rem, 1.4): the call in the drop area.
- **Title** (600, 1.125rem, 1.5): how-it-works step titles, card section titles.
- **Body large** (400, 1.125rem): a notice's or refusal's message.
- **Body** (400, 1.0625rem / 17 px, line height 1.7): everything else. The tall line height leaves room for Thai marks above and below.
- **Label** (400, 0.9375rem / 15 px): notes, the top bar line, step details, the privacy line, the pages table.
- **Small label** (500, 0.875rem / 14 px, tabular numbers): chips. The small line over each example word is the same size at 400. This is the smallest size; nothing goes under 13 px.
- **Button** (500, 1.0625rem, 1.3).

### Named Rules
**The Three Weights Rule.** Only 400, 500 and 600 exist. 600 for headings and titles, 500 for buttons, chips, step labels and table row headers, 400 for reading. No italics, no letter-spacing, no uppercase.

**The Tabular Numbers Rule.** Anything that counts (chips, step details, the pages table) uses tabular numbers so "หน้า 23/85" does not jitter as it updates.

## Layout

- **Container:** the top bar and `main` share a 72rem maximum, with side padding of the gutter (clamp(1rem, 3vw, 2rem)). `main` has clamp(2rem, 6vw, 4.5rem) above and clamp(3rem, 7vw, 5rem) below. The body is a column so short pages still push to full height.
- **Home:** the hero and the upload form are centred columns of 46rem. The drop area sits clamp(1.75rem, 4vw, 2.75rem) under the hero; the privacy line 1rem under it. "How it works" starts clamp(4rem, 9vw, 6.5rem) lower, as a two-column grid (steps left, example right, gap clamp(2rem, 5vw, 4rem)) under a centred heading.
- **Every other page:** one card, 44rem wide, centred, its contents a column with a 1.5rem gap.
- **Rhythm:** gaps step through 0.25, 0.5, 0.75, 1, 1.5 and 1.75rem; inner padding uses 0.625 to 1rem. Responsive spacing uses `clamp()` rather than breakpoints.
- **Phone width (at or below 47.5rem):** the top bar's line hides, leaving the wordmark; "how it works" becomes one column; the privacy line aligns left; a step's detail drops under its label; the pages table loses its scroll box, so every page shows. Long file names wrap anywhere. A number stays on its unit's line (`&nbsp;` in "50&nbsp;MB", "150&nbsp;หน้า").

## Elevation & Depth

Flat. Depth comes from Hairline borders and Soft Mist fills, never from shadows. The single exception is the white "+" circle in the drop area, which carries a soft lift (`0 8px 20px -10px rgba(8, 40, 32, 0.55)`) so it reads as something to press; it belongs to that circle alone.

### Named Rules
**The Border Not Shadow Rule.** Cards, tables, steps and buttons separate from the page with a 1px Hairline border. Do not add shadows to new surfaces.

## Shapes

Soft, generous rounding that grows with the size of the surface: 0.75rem buttons, 0.875rem example word boxes, 1rem panels (steps list, pages table, facts), 1.25rem surfaces (card, drop area, example), 1.75rem for the dashed frame around the drop area (whose 0.75rem padding keeps the two curves concentric). Chips and the progress bar are full pills; the "+" circle, step marks and how-it-works numbers are circles. The focus ring takes a 4px radius. Lines are solid 1px Hairline, except the 2px dashed drop frame and the 2px dotted line joining the how-it-works steps, both in Sage Line.

## Components

### Top bar
- A 1px Hairline rule under it, contents in the 72rem container, padding 1rem by the gutter.
- The wordmark ครบคำ links home (Contract Green, darker on hover, no underline, at least 44 px tall); beside it, on the baseline, one muted line of what the service does. Nothing to sign in to, no menu.

### Hero
- Centred title (Display) and subtitle (Muted Slate, clamp(1.0625rem, 1.8vw, 1.25rem), balanced wrap), 1rem apart.

### Drop area
- The whole area is the file input's label: a transparent input covers it, so tapping anywhere opens the picker, and dropping a file anywhere on the form sends it. With the script, choosing or dropping sends at once; without it, a full-width primary "แปลงไฟล์" button appears (noscript).
- Contract Green, 1.25rem corners, min-height clamp(15rem, 34vw, 19rem), content centred: a 4.75rem white circle with a green "+" icon, the drop title, then a note with the formats and limits. A dashed Sage Line frame surrounds it.
- Hover and drag-over: Deep Contract Green, and the circle grows to 1.06 scale. Keyboard focus: a 3px Ink outline 4px out (a green ring would vanish against the green).
- While sending, the title becomes "กำลังส่งไฟล์" and the file name shows under the note.
- The bot check's widget is invisible and sits in the form, which is why the form is not a flex column.

### Assurance line
- Directly under the drop area: a lock icon in Contract Green and one muted Label line saying where the file goes and when it is deleted. Centred on desktop, left-aligned on phones. Privacy is shown here, at reading size, not as small print.

### How-it-works steps and example
- Three numbered steps: a 2.5rem Pale Leaf circle with the number in Contract Green (CSS counter), a Title and a muted paragraph; a 2px dotted Sage Line joins each number to the next.
- The example is a Soft Mist panel: a muted caption, then two word boxes with an arrow between them: the wrong word "กำร" in Delete Red, struck through, and the right word "การ" in Contract Green with a green border, then a muted note. Words are 600, clamp(1.75rem, 3.4vw, 2.25rem). Examples are labelled as examples and use synthetic text, never the real contracts.

### Card
- Paper, 1px Hairline border, 1.25rem corners, padding clamp(1.25rem, 4vw, 2.25rem), 44rem wide, centred. Holds every state of a conversion and every notice.
- Head: the file icon in Contract Green and the file name in Muted Slate on the left, chips on the right, wrapping on narrow screens.
- Then the status as the page's `h1` (Headline), which is live (`aria-live="polite"`) and is also the tab's title. While the conversion waits or runs, the page asks for it every 2 seconds and writes it only when it changed, so a screen reader announces each change once.
- A notice card is heading, message (Body large) and one primary button that says where to go.

### Chips
- Pills of Small label text: Soft Mist on Muted Slate for counts ("6 หน้า"); Check Amber for pages to check. A waiting conversion's place in the queue is a step's detail, not a chip. Inside the pages table they tighten to 0 0.625rem padding.

### Steps list with progress
- A bordered list (1rem corners), rows split by Hairline, each row a 1.75rem mark, the label (500) and a right-aligned muted detail ("ลำดับที่ 2", "หน้า 23/85").
- Marks: done is a filled Contract Green circle with a white tick; now is a Pale Leaf circle with a green border and a green dot; later is an empty Hairline circle, its label muted. OCR, for a file with no page that needs it, is skipped: an empty circle, a muted label and the detail "ไม่ต้องใช้", never a tick. Each label carries a visually hidden state word for screen readers.
- During OCR a progress bar runs under the label: 0.5rem pill, Pale Leaf track, Contract Green fill.
- A step whose state just changed is lit Pale Leaf, holds for 4 seconds, then fades over 1.8 seconds. While the tab is hidden the fade pauses, so the change is still visible on return. The script updates each step in place rather than rebuilding the list, so a poll does not cut the fade short.

### Pages table
- Inside a bordered, 1rem-cornered wrapper that scrolls past 28rem on wider screens (a focusable, labelled region, so a keyboard can scroll it), with a sticky Soft Mist header in muted 500 text. Label size, tabular numbers, 0.625rem by 1rem cells, Hairline between rows, none after the last.
- Columns: page (row header, 500), how it was read, what to check. A page to check starts its note with an amber "ตรวจ" chip; nothing to check is a muted dash.

### Facts list
- For a conversion that ended with no result: a Soft Mist panel (1rem corners, 1rem by 1.25rem padding) of plain sentences, each led by a green tick icon, saying what became of the file.

### Buttons
- **Shape:** 0.75rem corners, at least 3rem (48 px) tall, padding 0.625rem 1.5rem, Button type, icon and text 0.5rem apart.
- **Primary:** Contract Green with white text; hover Deep Contract Green. One per page: upload fallback, "คัดลอก Markdown", or a notice's way out.
- **Secondary:** Paper with a Hairline border and Ink text; hover turns the border Contract Green. Downloads, cancel, and "แปลงไฟล์อื่น" under a result.
- **Danger:** Paper with a Hairline border and Delete Red text; hover turns the border red. Only "ลบเดี๋ยวนี้".
- **Focus:** every focusable element gets a 3px Contract Green outline, 3px out.
- The copy button fetches the Markdown as the result loads, so the click can write to the clipboard straight away; its label changes to "คัดลอกแล้ว", or says to use the download if the browser refuses.

### Actions
- A wrapping row with a 0.75rem gap. On a result, a grid: the primary copy button across the full width, the downloads side by side under it (each at least 13rem, so they stack on phones).
- The end of a result is split off by a Hairline rule: the muted clock line with minutes left on the left, the delete button on the right.

### Motion
- One easing for everything: `cubic-bezier(0.16, 1, 0.3, 1)`, a quick ease-out. Buttons change colour in 160ms, the drop area in 180ms, the "+" circle scales in 220ms; the lit step settles over 1800ms after a 4s hold.
- Nothing moves on load and nothing loops. With `prefers-reduced-motion: reduce`, all transitions and animations are switched off.

## Do's and Don'ts

### Do:
- **Do** keep every style in `site.css` and every icon as inline SVG in `pages.py` (24-unit viewBox, round caps and joins, `currentColor`, `aria-hidden`), always beside words that say the same thing.
- **Do** use the tokens on `:root`; a new colour must reach WCAG AA (4.5:1 for text) against the surface it sits on, and its ratio belongs in this file.
- **Do** keep Thai text at 0.875rem (14 px) or above, never under 13 px; inputs at 1rem (16 px) or above; every button and tap target at least 44 px tall (buttons are 48 px).
- **Do** check every new page or state at phone width: picking a file, dropping one and the copy button must all work there.
- **Do** put a new page in one centred card with a status heading and one primary way forward.
- **Do** show doubt plainly: pages read with OCR, uncertain text and pages to check are always visible, in amber.

### Don't:
- **Don't** add inline `style` or `<script>`, icon fonts, or fonts, scripts, images or anything else from another site; the Content-Security-Policy blocks them and only Cloudflare Turnstile is allowed.
- **Don't** add ads, invented numbers, user counts, reviews, testimonials or upsell; there are none to show.
- **Don't** use a second filled green button on a page, or fill other surfaces with Contract Green.
- **Don't** use amber for anything but a page to check, or red for anything but deleting and the example's wrong word.
- **Don't** add shadows (beyond the drop area's "+" circle), gradients or a dark theme; the page is flat and light.
- **Don't** add a fourth font weight or a second typeface.
- **Don't** put the real contracts from `docs/example_pdf/` in any design, screenshot or example; use the synthetic corpus, labelled as an example.
- **Don't** make it feel like an ad-filled free converter, an old government website, a startup selling something, or something too playful to trust with a contract.
