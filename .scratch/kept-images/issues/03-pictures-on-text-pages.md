# 03: Show pictures on text pages as themselves in DOCX

**Parent:** Kept images spec, in this feature folder.

**What to build:** With kept images chosen, each picture on a text page appears in the DOCX as the picture itself, where its placeholder would be. That covers photos, charts, signatures and stamps. The DOCX of a signed contract then shows the signatures and stamps. The Markdown keeps today's placeholders, and without kept images the DOCX is as today.

**Blocked by:** 01

**Status:** done

**Branch:** `feat/kept-images`

**The picture**
- [x] With kept images on, the placeholders of pictures on text pages (image, signature, stamp) carry the picture. With it off, they carry nothing.
- [x] The picture is the image object itself, not a crop of the page:
  - nothing drawn over or under it;
  - its soft mask becomes transparency;
  - turned and flipped as it is shown on the page, so a picture on a rotated page stands upright (ticket 19);
  - at most 150 dpi at the size it is placed;
  - other colour spaces, such as CMYK, converted to RGB.
- [x] Only compressed bytes are held: JPEG when the picture is opaque, PNG when it has transparency.
- [x] Pictures that get no placeholder today are not shown either (ticket 09's rules):
  - images too small to be pictures;
  - images behind text;
  - images repeated at an edge, such as a logo on every page.

**DOCX**
- [x] A picture sits in a paragraph of its own, where its placeholder would be. It keeps the size it is placed at, shrunk to the text area, keeping its shape, when it is larger.
- [x] An image inside a table cell comes right after the table, as its placeholder does.
- [x] Checked once in real Word: pictures stand upright, and a signature on a transparent ground does not cover the line under it.

**Markdown**
- [x] Unchanged: `[รูปภาพ]`, `[ลายเซ็น]` and `[ตราประทับ]` as today.

**Tests** (through the conversion function, with `pdf_builder` pictures)
- [x] Each of these is shown in the DOCX at its place and size:
  - a photo between paragraphs;
  - a signature on its signature line;
  - a stamp;
  - a pie chart;
  - a picture with transparency on a rotated page.
- [x] A picture wider than the text area is shrunk to fit.
- [x] An image in a table cell comes after the table.
- [x] These are left out:
  - a repeated edge logo;
  - an image behind three or more rows of text;
  - a rule-sized image.
- [x] Without kept images, the DOCX is unchanged.
- [x] The Markdown is the same with and without kept images.
- [x] pytest, mypy, the harness and the checks in the Linux image all pass.

## Comments

**2026-10-24, implemented on branch `feat/kept-images`**

- **Where pictures come from.**
  - With kept images, only the text pages that have images are read again, by `pdf_text.kept_pictures`. It is PyMuPDF's reading of `text_rows` once more, with each `PlacedImage` carrying its `kept_image`.
  - So scans, which a kept page or OCR shows instead, are never turned into pictures, and nothing is added without kept images.
  - Layout puts the picture into the placeholder it already makes. Images that make no placeholder are not shown, under ticket 09's rules: too small, behind text, or page furniture.
- **Making the picture** (`pdf_images._kept_picture`, from the image block):
  - converted to RGB;
  - its soft mask applied as transparency, resized when the mask has a resolution of its own;
  - scaled down to at most 150 dpi along its own sides on the page;
  - turned the nearest quarter turn to how its transform draws it, and flipped first when the transform mirrors it;
  - saved as a PNG when a pixel is transparent, otherwise as a JPEG at quality 75.
  - Its size is the length of its own sides, so a picture tilted a few degrees is shown level and keeps its shape. The first version took the tilted box, and stretched a 2:1 photo set at 30° to 178.6 × 149.3 pt; it is now 179.2 × 89.6.
- **The DOCX:**
  - A picture sits in a paragraph of its own, set single-spaced, where its placeholder was. It is shrunk to the A4 text area (451.3 × 697.9 pt), keeping its shape.
  - The page image of a kept page and its section moved into `pdf_images`, so the 150 dpi lives in one place for ticket 04.
- **Not covered:** an image stored as a stencil (an `/ImageMask`, drawn in the colour of the moment) comes out as stored, black and opaque, because PyMuPDF does not say what colour drew it.
  - In the DOCX it is still a picture in a paragraph of its own, so it covers nothing; only its ink colour is lost.
  - Ticket 07 checks whether the samples hold any.
- **`pdf_builder` gains on `Picture`:**
  - `turn`, drawn turned;
  - `dpi`;
  - `cmyk`, a CMYK JPEG.

  The defaults keep every committed corpus file the same.
- **Checks:**
  - **Turned pictures:** compared with PyMuPDF's render of the page, at 90°, 180° and 270°, and on pages turned upright by the PDF. With pictures never turned, the three turned tests fail.
  - **The reviewer, with throwaway scripts:** pictures drawn turned on rotated pages, and a mirrored picture, all matched the render.
  - **Real Word (16, through COM):** a synthetic DOCX gave 4 pages and 8 inline pictures, each as in the original side by side:
    - a photo;
    - a transparent signature on its line;
    - a stamp over a signature line;
    - a chart;
    - a photo drawn turned 90°;
    - a photo wider than the text area;
    - a signature on a page turned upright by the PDF;
    - a picture in a table cell.
  - **Default output:** the same as `main` on the 17 corpus PDFs: Markdown byte for byte, and DOCX except `docProps/core.xml`.
  - **Linux image:** mypy, pytest, `pytest -m ocr`, the harness (OCR CER 0.0072, unchanged), the CLI with `--keep-images` on the placeholders sample, and the sandbox entry point.
- **Code review** (two axes):
  - **Spec, fixed:** the stretched tilted picture. The test of a picture on a page turned upright by the PDF now compares the picture with the page's render, so an upside-down picture would fail it.
  - **Spec, left open:** stencil images, above, and the mirrored path, which `pdf_builder` cannot draw without writing a content stream by hand; the reviewer checked it by script.
  - **Standards, fixed:**
    - "rotated page" in a test name;
    - `_KEPT_DPI` private;
    - the selection of pages with pictures named;
    - why a negative determinant means a mirrored picture;
    - one helper for a pixmap's values, and one for shrinking to fit;
    - `PlacedImage.kept_image`;
    - `docx_reader.block_text` reused, not copied;
    - a test that repeated `test_placeholders` removed;
    - the test file's docstring;
    - the slope tolerance explained.
