# Test corpus

A **corpus** is a set of source files with **reference text**: the known-correct text of each page, which outputs are judged against for **broken text** (see `GLOSSARY.md`).

## Layout

```
<folder>/
  <name>.pdf
  <name>/
    page-001.reference.md
    page-002.reference.md
```

- Every source file sits beside a folder of the same name.
- That folder holds one reference file per page, numbered from 001.
- A page without a reference file is not scored.
- A source file without a reference folder is not converted.

The quality harness accepts any folder in this layout. Confidential documents can be measured from a local, git-ignored folder (for example under `docs/example_pdf/`) without entering the repo.

**Errors that stop an evaluation** (exit code 2):
- the folder does not exist
- no page has reference text
- a file ending in `.reference.md` is not named `page-NNN.reference.md`
- a reference file refers to a page the source file does not have

## Writing reference text

A reference file holds what a reader sees on the page, written as Markdown:

- Type the text exactly as printed. Keep Thai digits as Thai digits, and do not fix the original's typos.
- Write tables as HTML `<table>` elements, with `rowspan` and `colspan` where cells are merged.
- Replace content that is not transcribed with a placeholder:
  - `[รูปภาพ]` for an image
  - `[ลายเซ็น]` for a signature
  - `[ตราประทับ]` for a stamp
  - `[ลายมือ]` for handwriting
- Leave out headers, footers and page numbers that repeat on every page; the converter is meant to drop them.
- Line breaks and spacing between paragraphs do not matter.
- Saving with or without a byte order mark makes no difference.

## How pages are compared

Both the output page and its reference are reduced to visible text before comparison:
- HTML comments are removed.
- Inline tags such as `<mark>` (uncertain text) are removed without leaving a gap. Other tags, such as table cells, leave a space.
- HTML entities such as `&amp;` become the characters they stand for.
- Markdown heading, quote, table and `**`/`__` emphasis markup is removed.
- The text is put into Unicode NFC. NFKC is never applied: it would split sara am into two characters and hide that damage.
- Every run of whitespace becomes one space.

The harness then reports, per page and in total:

- **CER**: edits needed to turn the output into the reference, per reference character. The total is all edits over all reference characters. Output on a page whose reference is empty counts as error. CER is also computed over Thai characters only.
- **Broken text**, by kind. Each count is how much more the output has than the reference:
  - **orphan marks**: a Thai mark or sara am with no Thai letter before it
  - **spaces inside words**: a space the output puts between two Thai letters that the reference writes together. The letters are aligned without spaces, so a space that moved is found where it landed.
  - **PUA characters**: Private Use Area characters, from legacy Thai fonts
  - **decomposed sara am**: sara am stored as two characters, in either order
  - **missing text**: a run of 10 or more reference characters that the output lacks altogether. This does not depend on how the reference is wrapped into lines.
- **Page kind**: text page or OCR page.
- **OCR engine and uncertain-text count**: shown as `-` and 0 until OCR and uncertain-text marking exist.

## Commands

```sh
uv run pdf-to-doc-eval corpus/synthetic                       # print the table
uv run pdf-to-doc-eval corpus/synthetic --json report.json    # also write JSON
uv run pdf-to-doc-eval corpus/synthetic --max-broken 0 --max-cer 0   # exit 1 when exceeded
uv run python corpus/generate.py                              # regenerate corpus/synthetic
```

## Synthetic documents

`generate.py` describes each page twice:
- the lines to draw, which may carry damage such as sara am stored as two characters or letters set apart for justification
- the reference text a reader sees

It draws the PDFs with `pdf_builder.py`, using the fonts in `fonts/`.
- The same inputs always give the same bytes.
- A test fails when the committed files in `synthetic/` differ from what the generator makes.

The fonts are Sarabun and Niramit. Both are under the SIL Open Font License, and their licence files sit beside them.
