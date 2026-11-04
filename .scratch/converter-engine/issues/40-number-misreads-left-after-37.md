# 40: Number misreads that ticket 37's rules cannot catch

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, a number misread as another number that still looks like a number reaches the output unmarked. Ticket 37 marks the ones a rule can see, such as a date that cannot be or comma groups of the wrong size. The rest are left: an amount with an extra digit, a day misread as another valid day, a range that lost its dash. In a contract these are amounts, dates and counts, so the reader and the AI are not warned.

**Blocked by:** 37

**Status:** needs-triage

**Split from:** ticket 37, on 2026-11-03, in triage. The user chose to keep this gap as a known limitation on the what's-new page for good: some misreads leave no trace any check can find, so readers must always check amounts and dates against the original. This ticket stands for that limitation.

**Signals left to try**
- **A total that does not add up,** or a 7% VAT that does not match its amount. This needs a pass over a whole table, and a way to tell which row is the total.
- **A number unlike its neighbours** in the same column, or a column empty where other rows hold numbers.
- **The engine's confidence per character,** if ticket 37's measurement shows it separates misread digits from correct ones.

**Known to be out of reach:** a misread that leaves a valid value, such as a day read as another day, and a dash lost from a range.

## Comments
