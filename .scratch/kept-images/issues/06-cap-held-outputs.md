# 06: Cap the outputs the web app holds

**Parent:** Kept images spec, in this feature folder.

**What to build:** The web app stops taking new files while the outputs it holds total 1 GB or more.
- **Why:** with kept images a DOCX can reach 50 MB, and outputs are held in memory for 10 minutes. Without a cap, a burst of large conversions could hold about 2 GB. The web container has no memory limit, on a server it shares with Chatbot.
- **What the visitor sees:** "คิวเต็ม" until older outputs expire or are deleted.
- Decided with the user on 2026-10-24.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Branch:** `feat/kept-images-web`

**The cap**
- [ ] A new setting, `max_held_outputs`, in bytes, 1 GB by default, set through `PDF_TO_DOC_MAX_HELD_OUTPUTS`. It is read like the other number settings.
- [ ] It counts the outputs that ended conversions still hold. When they total the cap or more, a new upload gets the "คิวเต็ม" page, with the same status as a full queue. Nothing of the refused file is kept.
- [ ] Running conversions may add up to their own outputs on top of the cap. That is the headroom.
- [ ] Once outputs expire or are deleted, uploads are taken again.
- [ ] The statistics count these refusals under a kind of their own, apart from a full queue.

**Tests**
- [ ] With a small cap and a fake sandbox that returns large outputs, check that:
  - an upload is refused once the cap is reached;
  - it is taken again after a deletion, or after the outputs expire on the fake clock.
- [ ] The refusal is counted under its own kind.
- [ ] The setting is read from the environment, and a value it cannot take stops the service from starting.
- [ ] pytest and mypy pass.
