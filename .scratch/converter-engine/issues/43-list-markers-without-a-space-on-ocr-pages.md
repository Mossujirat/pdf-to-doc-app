# 43: List markers that OCR reads without a space are not list items

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, the engine often drops the space after a list marker. It reads "(1)" or "-" joined to the Thai word after it. The marker patterns, `_NUMBERED_ITEM` and `_BULLET_ITEM` in `layout.py`, require a space after the marker, so such a row is not a list item:
- Items in one list come out differently: some as list items, some as plain paragraphs.
- The wrapped line of an item that is missed becomes a paragraph of its own, cut from its item.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** the 10-page scanned contract of ticket 42, converted on 2026-11-10 with the user's permission.
- **5 numbered sub-clauses** were missed, on 3 pages, each read as "(n)" joined to its first word. Their neighbours, read with a space, became list items.
- **2 dash items** were missed, read as "-" joined to the word.
- **A third dash** was lost entirely. A rule on the marker cannot bring that one back.
- **A clause number read as "ข้อ n." joined to its text** is not list syntax either way, so this ticket does not change it.

**To decide at triage**
- **Where the rule applies:** OCR pages only, and only at the start of a row: "(n)", "n)" or a dash followed at once by a Thai letter.
  - On text pages, the text layer holds the real space, so they keep today's rule.
- **What it must not catch:** a row that starts with a dash used as a hyphen, or a number in brackets that continues a sentence. Ticket 28's rules still decide whether a marker starts a new item or continues the sentence before it.
- **A synthetic fixture:** a scan of a numbered list whose markers OCR reads without a space. Check that PaddleOCR really drops the space on it.

## Comments
