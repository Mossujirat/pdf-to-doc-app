# 03: Clean text-page structure

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Markdown from a text-page PDF keeps the document's structure and drops page furniture. Headings come out as headings with the right level. Numbered and bulleted lists come out as lists. Page headers, footers and page numbers that repeat across pages are removed.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/text-pages`

**Headers and footers**
- [x] Lines repeated in the same position across pages are removed. This includes a confidentiality stamp line and "หน้าที่ x/y" counters that restart in each appendix.
- [x] Removed counters are never used as page numbers. Page markers always use the PDF's own page index.
- [x] Text that appears on only one page is never removed, even near the page edge.

**Headings and lists**
- [x] Headings are detected from font size and weight relative to body text, and rendered with matching Markdown levels.
- [x] Thai and Arabic-numbered clauses and bulleted items are rendered as Markdown lists. Thai digits stay Thai digits.

**Tests**
- [x] Synthetic fixtures cover a stamped header, a page counter that restarts, two heading levels, and a numbered list. They are added to the corpus, and the harness shows zero broken text on them.

## Comments

**2026-10-17, findings from ticket 01 on the real contract**

- **List items merge into one paragraph.** PyMuPDF puts lines such as "ภาคผนวก 1 … จำนวน 7 หน้า" / "ภาคผนวก 2 …" in a single block, and joining its lines makes one paragraph. List detection must split lines inside a block, not only between blocks.
- **PyMuPDF blocks are not paragraphs.** Some sentences are split across blocks, for example "(Bio-Circular-Green" / "Economy: BCG)" and the centred title lines on page 1. Paragraphs need their own grouping from line spacing, indentation and alignment, beyond PyMuPDF's blocks.

**2026-10-19, implementation notes**

- **PyMuPDF's blocks are no longer used.** Paragraphs are grouped row by row (`layout.py`). A row starts a new paragraph when:
  - the font size changes
  - the vertical gap exceeds half a line
  - it is indented by more than one character, except between two centred lines
  - it starts a list item
  - it or the previous row is set out in columns

  The thresholds were checked on the real contract's geometry, looking only at positions, sizes and masked text: body text 16 pt, first-line indent of about 36 pt, about 8.6 pt between paragraphs, under 1 pt between lines.
- **Lines on one baseline become one row.** PyMuPDF splits a printed line at tab stops. Such lines are rejoined into one row, and a gap of more than two characters marks the row as set in columns. This keeps the "ภาคผนวก …" rows apart. A cell whose text wraps onto a second line still splits that row (ticket 04).
- **Page furniture.**
  - It must contain a letter or a digit. A dashes-only table cell low on two pages is content.
  - Page counters ("หน้าที่ x/y", "หน้า x จาก y", "Page x of y", "- 7 -") are blanked before rows are compared, so restarting counters match.
- **Headings.**
  - Larger sizes give levels 1, 2, …
  - A single bold row standing alone is the next level down, unless it is set out in columns (a table header).
  - Bold rows inside paragraphs are common in the contract, so a change to bold does not split a paragraph.
- **Lists.**
  - Numbered items keep their own marker ("- 1.", "- ๓.", "- (4)", "- 17.1.1"), because Markdown would renumber an ordered list and change the visible text.
  - Bullets are replaced by `- `.
- **Real contract, 110 pages, compared locally.**
  - The stamp and the "หน้าที่ x/y" footer were removed on all 110 pages.
  - No other text changed.
  - 30 headings, 34 list items.
  - Before the column rule, the bold cells of the budget table (pp. 69–72) made 92 headings.

**2026-10-19, changes after code review**

- **Page furniture no longer deletes real text.**
  - A page counter must end its row, and "หน้า" must not end another Thai word, as in "ล่วงหน้า 30 วัน".
  - A printed page number repeats only if it stays the same distance from the PDF page number. "500" and "1200" low on two pages are kept, while "1" and "2" on pages 2–3 are removed.
  - Rows must sit at the same edge, top with top and bottom with bottom.
  - A row counts as near the edge when it touches the band.
  - A row that is only a counter ("หน้าที่ ๑/๑") is removed even on a single page.
- **Lists.**
  - A numbered row starts an item only inside a list, or after a line that stops short of the text column's right edge. That edge is estimated as the page width minus the left margin. After a full line, "2.5 ล้านบาท" or "09.00 น." is a wrapped sentence.
  - "ก." is no longer a marker, because it is how Thai abbreviates ตำบล and อำเภอ. Only "(ก)" and "ก)" count.
  - Hanging indents continue an item.
  - A row set out in columns is never a list item.
- **Headings.**
  - A heading must be at least 6% larger than the body text.
  - Sizes within 0.6 pt share a level.
  - A heading is at most two rows, so a larger-type paragraph is not a heading.
  - A bold heading may wrap onto two rows.
- **Paragraph gaps.** A gap counts as a paragraph break when it exceeds the document's median line gap by 0.4 em. The median is capped at 0.75 em, so short documents still split on paragraph spacing. As a result, double-spaced text splits into one paragraph per line.
- **Known limits, left as they are.**
  - With no vertical gap between them, these are joined to the next text:
    - a centred title
    - a right-aligned date
    - a paragraph after a list

    The rule that would separate them breaks the contract's multi-line centred title, which mixes centred and near-full-width lines.
  - A bold heading followed directly by body text is joined to it. Bold does not split paragraphs, because the contract has whole bold lines inside paragraphs.
  - Multi-column body text drawn row by row interleaves. Multi-column layout is an open question in the spec.
- **Real contract, rerun locally and compared with the ticket 01 output.**
  - All 220 furniture rows were removed.
  - Apart from those rows, 0 letters changed.
  - 38 headings.
  - 84 list items, including items 1.1–1.7 and 5.1–5.21 that used to be merged into paragraphs.
