# 06: Cap the outputs the web app holds

**Parent:** Kept images spec, in this feature folder.

**What to build:** The web app stops taking new files while the outputs it holds total 1 GB or more.
- **Why:** with kept images a DOCX can reach 50 MB, and outputs are held in memory for 10 minutes. Without a cap, a burst of large conversions could hold about 2 GB. The web container has no memory limit, on a server it shares with Chatbot.
- **What the visitor sees:** "คิวเต็ม" until older outputs expire or are deleted.
- Decided with the user on 2026-10-24.

**Blocked by:** None (can start immediately)

**Status:** done

**Branch:** `feat/kept-images-web`

**The cap**
- [x] A new setting, `max_held_outputs`, in bytes, 1 GB by default, set through `PDF_TO_DOC_MAX_HELD_OUTPUTS`. It is read like the other number settings.
- [x] It counts the outputs that ended conversions still hold. When they total the cap or more, a new upload gets the "คิวเต็ม" page, with the same status as a full queue. Nothing of the refused file is kept.
- [x] Running conversions may add up to their own outputs on top of the cap. That is the headroom.
- [x] While the cap is reached, conversions already waiting do not start either (added with the user on 2026-10-25; see Comments).
- [x] Once outputs expire or are deleted, uploads are taken again.
- [x] The statistics count these refusals under a kind of their own, apart from a full queue.

**Tests**
- [x] With a small cap and a fake sandbox that returns large outputs, check that:
  - an upload is refused once the cap is reached;
  - it is taken again after a deletion, or after the outputs expire on the fake clock.
- [x] The refusal is counted under its own kind.
- [x] The setting is read from the environment, and a value it cannot take stops the service from starting.
- [x] pytest and mypy pass.

## Comments

**2026-10-25, implemented on branch `feat/kept-images-web`**

- **The setting:** `Settings.max_held_outputs`, 1024 × 1024 × 1024 bytes by default. That is a GB of 1024 MB, as the 50 MB output limit (`MAX_OUTPUTS`) counts its MB. It is read like the other whole numbers: "1GB" and "-1" stop the service. A cap of 0 is taken, as `max_running=0` is, and then refuses every upload.
- **The count:** `Conversions._outputs_full` adds up the outputs of every conversion still held. Only a finished one holds any, until it expires or is deleted.
- **A new upload at or over the cap:** `Conversions.start` raises `HeldOutputsFull`.
  - The checks run in this order: one file at a time, then the full queue, then the cap.
  - The app answers with the "คิวเต็ม" page and status 503, as for a full queue.
  - The refusal is counted as `held outputs full`.
  - Nothing of the file is kept, as the error comes before anything is stored.
- **The waiting conversions too (the user's choice, 2026-10-25).**
  - **Why:** the spec reviewer showed that a cap checked only on upload still lets every conversion already queued start and add its outputs: 3 running and 20 waiting, up to about 1.15 GB on top of the cap. That is close to the 2 GB this ticket set out to prevent.
  - **What changed:** `_start_next` now starts nobody while the cap is reached. Forgetting outputs, by deletion or expiry, starts the next one waiting. Only the 3 running can add outputs on top, about 150 MB. The spec records the decision.
  - **The cost:** while the cap holds, a waiting visitor's place stays "รอคิว ลำดับที่ 1", until older outputs go within at most 10 minutes.
- **Tests** (`test_web_queue.py`, `test_web_settings.py`):
  - With a scripted sandbox whose every conversion gives back 600 bytes: at a cap of 1,200, the third upload gets "คิวเต็ม" and 503. After a deletion an upload is taken again. The statistics show `held outputs full: 1` and only the 3 finished conversions, so the refused file was never converted.
  - At a cap of 600 with one finished conversion, the "or more" boundary refuses an upload, and after 10 minutes on the fake clock one is taken.
  - With the held sandbox, one place and a cap of 1 byte, the second conversion waits after the first finishes. It starts once the first is deleted, or expires; both cases are tested.
  - The setting from the environment, its default, and the two values it cannot take.
- **Checks:**
  - **Windows, final code:** pytest (546 passed, 1 skipped: the launcher's Unix socket) and mypy.
  - **Linux image, final code:** mypy, and pytest (547 passed).
  - **Linux image,** with the code mounted, on the first version:
    - mypy;
    - pytest: 545 passed;
    - `pytest -m ocr`: 15;
    - `pytest -m slow`: 1;
    - the harness: OCR CER 0.0072, unchanged;
    - the CLI;
    - the sandbox entry point.
- **Code review** (two axes):
  - **Spec:** the headroom, above. Also left as it is: when both the queue and the cap are full, the refusal counts as `queue full`. The visitor sees the same page either way.
  - **Standards, fixed:**
    - a named helper for the bytes held;
    - the class docstring's order;
    - the settings test's comment;
    - a long test line;
    - a test helper's docstring.
  - **Standards, kept:** the two `except` branches in `app.py`, which differ only in the statistics kind, as the kinds must stay apart.
