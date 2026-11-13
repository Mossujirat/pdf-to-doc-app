# 38: Signatures, stamps and pictures inside scans are lost

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On a scan read with OCR, signatures, stamps, logos, QR codes and photos are part of the page image. OCR reads them as junk text, marked uncertain, or they vanish. No placeholder stands for them, so the Markdown of a signed contract never says it was signed.

**Blocked by:** none

**Status:** needs-triage

**Seen on:** a 110-page Thai contract among the local samples in `docs/example_pdf/`, converted on 2026-10-23 with the user's permission. None of its 91 OCR pages has a placeholder; its only placeholders are on two text pages. That follows the spec, which gives OCR pages no placeholders on the grounds that they are images themselves.

**Split from:** ticket 24, on 2026-11-03, in triage. Ticket 24 keeps the pictures that are separate images in the PDF, on OCR pages that are not scans: the text-page placeholder rules can serve them. Finding a picture inside a page image takes image analysis, so it is a ticket of its own.

**To decide at triage**
- How to find a signature, a stamp or a picture in the page image, and tell it from text and table rules.
- Which placeholder kinds it can tell apart, and when it is unsure.
- Whether its ink is blanked before OCR reads the page.

## Comments

**2026-11-10, from a 10-page scanned contract**

The 10-page scanned Thai contract of ticket 42 was converted on 2026-11-10 with the user's permission.

- **Initials at the foot of every page:** two sets on each of 9 pages. They came out as junk marked uncertain, often with a row of dots beside them.
  - Ticket 24 fixed this for OCR pages that are not scans. It still happens on scans.
- **Junk damages real text, not only adds to it.** On the signing page, junk read from a signature joined the printed party label on the same signing row, and the uncertain mark covered the label too. One label came out garbled, and another lost a tone mark.
- **The initials keep page furniture from matching.** OCR reads the initials differently on each page, and they share a baseline with a footer line, so that line never matches across pages (ticket 22's comment of the same day). Triage this ticket with 22, or before it.

**2026-11-11, from ticket 22**

- **A footer line beside initials is now removed with them.** Ticket 22 matches furniture on OCR pages by what OCR is sure of, so the junk on the footer's row no longer stops the match. The whole row goes, its junk too.
- **Junk rows of their own stay,** such as a row of dots or a stray letter under the initials. On the 10-page contract, 5 such rows are left on 4 pages.

**2026-11-12, grilled with the user, together with ticket 44**

**Measured on the samples,** on this machine with the user's permission. Numbers only; the page images, boxes and contact sheets were deleted afterwards.
- **Every scan in the samples is in colour (RGB).**

  | File | Scanned pages | Pages with coloured ink |
  | --- | --- | --- |
  | The 10-page contract | 10 | 10. On 9 of them most of it lies at the foot, which is the initials in pen. |
  | The 110-page contract | 90 | 27 |
  | The 34-page supplement | 34 | 4 |
- **Coloured ink alone,** in regions of 1,500 pixels or more at 150 dpi: 50, 92 and 11 regions.
  - **Wrong on highlights:** printed text under a highlight passes for ink. Regions whose paper is mostly bright colour (a share of 0.3 or more) are highlights, and dropping them kept 48, 67 and 2. The user checked that what this dropped was right to drop.
  - **Still wrong on text printed in colour,** as on the 10-page contract's first page: 19 regions.
- **PaddleX layout models,** run on the same pages:

  | Model | Size | Seconds per page | "image" regions (110-page contract) |
  | --- | --- | --- | --- |
  | PP-DocLayout-S | 5 MB | 0.08 | 31 |
  | PP-DocLayout-M | 23 MB | 0.17 | 23 |
  | PP-DocLayout_plus-L | 125 MB | 1.3–1.6 | 55 |

  - **No model found a "seal" on any page.**
  - **plus-L:** its "image" regions were mostly right, by the user's check of contact sheets. It missed some full signatures and some logos, pictures and QR codes.
  - **Memory:** the three models in one process peaked at 1.38 GiB.

**Decisions**
1. **Scope:** signatures, initials, stamps, logos, photos and QR codes inside scans. The user chose to keep them all, rather than signature-like marks alone.
2. **The finder:**
   - **On scans only,** using PP-DocLayout_plus-L's "image" regions, plus "chart" and "seal" should it give them.
   - **The model is fetched by `pdf-to-doc-models`,** pinned like the OCR models. It is Apache-2.0, published by PaddlePaddle on Hugging Face.
   - **Signatures the model misses:** coloured ink beside a row to sign on (`SIGNATURE_LINE`) is a signature too, with highlights dropped as above. Ink is looked for there only, so text printed in colour elsewhere does not count.
3. **The kind of placeholder:** ticket 24's rules, as for pictures on a text page.
   - A ring in colour is a stamp.
   - A small picture beside a row to sign on is a signature.
   - Anything else is an image.
   - Pictures repeated at the same edge across pages are page furniture.
4. **Initials at the foot of the pages** are page furniture, and are dropped with the junk rows read in them, as on text pages.
5. **Text inside a picture's region:** text OCR read surely stays, such as a signer's name printed under a signature. Text it is unsure of, and junk, is dropped, and the placeholder stands in their place.
6. **Cost:**
   - **Time:** about +1.3 s per scanned page, against 2.8 s of OCR on the server. The 110-page contract would take about 6–7 minutes, well under the 30-minute limit.
   - **Memory:** it is measured with OCR in one sandbox. If the peak passes 2 GiB, the sandbox's memory limit goes to 3 GiB (`_MEMORY` in `web/docker.py`), through staging as usual.
7. **With images kept,** nothing changes: a scan is shown whole as an image.
8. **What is left** goes to a new ticket, and the known limitation on the what's-new page points there, worded with the user at the deploy:
   - signatures in black ink that the model misses;
   - logos, pictures and QR codes it misses.
9. **Done when:**
   - text pages do not change;
   - the corpus reports as before;
   - on the samples, the signing pages carry `[ลายเซ็น]` or `[ตราประทับ]`, the signers' names are not garbled, and the initials at the foot are gone;
   - the user looks at contact sheets of the placeholders before the merge;
   - tests and mypy pass.

**Size:** large. Next comes a spec (`/to-spec`), then tickets. Ticket 44 is grilled after this one is built.

**Also found:** `iapp/OpenThai2.0-OCR-Markdown`, noted on ticket 15 as a candidate for Accurate mode. It is not used here.

**2026-11-13, built**

- **Where:** the feature is built on branch `feat/pictures-inside-scans`, as the tickets in `.scratch/pictures-inside-scans/issues/`:
  - **01:** pictures found in a scan become placeholders;
  - **02:** the layout model PP-DocLayout_plus-L finds them;
  - **03:** coloured ink beside a row to sign on;
  - **04:** initials at the foot are page furniture;
  - **05:** the check on the samples.

  Their Comments hold the measurements.
- **What is left** is ticket 47, `47-pictures-the-layout-model-misses-on-scans.md`: signatures in black ink, coloured ink under rows of print, and logos, pictures and QR codes the model misses.
- **This ticket stays open until the release is written.** The known limitation on the what's-new page points here. When the release is written, the user rewords it to point to ticket 47, and this ticket is closed.
