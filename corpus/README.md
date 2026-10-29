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
- Write an **incomplete table** (see `GLOSSARY.md`) as its label, `[ตารางอาจไม่สมบูรณ์]`, on a line of its own, then its printed lines one by one. The label is not a placeholder: the table's text is transcribed. A table with no rules at all gets no label; write its rows one per line.
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
- **Cells**: on a page whose reference text holds tables, how many of their cells the output holds in the same place, out of all of them, such as `38/44`, and `cells_right` and `cells` in the JSON report; `-` on a page whose reference holds no table.
  - The comparison above ignores table structure, so a table flattened into paragraphs scores the same CER as one kept whole. This measure does not.
  - A cell is in place when the output's matching table has a cell at the same row and column, with merged cells spread over the positions they cover, holding the same text after NFC and with its spaces collapsed.
  - Each reference table is matched with the output table that shares most of its cells' text. A table the output lacks has none of its cells in place.
  - `<mark>` is dropped, and a `<br>` inside a cell counts as a space on both sides.
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
- `coarse-table` holds a ruled table whose cells hold several printed lines, as some budgets are drawn:
  - items stacked beside their amounts, which are sub-rows;
  - items beside one total, which keep their line breaks;
  - a wrapped description, which is one sentence.

  Text in a table cell wraps as Word wraps it: the first line fills the cell, and the next word would not fit after it.
- A page can draw its text as shapes, with no text layer, as some PDF printers write it: `text-drawn-as-shapes`. It holds the same clauses as the second page of `wrong-unicode-map`, with a line marked over its first and last words. Both are OCR pages that are not scans, which the converter renders from the PDF and softens before reading; read crisp, they lose their fifth line.
- A page can hold pictures, drawn from numbers: a photo, a signature in blue ink and a red stamp, the last two on a transparent ground. `placeholders` puts each on a signing page.
- A page can be stored landscape and turned upright by a page rotation, as some scanners save pages: `rotated-text-pages`, and `rotated-scans`, whose typed notes sit where their position on the stored page would fall over the scan's lines.
- A sideways page has its content printed on a landscape sheet set a quarter turn on the page, so a reader turns the page to read it: `sideways-scans` holds a price schedule turned each way.
- `two-column-scans` holds pages set in two columns of body text, read one column after the other: a Thai page and an English page of terms. Its third page is a cover sheet whose labels are set apart from their values, read row by row.
- `ruled-table-scans` holds ruled tables on scans, one a page, with text around each: a payment schedule with wrapped cells, a budget with merged cells, a table of dates two rows deep, and the coarse table of `coarse-table`. The rules are found in the scan's image, so each comes out as a table. `ruled-tables-wrong-unicode-map` and `ruled-tables-drawn-as-shapes` hold the same pages on OCR pages that are not scans, whose rules are found in the image rendered from the PDF.
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
