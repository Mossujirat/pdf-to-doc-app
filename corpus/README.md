# Test corpus

A **corpus** is a set of source files with **reference text**: the known-correct text of each page, which outputs are judged against for **broken text** (see `GLOSSARY.md`).

## Layout

```
<folder>/
  <name>.pdf          (or <name>.docx)
  <name>/
    page-001.reference.md
    page-002.reference.md
```

- Every source file, a PDF or a DOCX, sits beside a folder of the same name.
- A DOCX's pages are those Word laid out when it last saved the file.
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
- Headings may be written with `#` and list items with `- `, keeping each item's own number (`- 1. …`, `- (ก) …`). This markup is ignored when pages are compared, so plain text works too.
- Write tables as GFM pipe tables, or as HTML `<table>` elements. HTML is required where cells are merged, using `rowspan` and `colspan`.
- Replace content that is not transcribed with a placeholder:
  - `[รูปภาพ]` for an image
  - `[ลายเซ็น]` for a signature
  - `[ตราประทับ]` for a stamp
  - `[ลายมือ]` for handwriting
  - `[ตารางอาจไม่สมบูรณ์]` beside a table whose structure may be incomplete
- Leave out page furniture: headers, footers and page numbers that repeat at the same edge on two or more pages, and rows that are only a page counter. The converter drops them.
- Line breaks and spacing between paragraphs do not matter.
- Saving with or without a byte order mark makes no difference.

## How pages are compared

Both the output page and its reference are reduced to visible text before comparison:
- HTML comments are removed.
- Inline tags such as `<mark>` (uncertain text) are removed without leaving a gap. Other tags, such as table cells, leave a space.
- HTML entities such as `&amp;` become the characters they stand for.
- Markdown heading, quote, list bullet, table and `**`/`__` emphasis markup is removed.
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
- **OCR engine**: the engine that read an OCR page, `-` for a text page.
- **Uncertain text**: how many stretches the output marks as uncertain text, as its summary counts them.
- **Unmarked**: the share of edits that fall outside uncertain text, where a reader is not told to check. An edit counts as marked when the output character it changes or deletes is inside a `<mark>`, or, for text the output lacks, when a marked character stands next to the gap. The JSON report also gives each page's `unmarked_edits` and `marked_characters`, which show how much correct text is marked too.

Totals are given for all pages, and separately for text pages and for OCR pages. `--max-cer` and `--max-broken` apply to text pages only: the quality gate is zero broken text on text pages. OCR pages are measured, and their gate comes with the OCR baseline.

## Commands

```sh
uv run pdf-to-doc-eval corpus/synthetic                       # print the table
uv run pdf-to-doc-eval corpus/synthetic --json report.json    # also write JSON
uv run pdf-to-doc-eval corpus/synthetic --max-broken 0 --max-cer 0   # exit 1 when text pages exceed it
uv run python corpus/generate.py                              # regenerate corpus/synthetic
```

## Synthetic documents

`generate.py` describes each page twice:
- the lines to draw, which may carry damage such as sara am stored as two characters or letters set apart for justification
- the reference text a reader sees

It draws the PDFs with `pdf_builder.py`, using the fonts in `fonts/`.
- A scanned page is drawn, rendered as a grey image at 200 dpi, turned 0.4° and given mild grain, then saved as a JPEG inside the PDF. A header can be stamped over it as text, as PDF tools do.
- A document can have its fonts' ToUnicode maps rewritten, so the page looks right but its text layer says something else: `legacy-font` reports shifted marks as Private Use Area characters, as legacy Windows Thai fonts do, and `wrong-unicode-map` reports sara aa as sara am, so "การ" reads "กำร".
- A page can hold pictures, drawn from numbers: a photo, a signature in blue ink and a red stamp, the last two on a transparent ground. `placeholders` puts each on a signing page.
- The same inputs always give the same bytes.
- A test fails when the committed files in `synthetic/` or `degraded/` differ from what the generator makes.

## Damaged scans

`degraded/` holds one document, `damaged-scans`. Its five pages are the same twelve contract lines, scanned at rising damage: from the corpus's own 200 dpi with mild grain down to 75 dpi with heavy grain and 1.8° of skew. Each line is a paragraph of its own.

OCR is expected to get these pages wrong, so they sit outside the quality gate and outside CI. They are there to measure uncertain-text marking with the harness:

```sh
uv run pdf-to-doc-eval corpus/degraded
```

The **unmarked** column shows how much of what OCR got wrong was left unmarked. The JSON report's `marked_characters` shows how much was marked in all, including correct text.

The fonts are Sarabun and Niramit. Both are under the SIL Open Font License, and their licence files sit beside them.
