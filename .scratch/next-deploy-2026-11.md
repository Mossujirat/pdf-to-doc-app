# Next deploy: contracts' costliest errors

**Decided:** 2026-11-03, by the user, in triage.

**Status:** planned. Nothing started.

**Production:** `c109ac0`, deployed 2026-11-02. The previous round is recorded in `.scratch/next-deploy.md`.

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
