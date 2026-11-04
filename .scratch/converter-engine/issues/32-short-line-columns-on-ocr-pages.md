# 32: Side panels and signature blocks beside other text are read across on OCR pages

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What goes wrong:** On OCR pages, text with short lines set beside other text is joined line by line with it:
- a narrow panel of the sender's offices and bank details at the edge of a letter;
- signature blocks side by side;
- bank details beside a list of signatories.

An account or registry number lands in the wrong text, and a signer's name can be matched to the wrong title. This is broken text (wrong reading order), and nothing marks it.

**Blocked by:** 18

**Status:** done

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

**2026-10-30, from ticket 31**

- **Text pages too:** a text page that draws these layouts line by line across is read across in the same way (synthetic pages: CER 0.37 with a panel, 0.39 with signature blocks, 0.56 with bank details beside signatories). Ticket 31 gives text pages ticket 18's column finder, so a cue found here can serve both kinds of page.
- **A real signing page passes the body-text guard:** on the signing page of a research contract among the local samples, the signature blocks' dotted signing lines are long enough that the finder splits the two blocks into columns. Signature blocks with short lines do not pass it.

**2026-11-03, triage**

- **In this round,** with 37, 24 and 26.
- **Scope:** signature blocks side by side, and side panels. Bank details beside signatories split out as ticket 39: neither cue covers them.
- **The cues:**
  - **Signature blocks:** a signing word ("ลงชื่อ", "Signature") two or more times on one row, the pattern placeholders already use. Keep it out of the check that joins a band to the columns above it, or signature blocks under two-column terms join those columns (a test pins this today).
  - **Side panels:** a panel set in smaller type, whose lines do not pair with the body's. A panel in the body's own type stays read across.
- **How signature blocks come out:** each block whole, left before right: its signing line, name and title together, so a name cannot meet another signer's title.
- **Local samples:** the user allows converting them on this machine for the whole round; tickets record numbers and observations only.
- **Estimate:** medium. The code change is small; the cost is in new test pages for each layout, false-split guards, and checks on real signing pages, where OCR may misread the signing word or box it across both blocks.
- **The known limitation on the what's-new page** names signature blocks and side panels only. Closing this ticket drops it; if a panel in the body's own type is still read across, it needs a ticket and a narrower limitation of its own.

**2026-11-04, built**

**Signature blocks** (`_signature_blocks` in `columns.py`). The triage plan was to accept a gutter split when each column held a signing row. On the 110-page contract's signing page that never fired: a company stamp read as text ran across the gap between blocks, signatures read as junk ("ous", "XSt") sat in it, and the blocks were set two rows deep, signer above witness, with no blank line. So blocks are found by their signing rows instead:
- **A row of blocks starts at each printed line with two signing boxes or more** ("ลงชื่อ", "ลายมือชื่อ", "Signature", or a box opening with "By:", as the five-page English agreement names its signers), and runs to the next such line. Each block takes the boxes whose centres lie from its signing word to the next one's.
- **Blocks are read left to right, a row of blocks after the one above,** so each signer stays beside the witness set beside them, as Word draws them. What lies above the first signing row, such as a stamp, is read before the blocks.
- **Only where the band is not columns of body text,** which keeps every page that ticket 18 and 31 read right as it was.
- **"By:" counts here only,** not for signature placeholders: "Photo by" beside a picture must not make it a signature.

**Side panels** (`_panel_columns`). Two columns, one of body text of three lines or more, the other narrower, its boxes at most 0.85 as tall at the median, and fewer than 75% of its lines on a baseline of the body's (centres within a quarter of a box height). The first try, any column in smaller type off the shared baselines, split 13 regions on the 110-page contract, nearly all tables set apart without rules (budget, research team, rights), which reads each item away from its owner. The narrowing left one: the privacy notice's QR caption beside its paragraph, read after it, as it should be. Three body lines at least: a tax form's two heading lines, with a text-layer header joined on, passed for body text.

**What reads row by row still:** labels and values, unruled tables, a panel in the body's own type (new ticket 41), and bank details beside signatories (ticket 39).

**Corpus:** `short-line-columns-scans`, two scans: signature blocks two rows deep, and a letter with a 9-point panel holding an address and a bank account. With real PaddleOCR, CER 0.50 → 0.020 and 0.66 → 0.014. PaddleOCR read every "ลงชื่อ" as "ลงชือ", which ticket 24's tolerance of a lost mai ek accepts.

**The samples,** converted on this machine with the user's standing permission (the 110-page contract replayed from ticket 37's recorded boxes):
- **110-page contract:** the signing page of the rights annex (two rows of signer and witness) reads block by block, each name with its own title, where the right-hand witness's agency was joined to the director's title before. The privacy notice's QR caption follows its paragraph. Nothing else changed; its first signing page, a text page Word draws block by block, reads as before.
- **GIZ supplement:** the letter's side panel of offices, registry and bank details follows the letter, where it was joined line by line into the contract numbers.
- **Five-page agreement:** its signing page reads "By:", title and date block by block. One "Date:" label of the left block was missing before this ticket too.

**Left:** the lines of a panel or block are one paragraph, so a panel's lines join as Thai lines do ("กรุงเทพมหานครโทร"). The block headings "For the United Nations…" / "For National Metal…", in a band of their own above the blocks, still read across.

**The known limitation** now names what is left, the panel in the body's own type and bank details beside signatories (tickets 41 and 39), worded with the user.

**2026-11-04, after code review**

**Fixed, each with a guard test:**
- **A sign-in sheet whose header has two signing columns** ("ลายมือชื่อ (เช้า)", "ลายมือชื่อ (บ่าย)") was cut into blocks, on OCR and text pages. A row of blocks now starts only at a line that opens with its signing box; the sheet's header opens with "ลำดับ".
- **Labels with smaller values that wrap** passed for a side panel: only each value's first line shares a label's baseline. A panel's body may now not share a baseline with it on every line, as labels always do.
- **A paragraph right under the blocks, with no blank line,** joined the left block. Body text in one box that runs across a block's start, by a box height or more each way, ends the blocks; it is read after them all. A box height each way: the five-page sample's right block starts 3 pixels left of its "By:".
- **Tidied:** the unused `_text`; one comment per constant, each with where it comes from; one helper for lined-up columns, shared by body-text columns and panels; the test helper asserts with a message; `corpus/README.md` names this ticket's corpus file and ticket 24's.

**Checked after the fixes:** the three samples come out as recorded above; the corpus file reads at CER 0.020 and 0.014.
