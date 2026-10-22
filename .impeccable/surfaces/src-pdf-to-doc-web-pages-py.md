---
version: 1
slug: "src-pdf-to-doc-web-pages-py"
primary_target: "src/pdf_to_doc/web/pages.py"
related_targets: ["src/pdf_to_doc/web/static/app.js", "src/pdf_to_doc/web/static/site.css"]
---

# Surface: the web service's pages (home and conversion)

Mode: Operate. A Thai office worker converts one PDF or DOCX and takes the text. Every state of the conversion page is part of this surface. The service is named ครบคำ (the user renamed it from เป๊ะ on 2026-10-21).

## Direction contract

THESIS: A converter that looks the way people already know a converter to look, so nothing stands between the file and the text. On 2026-10-22 the user replaced the boarding-pass direction with this one, pointing at pdfguru's PDF to Word page as the reference for its simplicity. It keeps what that kind of site usually adds out: no ads, no invented numbers or reviews, no upsell.

OWN-WORLD: A white page, a slim top bar with the green wordmark, and one dark green, #0F6B55, used for the drop area, the one primary button and the marks of steps done. A pale green tint is used for the current step and for selection. Amber is used only for a page to check. Prompt 400, 500 and 600, loopless, for everything.

STORY: The visitor reads the title, drops a file on the green area and is sent straight to its page. The page shows each step as it happens, then the copy button and how each page was read.

FIRST VIEWPORT: The centred title and subtitle, then the big green drop area, inside a dashed frame, with a white "+" circle. One line under it says where the file goes. Below the fold are three numbered steps and the "กำร → การ" example. Every other page is one white card in the middle.

FORM: canon, the familiar centred converter, by the user's choice of reference.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
