# 20: Highlights and notes on text pages are lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** People mark up PDFs before passing them on. They highlight passages, draw over them, or add a typed or sticky note, for example in Acrobat on a file exported from Word. On a text page these marks are annotations, and the converter drops them in both outputs. The reader of the output never learns which passages someone marked.

**Blocked by:** none

**Status:** needs-triage

**Why it is a ticket of its own:** grilling the kept-images feature on 2026-10-22 found it. Kept images show highlights and notes on scans, because the whole page becomes an image. On text pages, the text stays text, so kept images cannot help. The user put this out of that feature's scope.

**To decide at triage**
- Which annotations count: highlights, drawn ink, typed notes, sticky notes.
- How a highlight shows:
  - In DOCX, yellow already marks uncertain text, so a highlight needs another colour, or a Word comment.
  - In Markdown, it needs a marking that AI chats read, and that differs from `<mark>`.
- Where a note's text goes, in reading order or at the end of its page.

## Comments

**2026-10-30, triage**

- **After the next deploy:** the user chose to leave it for a later version. See `.scratch/next-deploy.md`.
- Status stays `needs-triage` until then.
