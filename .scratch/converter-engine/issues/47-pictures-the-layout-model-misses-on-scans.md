# 47: Signatures and pictures the layout model misses on scans

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** Since ticket 38, a scan read with OCR gets placeholders for the pictures inside it. PP-DocLayout_plus-L finds them, helped by coloured ink beside a row to sign on. Some are still missed, and a missed signature leaves the Markdown with no sign that the page was signed:
- **Signatures in black ink** that the model misses. The coloured-ink rule cannot find them, because black ink looks the same as print.
- **Coloured ink with print over it.** A signature under three rows of print or more is taken for the page behind the text, as a whole scan is.
- **Logos, pictures and QR codes** that the model misses.

**Blocked by:** none

**Status:** needs-triage

**Split from:** ticket 38, on 2026-11-13, by its last ticket (`.scratch/pictures-inside-scans/issues/05`).

**Seen on the samples,** on this machine, numbers only (2026-11-13):

| File | Signing scans | With `[ลายเซ็น]` | Left without one |
| --- | --- | --- | --- |
| The 10-page contract | 1, with 5 rows that match a row to sign on | 1, with one signature, found by its blue ink | 3 of those rows still hold text marked uncertain, as they did before ticket 38: junk read in a signature joins a party's label |
| The 110-page contract | 4 | 3, with 4 signatures | 1, whose only coloured ink lies under 3 rows of print |
| The 34-page supplement | 1, with 3 rows to sign on | 0 | the page holds no coloured ink, and the model found nothing on it |

- **The 10-page contract's signing page:** the model took the whole signature block for one image, rows of print and all, and the page held one mark of coloured ink. Whether its other rows were signed in black, or not at all, is for the user's look at the page.
- **`[รูปภาพ]` from scans:**
  - 33 in the 110-page contract;
  - 2 in the 10-page contract;
  - 3 in the supplement.

  The user checks the contact sheets of ticket 05 before the merge. Logos, pictures and QR codes the model missed are not counted yet; that check is where to count them.

**To decide at triage**
- Whether to find signatures in black ink beside a row to sign on, and how to tell them from print: by stroke width, by OCR reading nothing surely there, or by a second model.
- Whether coloured ink under rows of print is a signature when the rows are what OCR read in it.
- Whether a smaller or second layout model finds the logos and QR codes that plus-L misses, and at what cost per page.
