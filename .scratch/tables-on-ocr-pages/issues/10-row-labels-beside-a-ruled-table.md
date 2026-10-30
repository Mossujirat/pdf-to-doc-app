# 10: Row labels beside a ruled table

**Parent:** Tables on OCR pages spec, in this feature folder.

**Status:** needs-triage

**Found by:** ticket 09, the final check on the real samples.

**What is wrong:** Budget sheets made in a spreadsheet often rule only the cells of their numbers. Each row's label, such as an item's name, lies on the same printed line, but to the left of the rules. Only the ruled part becomes a table. The labels are read as lines of their own, before or after it. A reader must match each label to its row by counting.

Before tables on OCR pages, each such row came out as one line, its label and its numbers together.

No text is lost, and every cell of the ruled part holds the right number.

**On the samples:** three pages of the 110-page contract, the budget pages whose text layer cannot be trusted. Between them they hold 15 ruled blocks (5, 3 and 7). On the first page, checked against its image, all 5 have their row labels set apart; the other two pages are laid out alike.

**To decide:**
- Whether a ruled table takes the text level with its rows just beside it as a first column, with no rule of its own.
- Or whether a ruled table with such labels comes out as an incomplete table, each printed line whole.
- How to tell row labels from a paragraph that runs beside a table.

## Comments
