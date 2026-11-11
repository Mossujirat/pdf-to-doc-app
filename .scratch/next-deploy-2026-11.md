# Next deploy: contracts' costliest errors

**Decided:** 2026-11-03, by the user, in triage.

**Status:** deployed 2026-11-04. Production runs `6467c4f`: PR #23 (the four tickets) and PR #24 (the release).

**Production before this round:** `c109ac0`, deployed 2026-11-02. The previous round is recorded in `.scratch/next-deploy.md`.

## To finish before the deploy

Each is its own task: `/grill-with-docs` if anything is still open, then `/implement`, then `/code-review`. Each ticket's 2026-11-03 triage comment holds its scope and estimate.

| Order | Ticket | Why | Estimate |
| --- | --- | --- | --- |
| 1 | converter-engine 37: numbers misread as other numbers | an amount or date changed by one digit reads as fact | small, plus a day's measurement |
| 2 | converter-engine 24: pictures on OCR pages that are not scans | the Markdown of a signed agreement never says it was signed | small to medium |
| 3 | converter-engine 32: side panels and signature blocks read across | a signer's name can meet another signer's title | medium |
| 4 | converter-engine 26: ticked boxes on scans | the choice a form records is lost | medium, two to four days |

24 goes before 32: both work on signing pages, and 32 orders signature blocks that 24 gives placeholders.

**The user allows converting the local samples in `docs/example_pdf/` on this machine for the whole round.** Tickets record numbers and observations only, never text copied from the contracts.

## The what's-new page

- Each ticket that closes behind a known limitation drops or rewords it in `src/pdf_to_doc/web/releases.py`, and the release lists the fix, saying no more than the ticket measured.
- **37** closes, but its limitation stays for good, pointing to ticket 40.
- **24** closes, but the limitation about pictures on scans stays for ticket 38.
- **32** closes and drops its limitation, unless a side panel in the body's own type is still read across.
- **26** closes and drops its limitation.

## Done

- **37,** 2026-11-04, on `fix/number-misread-rules`. Its known limitation now says what is left, worded with the user. A draft line for the release, to approve at the deploy: "ตัวเลขในหน้าสแกนที่อ่านผิดจนเป็นไปไม่ได้มีสีเหลืองบอกแล้ว ได้แก่ จำนวนเงินที่จุลภาคคั่นไม่ลงตัวทีละสามหลัก ปีในวันที่ที่เหลือสามหลัก และวันที่ที่เดือนนั้นไม่มี".
- **24,** 2026-11-04, on `fix/pictures-on-drawn-pages`, branched from 37's. Its known limitation stays for ticket 38, as worded. A draft line for the release: "ไฟล์ PDF ที่ตัวหนังสือเป็นลายเส้น ไม่ใช่ภาพสแกน (เช่นไฟล์ที่สั่งพิมพ์ออกมาเป็น PDF) มีป้ายบอกลายเซ็น ตราประทับ และรูปภาพในข้อความแล้ว และลายเซ็นย่อที่ท้ายทุกหน้าไม่ติดมาเป็นตัวอักษรมั่วอีก".
- **32,** 2026-11-04, on `fix/signature-blocks-and-side-panels`, branched from 24's. Its known limitation now names what is left (tickets 39 and 41), worded with the user. A draft line for the release: "ลายเซ็นหลายชุดที่วางเรียงกันบนหน้าสแกน อ่านทีละชุดแล้ว ชื่อผู้ลงนามอยู่กับตำแหน่งของตัวเอง และแถบที่อยู่ข้างจดหมายที่ตัวอักษรเล็กกว่าเนื้อความ อ่านต่อท้ายจดหมาย ไม่ปนกับเนื้อความอีก".
- **Split off on the way:** 41, side panels in the body's own type.
- **26,** 2026-11-04, on `fix/ticked-boxes`, branched from 32's. Its known limitation is dropped. A draft line for the release: "ช่องติ๊กบนหน้าสแกนออกมาแล้ว ช่องที่ติ๊กเป็น ☒ ช่องว่างเป็น ☐ อยู่หน้าตัวเลือกหรือในช่องตาราง ถ้าในช่องมีแค่รอยเล็กๆ จนไม่แน่ใจ จะมีสีเหลืองบอก".

## Split off in triage

- **38:** signatures, stamps and pictures inside scans (from 24).
- **39:** bank details beside a list of signatories (from 32).
- **40:** number misreads that 37's rules cannot catch (from 37).

## Left for a later version

- **Converter engine:**
  - 20 and 36: highlights and notes, on text pages and on scans, one piece of work;
  - 22: page furniture on scans;
  - 29: sideways text inside upright pages;
  - 34: diagonal text on scans;
  - 35: Thai misreads that are real words;
  - 38, 39 and 40 above.
- **Tables on OCR pages:** 10, row labels beside a ruled table.
- **Larger work:** 15, Accurate mode with Typhoon; 16, the public-document corpus; 17, the quality gate and OCR baseline.

## At the deploy

- **The release entry** goes into `releases.py` before staging, dated the deploy day, with the Thai wording approved by the user (`docs/DEPLOY.md`).
- **Through staging and its gate,** with the steps shown to the user and approved first.
- **Checks still open from the launch:** a file near 50 MB through Funnel; Funnel on IPv6.

## Deployed

**2026-11-04:** PR #23 merged, then PR #24 with the release entry, as worded and approved by the user. Staging passed its smoke test at `6467c4f` (CER 0.000 on both corpus files, 2.3 and 1.4 s per OCR page); production runs `6467c4f`, and its `/health`, what's-new page and `/source-code` answer as they should. The two checks still open from the launch stay open.

## The next round: deployed 2026-11-11

The user chose this order on 2026-11-10. Each ticket was grilled, built and reviewed on its own branch and merged on its own PR:

| Ticket | PR | What it fixed |
| --- | --- | --- |
| converter-engine 42 | #26 | single lines lost on clean scans, read again blurred |
| converter-engine 39 | #27 | headed blocks side by side, in the body's own type, read a column at a time |
| converter-engine 22 | #28 | page furniture on scans that OCR reads differently, or a little further in |
| converter-engine 43 | #29 | list markers that OCR reads joined to their word |

- **The release,** PR #30. It lists the four fixes, worded and approved by the user. It adds ticket 42's known limitation, which points to ticket 46, opened for the lines still lost. The limitations for 39 and 22 had already been reworded to point to tickets 41 and 44.
- **Opened on the way:** 44 (furniture still left), 45 (list markers OCR does not read), 46 (lines still lost unmarked). All three need triage. 41 is `needs-info`.
- **Deployed:** staging passed its smoke test at `24b8cf0`, with a CER of 0.000 on both corpus files, at 2.8 and 1.4 s per OCR page. Production runs `24b8cf0`. Its `/health`, its what's-new page with the release of 11 November, and `/source-code` answer as they should. Staging was stopped.
- **Branches:** the round's five merged branches were deleted locally and on GitHub. The eight older ones stay.
- **Still open from the launch:** a file near 50 MB through Funnel, and Funnel on IPv6.
