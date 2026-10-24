# 03: Show pictures on text pages as themselves in DOCX

**Parent:** Kept images spec, in this feature folder.

**What to build:** With kept images chosen, each picture on a text page appears in the DOCX as the picture itself, where its placeholder would be. That covers photos, charts, signatures and stamps. The DOCX of a signed contract then shows the signatures and stamps. The Markdown keeps today's placeholders, and without kept images the DOCX is as today.

**Blocked by:** 01

**Status:** ready-for-agent

**Branch:** `feat/kept-images`

**The picture**
- [ ] With kept images on, the placeholders of pictures on text pages (image, signature, stamp) carry the picture. With it off, they carry nothing.
- [ ] The picture is the image object itself, not a crop of the page:
  - nothing drawn over or under it;
  - its soft mask becomes transparency;
  - turned and flipped as it is shown on the page, so a picture on a rotated page stands upright (ticket 19);
  - at most 150 dpi at the size it is placed;
  - other colour spaces, such as CMYK, converted to RGB.
- [ ] Only compressed bytes are held: JPEG when the picture is opaque, PNG when it has transparency.
- [ ] Pictures that get no placeholder today are not shown either (ticket 09's rules):
  - images too small to be pictures;
  - images behind text;
  - images repeated at an edge, such as a logo on every page.

**DOCX**
- [ ] A picture sits in a paragraph of its own, where its placeholder would be. It keeps the size it is placed at, shrunk to the text area, keeping its shape, when it is larger.
- [ ] An image inside a table cell comes right after the table, as its placeholder does.
- [ ] Checked once in real Word: pictures stand upright, and a signature on a transparent ground does not cover the line under it.

**Markdown**
- [ ] Unchanged: `[รูปภาพ]`, `[ลายเซ็น]` and `[ตราประทับ]` as today.

**Tests** (through the conversion function, with `pdf_builder` pictures)
- [ ] Each of these is shown in the DOCX at its place and size:
  - a photo between paragraphs;
  - a signature on its signature line;
  - a stamp;
  - a pie chart;
  - a picture with transparency on a rotated page.
- [ ] A picture wider than the text area is shrunk to fit.
- [ ] An image in a table cell comes after the table.
- [ ] These are left out:
  - a repeated edge logo;
  - an image behind three or more rows of text;
  - a rule-sized image.
- [ ] Without kept images, the DOCX is unchanged.
- [ ] The Markdown is the same with and without kept images.
- [ ] pytest, mypy, the harness and the checks in the Linux image all pass.
