# 28: A clause reference that wraps becomes a false clause

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On a text page, a clause ends a line with a cross-reference such as "ตามข้อ", and the clause number it refers to starts the next line. The converter takes that next line for a new numbered list item. The output then holds a second clause with the number of an earlier, real one, and the sentence it belonged to is cut in two. In a contract a reader, or an AI, takes it for a clause of its own.

**Blocked by:** none

**Status:** ready-for-agent

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
