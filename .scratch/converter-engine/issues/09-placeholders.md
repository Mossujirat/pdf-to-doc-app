# 09: Placeholders

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** Content the converter deliberately does not transcribe shows up as a short Thai placeholder, both in Markdown and in DOCX. The reader then knows something was there, and nothing is invented. This covers images, signatures and stamps. The document model gains a placeholder block with a kind.

**Blocked by:** 07

**Status:** done

**Branch:** `feat/docx`

**Placeholder kinds**
- [x] Image objects on text pages become `[รูปภาพ]` placeholders at their position in reading order.
- [x] Where an image can be identified as a signature or a stamp, it becomes `[ลายเซ็น]` or `[ตราประทับ]`. For example: a small image next to signature-line text, or a round coloured mark.
- [x] When the kind is unclear, use the generic image placeholder rather than guessing.
- [x] The placeholder kinds the spec defines for later tickets (handwriting, incomplete table) exist in the document model and both renderers.

**Rendering and summary**
- [x] Placeholders appear in both Markdown and DOCX outputs.
- [x] The summary counts placeholders by kind.

**Tests**
- [x] Synthetic fixtures with an embedded image and a signature-line image cover placeholder output in both formats.

## Comments

**2026-10-20, implementation notes**

- **Choices made with the user:**
  - The incomplete-table placeholder reads `[ตารางอาจไม่สมบูรณ์]`. Handwriting reads `[ลายมือ]`, as `corpus/README.md` already said.
  - When there are placeholders, the summary ends with "ส่วนที่ไม่ได้ถอดเป็นข้อความ: รูปภาพ 1 จุด, ลายเซ็น 2 จุด, ตราประทับ 1 จุด", naming only the kinds found. Without placeholders the summary is as before.
  - Images of the same size in about the same place at an edge of two or more pages are page furniture and get no placeholder, like repeated headers and footers. "About the same place" was added after code review, at the user's choice; see below.
  - An image inside a table cell gets its placeholder right after the table. A cell holds only text in the document model.
- **The document model** gains `Placeholder` with a kind: image, signature, stamp, handwriting or incomplete table. Its `text` is the label in square brackets, so both renderers write it like any paragraph. The labels live in one `match` that ends in `assert_never`, so mypy fails if a kind lacks one. That is how the two later kinds are covered: nothing makes them through the conversion function yet, and the spec allows no other seam to test at.
- **Where placeholders come from** (`pdf_images.py`, read from the same text-layer pass as the text):
  - Each image on a text page, at its box. Images are placed in reading order the way tables are: before the first text that starts below them. OCR pages are images themselves and get none.
  - Left out: images whose shorter side is under 8 pt (rules, bullets, ornaments); images that are not stamps and have three or more rows of text printed over them (a scan made searchable, a watermark); and repeated edge images: the same size within 20% each way, and centres within 36 pt each way. Initials at the foot of every page of the short sample contract moved up to 21 pt.
- **Which kind** (judged on numbers from the two sample contracts, printing no document text):
  - **Stamp**, checked first and wherever it is pressed, a ring in colour:
    - the box is nearly square (sides 0.75 to 1.33 to each other);
    - the ink is well coloured (mean saturation 0.4 or more);
    - the corners outside the round hold at most 0.25 of the round's ink density;
    - the round's outer band (from 0.8 of the radius) holds its ink at least 1.5 times as densely as the inside, where a stamp's border runs. A pie chart or a photo cropped round does not.

    Pixels are read with the image's soft mask applied: scanned signatures and stamps are often a plain colour whose shape is all in the mask. On the samples, a square blue signature's corners held 0.63 of its round's ink, and a logo's 0.68.
  - **Signature**: the image is small, at most 40% of the page's width and 20% of its height (the largest on the samples was 199 by 118 pt), overlaps a row to sign on across the page ("ลงชื่อ", "ลายมือชื่อ", or the whole word "Signature"), and lies less than a row's height above or below it. On the long sample's signing page, four of six blue-ink images sat on or 5 pt above a "ลงชื่อ ......" row and become signatures.
  - **Image** otherwise. The other two images on that page have no signature line near them, and one on page 1 sits on a row of dots alone; all three stay images, rather than guesses.
- **Summary.** `PageSummary.placeholders` lists each page's placeholder kinds in reading order; `Summary.placeholder_count(kind)` totals one kind.
- **Fixtures.** `pdf_builder.Picture` draws a photo, a blue-ink signature, a red stamp or a pie chart from numbers, all but the photo on a transparent ground, so the bytes stay the same. The corpus gains `placeholders`, a signing page with all three; the harness scores it CER 0, and the DOCX corpus test reads it back too.
- **Tests** (`tests/test_placeholders.py`): an image between paragraphs in Markdown and DOCX; a signature on its signature line in both; a scribble away from any signature line, a word that only contains "sign", and a large picture above a signature line all stay images; a stamp, alone, over a signature line and over a whole signature block; a pie chart is no stamp; rules and ornaments; repeated edge images, with initials that move from page to page; stamps at different places at the foot of two pages are kept; an edge image on one page only; an image in a table cell; and the summary, by kind and without placeholders. The searchable-scan test in `tests/test_ocr_pages.py` caught the first version, which made the scan behind the text a placeholder.
- **Left open:**
  - A page that is mostly picture, with little text, is read with OCR, as the page classifier decides, so its image gets no placeholder. Letting pictures not count as ink would also stop scans being read with OCR.
  - Signatures without a signature-line row next to them, such as one above a drawn line or "(name)" only, stay images.
  - The stamp rule was checked against synthetic stamps only; the sample contracts hold none that could be confirmed without looking at them. A stamp with no border ring, or a rectangular one such as a date stamp, stays an image.
  - At the user's request, the sample contracts were not processed again after the first look, so the changes after code review were checked on synthetic pages only.

**2026-10-20, changes after code review**

The reviewer probed the rules with synthetic pages. Four of their cases made a placeholder disappear or guessed a kind:
- **A stamp pressed over a whole signature block disappeared.** Three rows printed over it made it look like the page behind the text. The stamp check now comes first; only images that are not stamps can be the page behind the text.
- **A photo beside "Cover designed by…" became a signature,** because "signed" matched inside a word. English now needs the whole word "Signature", and "Signed" is no longer taken.
- **A 300 by 150 pt photo above a signature line became a signature.** A signature now has to be small, as above.
- **A filled pie chart became a stamp.** A stamp now needs a border band denser than its inside.
- **Stamps of one size at the foot of two signing pages were dropped as furniture**, as were signatures at different places. At the user's choice, repeated edge images now have to be in about the same place too. The same stamp pressed in the same place on two pages is still furniture.

Also changed: the spec's placeholder block keeps the decisions but leaves the thresholds to this ticket; `corpus/README.md` lists `[ตารางอาจไม่สมบูรณ์]`; `GLOSSARY.md` counts a repeated edge image as page furniture; `headline()` says it counts placeholders.

Tidying: tables and placeholders join reading order as `(top, block)` pairs, so no type check picks between them; `_edge` takes a top and a bottom, for rows and images alike; `PlacedImage.round_mark` is `stamp_like`; the furniture loop no longer names two counters `number`; the signature fixture and its line live in `corpus/generate.py` and the tests import them; the picture builder has one branch per kind and ends in `assert_never`.

Not changed: the summary still names a kind by building a `Placeholder`, so that the one `match` with `assert_never` stays the only place labels live.
