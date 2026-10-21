# 05: Results kept for 10 minutes, deleted on request

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A finished conversion's outputs are kept for 10 minutes after it finishes (ADR 0001). The result page shows the time left and a button that deletes the outputs at once. Downloading does not delete them, so a failed download can be retried and both formats fetched. Once a conversion has expired, been deleted, or been lost to a restart, its link shows a page that explains this and offers to convert again.

**Blocked by:** 03

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Keeping and deleting**
- [ ] Outputs are dropped 10 minutes after the conversion finishes, and their memory is released. The 10 minutes are a setting.
- [ ] The result page shows the time left.
- [ ] "Delete now" drops the outputs at once. Later requests for them get the expired page.
- [ ] A download can be repeated within the 10 minutes.
- [ ] Refused, failed and cancelled conversions are forgotten after the same 10 minutes. Nothing of them lingers.

**Unknown links**
- [ ] One page serves a link that has expired, been deleted, been lost to a restart, or never existed, and a link opened by another browser. It says the conversion may have expired, been deleted or been lost to a restart, and offers to convert again. It reveals nothing about which case applies.

**Tests**
- [ ] HTTP tests with a fake clock:
  - outputs download before 10 minutes, and the expired page appears after
  - "delete now" works
  - a download repeats within the window
  - a fresh app instance, standing in for a restart, shows the expired page for an old link
