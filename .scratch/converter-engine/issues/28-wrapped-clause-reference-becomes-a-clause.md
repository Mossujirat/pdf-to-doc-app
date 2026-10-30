# 28: A clause reference that wraps becomes a false clause

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On a text page, a clause ends a line with a cross-reference such as "ตามข้อ", and the clause number it refers to starts the next line. The converter takes that next line for a new numbered list item. The output then holds a second clause with the number of an earlier, real one, and the sentence it belonged to is cut in two. In a contract a reader, or an AI, takes it for a clause of its own.

**Blocked by:** none

**Status:** done

**Seen on:** a text page exported from Word in a 110-page Thai contract among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission. Text pages are otherwise the most faithful part of the output.

**To decide at triage**
- **Where it happens:** the rule that makes a row starting with its own number into a list item.
- **When a numbered row continues the sentence before it,** for example when:
  - the row before does not end a sentence;
  - the row before ends with a word that introduces a reference, such as "ข้อ", "ตามข้อ", "มาตรา" or "clause";
  - the row starts at the indent of the paragraph's wrapped lines, not where its items start.
- **A synthetic fixture:** a wrapped cross-reference in the corpus, with its reference text.

## Comments

**2026-10-30, triage**

- **In the next deploy:** the user chose this ticket among the 6 to be done before it. See `.scratch/next-deploy.md`.
- **Next:** `/grill-with-docs`, then `/implement`.

**2026-10-30, grilled**

- **Where it happens:** `layout._starts_new_item`.
  - A number starts an item after a line that stops short, or whenever the group so far is a list item, even after a full line.
  - Contracts are list items throughout, so a number wrapped onto a new line becomes a false item there. That covers both a clause reference and an amount ("2.5 ล้านบาท").
  - No test pins the list-item branch: with it removed, the whole suite still passes.
- **The user decided the rule,** checked in this order:
  1. **After a line that ends with a reference word, a number carries on the sentence,** even when that line stops short. A word that ends with one of these counts too, as "ตามข้อ" and "หัวข้อ" do.
     - Thai: ข้อ, ข้อที่, มาตรา, วรรค, หมวด, หมวดที่, ภาคผนวก, ตารางที่, รูปที่, and หน้า as a word of its own only, after a space. "ล่วงหน้า", "ข้างหน้า" and "หัวหน้า" are not references.
     - English: clause, section, article, paragraph, item, table, figure, annex, appendix, page, no.
  2. **After a line that stops short, a number starts an item,** as before.
  3. **After a full line, a number carries on the sentence,** inside a list item too. The one exception: in a list item with a hanging indent, whose wrapped lines start right of its number, a number that starts in line with the item's own number starts a new item.
- **"List item"** was added to `GLOSSARY.md`.
- **Tests:**
  - Fast tests through `convert`, one per case:
    - a reference at a line's end, the line full;
    - a reference at a line's end, the line short;
    - an amount wrapped inside an item;
    - a new item after a short line;
    - a new item after a full line, under a hanging indent;
    - "ล่วงหน้า" at a line's end, before a real item.
  - **Corpus:** a synthetic contract on a text page, numbered clauses holding a wrapped cross-reference and a wrapped amount, with its reference text.
  - Check by breaking each mechanism on purpose.
- **Samples:** the user allowed converting the three samples before and after the fix, on the terms of tickets 18, 21 and tables 09: this machine only, no sub-agent, counts only, outputs deleted after.

**2026-10-30, implemented**

- **Rule 3 was taken out, as the user chose on the samples' evidence.** Rule 3 said that after a full line a number carries on the sentence, in a list item too, unless it starts in line with the item's own number under a hanging indent.
  - On the 110-page contract it joined 6 real clauses, on 4 pages, onto the clause before them. Justified clauses often end on a full line, and none of those had a hanging indent.
  - That is why a number within an item started the next one. That branch had no test. Now `test_a_clause_whose_last_line_runs_full_is_followed_by_the_next_clause` pins it.
  - **What is left as a known limit:** an amount that wraps onto a new line within a clause, as "2.5 ล้านบาท", still becomes a false clause. The samples have none.
