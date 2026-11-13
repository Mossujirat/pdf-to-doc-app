# 05: Check on the samples, the web page, and what is left

**Parent:** ticket 38 of the converter work (`.scratch/converter-engine/issues/38-pictures-inside-scans.md`), decisions 8 and 9 of its comment of 2026-11-12.

**What to build:** Proof on the real samples that the feature does what ticket 38 set out, the user's own check of the placeholders before the merge, the site's wording brought up to date, and a ticket for what the model still misses.

**Blocked by:** 02, 03, 04

**Status:** ready-for-human

**Branch:** `feat/pictures-inside-scans`

**On the samples**

On this machine only, without sub-agents. Record numbers only, and delete the outputs, crops and sheets afterwards.
- [x] **The signing pages** carry `[ลายเซ็น]` or `[ตราประทับ]`.
- [x] **The signers' names and the parties' labels** on the signing pages are not garbled.
- [x] **The initials at the foot are gone.**
- [x] **Per file, record:**
  - placeholders of each kind;
  - uncertain text before and after;
  - seconds per scanned page.
- [x] **Text pages do not change:** their output is the same before and after, on every sample.
- [ ] **Contact sheets** of every placeholder's region, for the user to look at on this machine before the merge. Only the user views them.

**Corpus and checks**
- [x] The harness reports on the corpus's existing files as before.
- [x] Run pytest, mypy, `pytest -m ocr`, the harness, and the checks in the Linux container.

**Web**
- [x] **"ข้างในทำอะไรกับไฟล์ของคุณ"** says that only pages whose text is in the file get placeholders. Change it to include scans. The user approves the Thai.
- [ ] **The known limitation about pictures on scans** is reworded with the user when the release is written, before staging. It points to the new ticket below.

**What is left**
- [x] **A new ticket in the converter work** for what the model still misses:
  - signatures in black ink;
  - logos, pictures and QR codes.

  Give it the numbers from the samples.
- [x] Add a comment to ticket 38 that points to this feature's tickets and the new one.
- [x] Ticket 44 is ready to grill, with the junk ticket 04 recorded.

## Comments

**2026-11-13, checked on the samples**

- **How it was measured:** on this machine, numbers only.
  - **Before** is `main` (e3bab27). **After** is this branch with tickets 01 to 04.
  - **Both read the same pages,** from one cache of PaddleOCR's and the layout model's readings. `main` asked for no reading the branch had not.
  - **The four samples:** the 5-page agreement, the 110-page contract, the 10-page contract and the 34-page supplement.
- **Placeholders, before → after:**

  | File | `[ลายเซ็น]` | `[ตราประทับ]` | `[รูปภาพ]` |
  | --- | --- | --- | --- |
  | The 5-page agreement (no scans) | 0 → 0 | 0 → 0 | 2 → 2 |
  | The 110-page contract | 4 → 8 | 0 → 0 | 4 → 33 |
  | The 10-page contract | 0 → 1 | 0 → 0 | 0 → 2 |
  | The 34-page supplement | 0 → 0 | 0 → 0 | 0 → 3 |

  - **No stamp:** no sample scan holds a ring in colour that was found, as grilling found no "seal".
- **Uncertain text,** in marked spans and characters, before → after:

  | File | Before | After |
  | --- | --- | --- |
  | The 5-page agreement | 5 spans, 26 characters | 5, 26 |
  | The 110-page contract | 1,143 spans, 8,062 characters | 1,136, 7,923 |
  | The 10-page contract | 26 spans, 130 characters | 20, 96 |
  | The 34-page supplement | 131 spans, 642 characters | 130, 637 |

- **Text pages do not change.**
  - **The 110-page contract's 19 text pages** come out the same before and after.
  - **The other samples have no text pages.** The 5-page agreement's OCR pages, which are not scans, are the same too.
- **The signing pages:**
  - **The 110-page contract:** 3 of its 4 signing scans carry `[ลายเซ็น]`, with 4 signatures. Its signatures on text pages were there before.
  - **The 10-page contract:** its signing scan carries 1 `[ลายเซ็น]`, found by its blue ink (ticket 03).
  - **Left without one:** the 110-page contract's fourth signing scan, whose coloured ink lies under three rows of print, and the supplement's, which holds no coloured ink. Both go to ticket 47.
- **Garbling on the signing scans.** Text marked uncertain on each page fell or stayed the same, before → after:

  | Page | Characters marked |
  | --- | --- |
  | The 110-page contract's signing scans | 63 → 63, 308 → 283, 76 → 76, 92 → 82 |
  | The 10-page contract's signing scan | 36 → 35 |
  | The supplement's | 57 → 57 |

  - **Lines that now run together:** on one page, the signer's lines under the signature had been parted by junk read in it. They now run on as one paragraph, as close rows do; ticket 01 tests the same.
  - **Not fixed:** 3 rows to sign on of the 10-page contract still hold text marked uncertain, as before. That is junk from signatures the finder missed, joined to the parties' labels. It is in ticket 47.
- **The initials at the foot are gone** on the 10-page contract: no junk is left at its foot (ticket 04).
- **Seconds per scanned page,** on this machine (Windows, 16 logical CPUs), from the readings that filled the cache:

  | File | Scans | OCR and layout model | Of which the layout model |
  | --- | --- | --- | --- |
  | The 110-page contract | 87 | 6.7 s | 1.4 s |
  | The 10-page contract | 10 | 5.5 s | 1.6 s |
  | The 34-page supplement | 34 | 7.4 s | 1.6 s |

  - **Looking for coloured ink** took 1.1 s over the whole 110-page contract. It runs only on scans with a row to sign on.
  - **On the server's limits,** ticket 02 measured 579 s for the 110-page contract with the model, against 426 s without.
- **Contact sheets:** 39 crops, one for each placeholder from a scan, each labelled with its file, page, kind and finder ("model" or "ink"):
  - 33 from the 110-page contract;
  - 3 from the 10-page contract;
  - 3 from the supplement.

  They are in the session's scratchpad, under `samples/sheets/`, for the user to look at before the merge. Only the user has viewed them.
- **The corpus and checks:**
  - **The harness:** on the corpus's existing documents, every row is the same as at 87adacf (ticket 03). Its new document, `pictures-in-scans`, reads at CER 0.0063.
  - **On this machine:** pytest, mypy and `pytest -m ocr` passed.
  - **In the Linux container,** the checks of `ci.yml` all passed:
    - mypy;
    - pytest: 798 passed;
    - `-m ocr`: 32 passed;
    - `-m slow`: 1 passed;
    - the harness with `--max-broken 0`;
    - a mounted conversion;
    - the sandbox entry point.
- **Web:** the paragraph under "เก็บโครงสร้าง และไม่เดาสิ่งที่อ่านไม่ได้" now says placeholders stand for pictures on scans too, though the converter may miss some, such as signatures in black ink or some logos. It also says that initials repeated at the foot of pages are cut, like page numbers. The user chose this wording, which says what may be missed, over a shorter one.
- **Left for the release:** the known limitation about pictures on scans still points to ticket 38, which stays open until then. The test that every known limitation stands for an open ticket needs that. When the release is written, the user rewords the limitation to point to ticket 47, and ticket 38 is closed.
- **Status is `ready-for-human`** until the user has looked at the contact sheets. Then the outputs, the cache and the sheets are deleted.
