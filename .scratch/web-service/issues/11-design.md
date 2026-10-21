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

**Status:** ready-for-agent

**Branch:** `feat/web-design`

**Design**
- [ ] The user has chosen a name and a direction, and `DESIGN.md` records them: tokens, type, components.
- [ ] Every page state above is designed and built.
- [ ] Readability:
  - Thai text at least 13 px, and inputs at least 16 px
  - WCAG AA contrast
  - touch targets at least 44 px
- [ ] At phone width:
  - the file picker and dropping both work
  - the copy button works in mobile browsers
- [ ] Fonts are served by the service, under a licence such as the OFL. The page requests nothing from other sites except Turnstile.

**Checks**
- [ ] The main flow is checked in a real browser at phone and desktop widths, with screenshots in this ticket's comments.