- **The rule now:** after a line that ends with a reference word, a number carries on the sentence (`layout._REFERENCE_AT_END`), when the line wrapped. Otherwise a number starts an item within an item, or after a line that stops short, as before.
  - **Wrapped** means the number's first word would not have fitted at the line's end. The spec review showed that a short heading ending in a reference word, such as "ภาคผนวก" or "รายละเอียดแยกตามหมวด", joined the list under it. "each item" did the same.
  - **A word after "ทุก" is no reference,** as in "ทุกข้อ", "ทุกมาตรา", "ทุกหมวด" and "ทุกวรรค": every one, which points at no number. A clause ending "…ตามสัญญานี้ทุกข้อ" swallowed the next clause.
  - The user chose both conditions after the review.
  - "หน้า" counts only when it does not end another Thai word, as the page counter's pattern already has it.
- **The harness can't see this:** it drops list markup and collapses spaces, so a false clause scores the same CER as the right sentence. `test_corpus.py` therefore compares the new document's page whole, list markers included.
- **Corpus:** `clause-references`, a text page with numbered clauses:
  - a cross-reference wrapped onto the next line;
  - a clause ending on a full line before the next;
  - a line ending in "ล่วงหน้า" before the next clause.
- **Tests,** `test_page_structure.py`:
  - a clause number wrapped after its reference, in Thai and in English, the line full;
  - a reference whose line stops short of the next word, which is wider;
  - a short heading that ends in a reference word, followed by its list;
  - "ทุกข้อ" and "ล่วงหน้า" at the end of a list item, followed by the next;
  - a list item ending on a full line, followed by the next.
- **Checked by breaking the code on purpose:**

  | Broken | Tests that fail |
  | --- | --- |
  | no reference rule | 3 |
  | a reference counts on any line, wrapped or not | 1 |
  | "ทุก" before the word counts | 1 |
  | within an item, a number starts one only after a short line | 4 |
  | "หน้า" ending another word counts | 1 |
  | no English reference words | 1 |

- **Code review (two axes):**
  - **Standards:**
    - "clause" was used for output blocks, where `GLOSSARY.md` says "list item". Fixed in test names and in `corpus/README.md`.
    - "List item" moved to the glossary's Conversion section. It now defines the term without claiming what the code does.
    - The width of a row's first word reuses `_first_word_width`, which tables ticket 02 wrote for cells.
    - Not done: sharing the page word with `_PAGE_COUNTER`. That pattern also takes "หน้าที่", which, after a word, can mean duty.
  - **Spec:** the false joins above, fixed.
- **Known limits:**
  - An amount wrapped within a clause becomes a false clause, as noted above.
  - "ตามข้อ / ๔.๒" in Thai digits joins as "ตามข้อ๔.๒". `thai.join_lines` puts no space between Thai characters, and Thai digits are Thai characters. That holds on every page, not only after a reference.
  - "No" without a full stop is no reference: as a word it is too common.
  - A reference word at the end of a line that wrapped, followed by a real clause whose number would not have fitted, joins that clause. That needs the line to run full and the clause to follow at once.

- **On the samples, against the code before (`ec117d3`):**
  - Only one page changed, on the contract: a clause's reference ("ตามข้อ / 17.1.3") no longer becomes a clause. Checked against the page image.
  - The supplement and the agreement are unchanged.
  - Times: 437 s, 196 s and 33 s, against 456 s, 208 s and 36 s before.
  - **After the review's fixes, again:** only the same page changed, the same way. Times: 452 s, 194 s and 31 s.
- **Run:**
  - **Windows:** pytest (652 passed, 1 skipped) and mypy.
  - **The harness:** before the review's fixes, `corpus/synthetic` and `corpus/degraded` gave the same report as `ec117d3`, page by page, the new document included. It cannot see list structure.
  - **The Linux image,** with the source mounted, as no dependency changed:
    - mypy;
    - pytest (653 passed);
    - `pytest -m ocr` (25 passed);
    - the harness, with text pages at CER 0 and the same OCR totals as before.
