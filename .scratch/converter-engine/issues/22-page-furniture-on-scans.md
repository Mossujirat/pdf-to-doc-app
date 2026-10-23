# 22: Page furniture on scans is left in

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, headers, footers and page numbers stay in the output, although the spec says outputs leave page furniture out:
- The text in a letterhead logo comes out as broken fragments at the top of most pages, often marked uncertain.
- A footer line with its page number, and page numbers on their own, come out at the bottom of most pages.

They waste AI tokens and break the text between pages.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a 34-page scanned contract supplement among the local samples in `docs/example_pdf/`, converted on 2026-10-22 and 2026-10-23 with the user's permission. The file joins three documents, and each one numbers its pages from 1.

**A 110-page Thai contract** among the same samples has scans pasted into Word pages. It was converted on 2026-10-23 with the user's permission.
- **What works:** the Word page's header and footer, laid over each scan as text, were dropped on every page, as the spec intends.
- **What stays:** the scans' own form footers and page numbers stayed on most scan pages, as lines of the body. Examples are a form's name with its revision and page number, and an "x/7" count.

**What is known so far:** `remove_page_furniture` in `layout.py` matches rows by their exact text at the same edge. OCR reads the same letterhead a little differently on each page. One acronym in it came out three different ways, with a capital I read as "l" or "!", so the rows never match. Why lone page numbers stay has not been looked into.

**To decide at triage**
- **Check again after ticket 19.** Every page of this sample is rotated, and the edge bands depend on positions on the page.
- How OCR rows can match while their text differs slightly, for example by similarity rather than equality, and only within the edge bands.
- Whether page numbers need their own rule on OCR pages, where a misread digit breaks the "same distance from the PDF page number" test.
