# 17: Quality gate + OCR baseline

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** This ticket gives an objective answer to "is the converter good enough to put behind a web page?" (decision Q27). It runs the full harness over:
- the committed corpus
- the user's confidential reference pages, which stay local

It then checks the text-page gate, records the OCR baseline, and the user sets the numeric OCR target from real measurements.

**Blocked by:** 10, 11, 14, 16. It also needs the user's corrected reference text for the confidential scanned pages, at least 5–6 pages.

**Status:** ready-for-human

**Branch:** `chore/quality-gate`

**Text-page gate**
- [ ] Zero broken text on every text page in both corpora. Any failure is fixed, or filed as a new ticket, before the gate passes.

**OCR baseline**
- [ ] For OCR pages, record per engine (default and Accurate mode):
  - CER, overall and Thai-only
  - the share of wrong characters left unmarked
  - seconds per page
- [ ] Commit the baseline for the public corpus to the repo. Keep the confidential-corpus numbers only as aggregate figures, never as text excerpts.

**Decision**
- [ ] The user sets the numeric OCR target.
- [ ] The harness threshold in CI is updated to match.
- [ ] Record the target and its reasoning, as an ADR if it involved a real trade-off.

**Afterwards**
- [ ] Note what the web spec needs to settle next: hosting, and whether a GPU is needed for Accurate mode.
