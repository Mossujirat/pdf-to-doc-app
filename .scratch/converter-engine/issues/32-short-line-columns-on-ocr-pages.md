# 32: Side panels and signature blocks beside other text are read across on OCR pages

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, text with short lines set beside other text is joined line by line with it:
- a narrow panel of the sender's offices and bank details at the edge of a letter;
- signature blocks side by side;
- bank details beside a list of signatories.

An account or registry number lands in the wrong text, and a signer's name can be matched to the wrong title. This is broken text (wrong reading order), and nothing marks it.

**Blocked by:** 18

**Status:** needs-triage

**Seen on:** the local samples listed in ticket 18: the scanned supplement's letter and signing page, the five-page agreement printed to PDF, and signature blocks in the 110-page contract.

**Split out of ticket 18 (2026-10-24).** That ticket splits a page into columns only where both sides are body text. These layouts look too much like label–value lists to split safely.

**What is known so far** (synthetic scans; numbers in ticket 18)
- **Today's CER:** 0.65 on a letter with a side panel, 0.34–0.41 with signature blocks side by side, and 0.36 with bank details beside signatories.
- **Cutting at the gutter between the engine's boxes reads them all right,** at CER 0.015–0.11. But the same cut separates labels from values in label–value lists, term–definition lists and unruled tables.
- **Line length does not separate them.** Median characters per line on the shorter side:

  | Layout | Median |
  | --- | --- |
  | bank details beside signatories | 18.5 |
  | form with two fields on each line | 18 |
  | side panel | 17 |
  | signature blocks | 16.5–17 |
  | label–value layouts | 13.5 at most |

- **Nine guards on box positions were tried;** none separates these layouts from label–value lists (ticket 18).
- **Leads not yet tried:**
  - **A panel set in smaller type** does not share baselines with the body: 41–47% of its lines pair with a body line, against 100% in every label–value list measured. A panel in the body's own type would pair more.
  - **Signature blocks side by side** put "ลงชื่อ" (or "Signature") two or more times on one row. Layout already knows that pattern for placeholders.
- **Ruled out:** PaddleOCR's layout model, PP-DocLayout-S. It read one side-by-side signature page and the bank details as one region (ticket 18).

**To decide at triage**
- Which cue to use for each layout, and whether the signature cue is reliable on real signing pages.
- How the title beside each signature should come out. Today the right-hand signer's title came first on one sample.

## Comments

**2026-10-30, triage**

- **After the next deploy:** the user chose to leave it for a later version. See `.scratch/next-deploy.md`.
- Status stays `needs-triage` until then.
