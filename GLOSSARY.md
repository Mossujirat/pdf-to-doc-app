# pdf-to-doc-app

Converts PDF and DOCX files into DOCX or Markdown whose Thai and English text reads exactly as it does in the original.

## Conversion

**Source file**:
The PDF or DOCX a user submits for conversion.
_Avoid_: input file

**Document model**:
The single structured representation of a source file's content (headings, paragraphs, lists, tables, images and page boundaries) that every output is produced from.
_Avoid_: intermediate format, AST

**Output**:
A DOCX or Markdown file produced from the document model.

**Conversion**:
One request to turn a source file into an output, from submission until the output is downloaded or discarded.
_Avoid_: job, task

**Accurate mode**:
A slower conversion setting that reads OCR pages with a more accurate engine. The default is the faster setting.
_Avoid_: high-quality mode, slow mode

## Quality

**Broken text**:
Any place where the output's text differs from what a reader sees in the original: missing, misplaced or substituted vowels and tone marks, spaces inside a word, a word split across lines, wrong reading order, or text that is missing altogether.
_Avoid_: garbled text, ตัวหนังสือขาด (when used loosely)

**Uncertain text**:
Text in an output that the converter could not confirm reads correctly, such as a low-confidence OCR result. It is always marked in the output and counted in the output's summary.
_Avoid_: low-quality text, error

**Placeholder**:
A short bracketed label that stands in for content the converter deliberately does not transcribe, such as an image, a signature or handwriting.
_Avoid_: tag, alt text

**Reference text**:
The known-correct text of a test page, against which outputs are judged for broken text.
_Avoid_: ground truth, expected output

## Pages

**Text layer**:
The machine-readable characters stored in a PDF page, separate from what the page draws.

**Text page**:
A page whose text layer matches what a reader sees, so its text can be taken from the layer.

**OCR page**:
A page whose text must be read from its image, because its body has no text layer (a scan) or its text layer cannot be trusted.
_Avoid_: scanned page (a page with an untrustworthy text layer is not a scan but is still an OCR page)
