# 12: The "how it works" section

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A section of the home page explains a conversion with pictures, in plain Thai, for readers with no technical background. It shows what the converter actually does, so that a visitor understands why the output can be trusted, and where their file goes. The pictures are inline SVG and HTML, in the look from ticket 11.

**Blocked by:** 11

**Status:** ready-for-agent

**Branch:** `feat/web-design`

**What it shows**
- [ ] **The file is checked:** its type is read from its content, and the limits are applied.
- [ ] **Each page is read in one of two ways:** from the file's own text when there is any and it can be trusted, otherwise with OCR. OCR is needed for a scan, for text drawn as shapes, and for a page whose own text is wrong.
- [ ] **How wrong text is caught,** using the example "กำร" where the page shows "การ":
  - characters that cannot be read
  - sara am in the wrong place
  - fewer than 95% of the words found in the dictionary
- [ ] **The Thai repair:**
  - marks put back in order
  - sara am made one character
  - legacy-font characters mapped back
  - no spaces inside words
  - printed lines joined back into paragraphs
- [ ] **Structure and placeholders:**
  - headings, lists and tables kept
  - repeated headers and page numbers removed
  - signatures, stamps and images replaced by placeholders, never by invented text
- [ ] **One document model, two outputs,** with uncertain text marked in both.
- [ ] **Where the file goes:** encrypted all the way to our server, converted in a throwaway container with no network, and deleted after 10 minutes or on request.

**Rules**
- [ ] Every fact matches the converter as it is. The limits shown (50 MB, 150 pages, 10 minutes, 95%) come from the same settings the service and the converter use.
- [ ] Every example is synthetic, never taken from a real document.
- [ ] Each picture has a text alternative, and the section reads well at phone width.
- [ ] The converter spec's notes say that a change to any rule shown here updates this section in the same ticket.

**Tests**
- [ ] The limits shown on the page match the settings.
- [ ] The page loads no image from another site.

## Comments

**2026-10-22, from ticket 11**

The home page already has the start of this section, under "แปลงอย่างไร", in the layout the user approved:
- three numbered steps: drop or pick a file, wait, then copy or download
- the "กำร → การ" example, as one worked case of wrong text being caught

Build the full section from these, in the same look (`DESIGN.md`), rather than adding a second one beside them.
