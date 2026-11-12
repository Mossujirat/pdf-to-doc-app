# 05: Check on the samples, the web page, and what is left

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decisions 8 and 9 of its comment of 2026-11-12.

**What to build:** Proof on the real samples that the feature does what ticket 38 set out, the user's own check of the placeholders before the merge, the site's wording brought up to date, and a ticket for what the model still misses.

**Blocked by:** 02, 03, 04

**Status:** ready-for-agent

**Branch:** `feat/pictures-inside-scans`

**On the samples**

On this machine only, without sub-agents. Record numbers only, and delete the outputs, crops and sheets afterwards.
- [ ] **The signing pages** carry `[ลายเซ็น]` or `[ตราประทับ]`.
- [ ] **The signers' names and the parties' labels** on the signing pages are not garbled.
- [ ] **The initials at the foot are gone.**
- [ ] **Per file, record:**
  - placeholders of each kind;
  - uncertain text before and after;
  - seconds per scanned page.
- [ ] **Text pages do not change:** their output is the same before and after, on every sample.
- [ ] **Contact sheets** of every placeholder's region, for the user to look at on this machine before the merge. Only the user views them.

**Corpus and checks**
- [ ] The harness reports on the corpus's existing files as before.
- [ ] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

**Web**
- [ ] **"ข้างในทำอะไรกับไฟล์ของคุณ"** says that only pages whose text is in the file get placeholders. Change it to include scans. The user approves the Thai.
- [ ] **The known limitation about pictures on scans** is reworded with the user when the release is written, before staging. It points to the new ticket below.

**What is left**
- [ ] **A new ticket in the converter work** for what the model still misses:
  - signatures in black ink;
  - logos, pictures and QR codes.

  Give it the numbers from the samples.
- [ ] Add a comment to ticket 38 that points to this feature's tickets and the new one.
- [ ] Ticket 44 is ready to grill, with the junk ticket 04 recorded.
