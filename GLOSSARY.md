# pdf-to-doc-app

Converts PDF and DOCX files into DOCX or Markdown whose Thai and English text reads exactly as it does in the original.

## Conversion

**Source file**:
The PDF or DOCX a user submits for conversion.
_Avoid_: input file

**Document model**:
The single structured representation of a source file's content (headings, paragraphs, lists, tables, images and page boundaries) that every output is produced from.
_Avoid_: intermediate format, AST

**List item**:
A block of the document model that starts with its own number, letter or bullet, such as a clause of a contract. A number that only carries on a sentence, such as an amount or the clause number a cross-reference points to, wrapped onto a new line, does not start one.
_Avoid_: clause (for the block), numbered paragraph

**Output**:
A DOCX or Markdown file produced from the document model.

**Conversion**:
One request to turn a source file into one or both outputs, from submission until nothing of it is held any more.
_Avoid_: job, task

**Accurate mode**:
A slower conversion setting that reads OCR pages with a more accurate engine. The default is the faster setting.
_Avoid_: high-quality mode, slow mode

**Kept images**:
A conversion setting, chosen once for the whole source file, under which the DOCX output shows each scan as an image of the whole page as it looks, highlights and notes included, and each picture as the picture itself, instead of OCR text or a placeholder. The Markdown output gets a placeholder in their place, followed by any trustworthy text the source file already holds on a scan, such as a typed note or the hidden text of a searchable scan. The default is to read scans with OCR.
_Avoid_: image mode, picture mode

## Quality

**Broken text**:
Any place where the output's text differs from what a reader sees in the original: missing, misplaced or substituted vowels and tone marks, spaces inside a word, a word split across lines, wrong reading order, or text that is missing altogether.
_Avoid_: garbled text, ตัวหนังสือขาด (when used loosely)

**Reading order**:
The order a reader takes a page's text in: from top to bottom, and where text is set in columns, each column to its end before the column to its right. A table, or a list of labels and their values, is read row by row.

**Uncertain text**:
Text in an output that the converter could not confirm reads correctly, such as an OCR word that is not in the dictionary, or text the OCR engine read with low confidence. It is always marked in the output and counted in the output's summary.
_Avoid_: low-quality text, error

**Placeholder**:
A short bracketed label that stands in for content the converter deliberately does not transcribe, such as an image, a signature or handwriting.
_Avoid_: tag, alt text

**Incomplete table**:
A table on an OCR page whose text the converter could not place in its cells with certainty, so the output gives it row by row, each printed line on its own, after a label saying the table may be incomplete. Its text is transcribed, so it is not a placeholder, and the summary counts it apart from them.
_Avoid_: broken table, partial table

**Reference text**:
The known-correct text of a test page, against which outputs are judged for broken text.
_Avoid_: ground truth, expected output

**Corpus**:
A set of source files, each with reference text for some or all of its pages, used to measure broken text.
_Avoid_: dataset, fixtures (when meaning the whole set)

## Pages

**Text layer**:
The machine-readable characters stored in a PDF page, separate from what the page draws.

**Text page**:
A page whose text layer matches what a reader sees, so its text can be taken from the layer.

**Page furniture**:
Headers, footers and page numbers that repeat across pages and are not part of the document's content, including an image repeated at the same edge, such as a logo or initials on every page. Outputs leave them out.
_Avoid_: running header (when meaning all of these)

**OCR page**:
A page whose text must be read from its image, because its body has no text layer (a scan, unless images are kept) or its text layer cannot be trusted. A page whose text layer cannot be trusted is read with OCR even when images are kept, unless it is a scan.
_Avoid_: scanned page (a page with an untrustworthy text layer is not a scan but is still an OCR page)

**Scan**:
A page whose body is a picture of a printed or written page, such as a page from a scanner or a phone photo of one. Notes, stamps or highlights may be laid over it, and a searchable scan has the text of the picture hidden behind it. A page whose text is drawn as shapes is not a scan.
_Avoid_: image page

**Kept page**:
A scan that the DOCX output shows as an image of the whole page, because images are kept, or any other page that would be read with OCR and shows nothing but pictures, such as a logo alone on a page. It is not read with OCR: the Markdown output gives a placeholder in its place, followed by any trustworthy text the source file holds on it.
_Avoid_: image page

**Sideways page**:
A page whose content is printed a quarter turn from the page, so a reader turns the page to read it, such as a wide table printed across a tall page. A page that the PDF itself turns upright when it is shown is not a sideways page.
_Avoid_: rotated page, landscape page

**Upside-down page**:
A page whose content is printed a half turn from the page, so a reader turns the page round to read it, such as a sheet fed into a scanner the wrong way round. A page that the PDF itself turns upright when it is shown is not an upside-down page, nor is an upright page with an upside-down stamp or line on it.
_Avoid_: rotated page, inverted page

**Column**:
Text set beside other text on a page, with a clear gap between them, which a reader reads to its end before the text beside it: one of the two columns of a terms-and-conditions page, a panel of addresses beside a letter, or one of several signature blocks side by side. A table's columns are not columns in this sense, nor are labels set apart from their values, as on a form: they are read row by row.
_Avoid_: text block, side-by-side text

**Picture**:
An image placed on a page among its text, such as a photo, a chart, a signature or a stamp. It becomes a placeholder unless images are kept.
_Avoid_: figure
