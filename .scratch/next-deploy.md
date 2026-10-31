# Next deploy

**Decided:** 2026-10-30, by the user, in triage.

**Status: deployed on 2026-10-31.** Production runs `31d52d5`, `main` after PR #18 (see "The deploy" at the end).

**Production before it:** `c145cab`, live since 2026-10-22.

**On `main` before this deploy, not deployed:** PRs #12–#17.
- rotated pages, sideways pages and two-column OCR pages;
- kept images, in the converter, the command line and the web;
- tables on OCR pages, and OCR pages that are not scans no longer losing lines.

## To finish before the deploy

Each is a small task: `/grill-with-docs`, then `/implement`, then `/code-review`. The suggested order puts text pages first, then whole OCR pages, then uncertain text.

| Order | Ticket | Why it goes first |
| --- | --- | --- |
| 1 | converter-engine 28: a clause reference that wraps becomes a false clause | a contract gains a false clause, on text pages |
| 2 | converter-engine 31: text pages drawn line by line across their columns | the columns' sentences are mixed, with nothing to warn the reader |
| 3 | converter-engine 30: upside-down scans | the whole page is unusable |
| 4 | converter-engine 25: text under a diagonal watermark is lost | whole list items vanish, unmarked |
| 5 | converter-engine 23: English and number misreads are not marked | a misread amount reads as fact |
| 6 | converter-engine 27: uncertain-text marking on Thai scans is off both ways | so many marks that a reader stops looking; real misreads missed |

Tickets 23 and 27 are one piece of work: uncertain text a reader can trust.

## Left for a later version

- **Converter engine:**
  - 20: highlights and notes on text pages;
  - 22: page furniture on scans;
  - 24: pictures on OCR pages that are not scans;
  - 26: ticked boxes on scans;
  - 29: sideways text inside upright pages;
  - 32: side panels and signature blocks read across.
- **Tables on OCR pages:** 10, row labels beside a ruled table.
- **Larger work:**
  - 16, the public-document corpus, which needs the user's documents and checked text;
  - 17, the quality gate and OCR baseline, after 16;
  - 15, Accurate mode with Typhoon.

## At the deploy

- **The web app and the launcher go together,** from one image. An older launcher breaks on the `run-keeping-images` frame, and the page summary now has two required fields, `tables` and `incomplete_tables`.
- **The deploy goes through staging and its gate,** as the web-service tickets set up. Its steps are shown to the user and approved first.
- **Checks still open from the launch:**
  - a file near 50 MB through Funnel;
  - whether Funnel passes on IPv6 addresses.

## The deploy

On 2026-10-31, with the user's approval of each step:
1. **PR #18 merged.** It holds the six tickets above and the triage, with CI passing, so `main` is at `31d52d5`.
2. **Staging:** `scripts/deploy.sh staging main` built `31d52d5` and passed every smoke-test check in 8 minutes:
   - through Tailscale, the web app, the launcher and a gVisor sandbox;
   - every restriction of the sandbox in place;
   - both corpus files at CER 0 in Markdown and DOCX;
   - 2.9 s and 1.4 s per OCR page;
   - no sandbox left behind.
3. **Production:** no conversion was running, so none was cancelled. `scripts/deploy.sh` passed the staging check, rebuilt the image and recreated the web app and the launcher in 17 seconds; the Tailscale container was left running.
4. **Checked:**
   - `/health` answers `ok` through Funnel;
   - `/source-code` opens `31d52d5`;
   - the checkout on `gmt` has no changes.
5. **Staging stopped,** its record `refs/staging/passed` at `31d52d5`.

**Still open:**
- the two launch checks above;
- converter tickets 34 and 35, both needs-triage, split off on the way.
