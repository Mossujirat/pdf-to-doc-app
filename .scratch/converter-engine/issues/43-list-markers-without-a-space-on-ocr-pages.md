# 43: List markers that OCR reads without a space are not list items

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, the engine often drops the space after a list marker. It reads "(1)" or "-" joined to the Thai word after it. The marker patterns, `_NUMBERED_ITEM` and `_BULLET_ITEM` in `layout.py`, require a space after the marker, so such a row is not a list item:
- Items in one list come out differently: some as list items, some as plain paragraphs.
- The wrapped line of an item that is missed becomes a paragraph of its own, cut from its item.

**Blocked by:** none

**Status:** done

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

### 2026-11-11: triage, decided with the user

**The fix:** where a row is built from the OCR engine's boxes, put back the space OCR dropped after a list marker. The row then reads "(1) คำ", like the items around it that OCR read with the space, and `layout.py` keeps its marker patterns and ticket 28's rules unchanged.
- **Markers:** "(n)", "n)", "(ก)" and "ก)", in Arabic or Thai digits, and the bullets of `_BULLET_ITEM` but "*", which also marks a note. Only at the start of a row, and only when a Thai letter follows at once.
- **Left out:** "n." and "n.n", which a decimal or a wrapped reference such as "4.2ของ" would match, and "*".
- **A dash joined to its word** starts an item always, as a dash with a space does. Word breaks a line after a joined hyphen, never before it, so a range such as "มกราคม-มีนาคม" does not put one at the start of a row.
- **Where:** rows the engine read, on the body and in incomplete tables. Text-layer rows on an OCR page, ruled tables' cells and text pages keep their text as it is.

**PaddleOCR on a synthetic scan,** Sarabun at 16 pt, whose space is 3.9 pt wide:
- With a full space, it kept the space after "(1)", "1)", "(ก)" and "-" on three seeds.
- With the marker 0 or 1 pt from the word, it joined every marker to its word, and the whole list became one paragraph.
- At 2 pt, some markers were joined and some were not. At 3 pt, none were.
- It also lost a "•" entirely, so its line ran on from the item above. That goes to ticket 45, with the contract's third dash.

**The fixture:** one scanned page in `corpus/synthetic` whose single list mixes markers set a full space from the word with markers set 1 pt from it, and one item that wraps onto a second line.

**To measure:** all four samples, converted once, with the rule tried offline on their rows. The 5 numbered sub-clauses and 2 dash items should become list items, with their wrapped lines in them. Every other row the rule changes is to be listed and checked.

### 2026-11-11: done

`with_marker_spaced` in `layout.py` puts the space back, and `ocr.py` calls it on the first box of each line the engine read.

**Changed in review,** with the user: "n)" and "ก)", with no opening bracket, are left out after all. A bracket that wraps onto the next row starts it the same way: "(ฉบับที่ / 2)ซึ่ง" or "(ภาคผนวก / ก)ซึ่ง". With the space put back, that row started a new item within a list item, or after a line that stops short. The joined markers are now "(n)", "(ก)" and the bullets. "1)" and "ก)" still start an item with a space after them, on every page, as before.

**Measured** on the four samples, converted once with the user's permission, with the rule tried on their rows:
- **The 10-page contract:** 7 rows changed: the 5 numbered sub-clauses on 3 pages, and the 2 dash items. All 7 are list items now. List items rose from 6 to 13, and paragraphs fell from 85 to 77: one item's wrapped line rejoined it.
- **The 110-page contract:** 24 rows changed, on 12 pages. All of them start with a list marker as printed: "(n)", a bullet "•" or a dash. List items rose from 278 to 301, and paragraphs fell from 853 to 833. The first rule, which also caught "n)", changed 27 rows: the other 3 were numbered "n)", and they stay as they were.
  - One row is OCR's garble of a printed line that starts with a dash. It is now an item of its own, where before it ran on from the row above, a number.
- **The other two samples:** no row changed.
- **On all four:**
  - Text pages are unchanged.
  - No row of an incomplete table changed.
  - Uncertain text is unchanged, but on the 110-page contract: the same 913 stretches, one character fewer. That character is the garbled row's dash, which is now its item's bullet.

**The fixture, `list-markers-scans`:** one scanned page with a numbered list and a dash list. In each, some markers are set a full space from the word and some 1 pt from it.
- With the rule switched off, PaddleOCR read the 4 tight markers joined to their words. The page came out with those items run into the line or item before them, at a CER of 0.020.
- With the rule, each block matches the reference, at a CER of 0.007. The one misread is a lost mai tho, which is marked uncertain.

**`corpus/synthetic`, through the harness:** the rule changed only the 4 tight rows of `list-markers-scans`. No other page's text changed. Text pages read at a CER of 0 with no broken text; OCR pages at 0.0091 in all.
