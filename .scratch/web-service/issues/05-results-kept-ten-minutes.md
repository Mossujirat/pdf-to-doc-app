# 05: Results kept for 10 minutes, deleted on request

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A finished conversion's outputs are kept for 10 minutes after it finishes (ADR 0001). The result page shows the time left and a button that deletes the outputs at once. Downloading does not delete them, so a failed download can be retried and both formats fetched. Once a conversion has expired, been deleted, or been lost to a restart, its link shows a page that explains this and offers to convert again.

**Blocked by:** 03

**Status:** done

**Branch:** `feat/web-core`

**Keeping and deleting**
- [x] Outputs are dropped 10 minutes after the conversion finishes, and their memory is released. The 10 minutes are a setting.
- [x] The result page shows the time left.
- [x] "Delete now" drops the outputs at once. Later requests for them get the expired page.
- [x] A download can be repeated within the 10 minutes.
- [x] Refused, failed and cancelled conversions are forgotten after the same 10 minutes. Nothing of them lingers.

**Unknown links**
- [x] One page serves a link that has expired, been deleted, been lost to a restart, or never existed, and a link opened by another browser. It says the conversion may have expired, been deleted or been lost to a restart, and offers to convert again. It reveals nothing about which case applies.

**Tests**
- [x] HTTP tests with a fake clock:
  - outputs download before 10 minutes, and the expired page appears after
  - "delete now" works
  - a download repeats within the window
  - a fresh app instance, standing in for a restart, shows the expired page for an old link

## Comments

**2026-10-21, how it works**

**Every conversion records when it ended,** however it ended, on the app's clock. `Settings.keep_for` (600 seconds) after that, the whole conversion is forgotten: its record, its summary and its outputs.

**Forgetting happens two ways:**
- On every request that reads or starts a conversion, so no request can reach a conversion past its time.
- In a loop started with the app, every 15 seconds, so that outputs leave memory even when no request comes. Outputs can therefore stay in memory up to 15 seconds past the 10 minutes, never longer.
- The loop has no test: through HTTP, the per-request forgetting hides whether it ran.

**"ลบเดี๋ยวนี้"** is a form that posts to `/conversions/{id}/delete`. It forgets the conversion and answers with a page saying the outputs were deleted. Any later request for the link gets the expired page. As with cancel, the `Origin` check comes with ticket 10.

**The time left** is shown as whole minutes, rounded up, when the page loads. It does not count down while the page stays open; ticket 11 can make it.

**The expired page** is the app's one 404 page, for every case in the ticket and for any unknown address. It says how long results are kept.

**The clock** is `time.monotonic`, injected as `Clock` so that tests can use `tests/fake_clock.py`. It tells no date. Ticket 08's daily allowance resets at midnight Bangkok time, so it needs a clock that does, injected beside this one or as a fake that moves both.

**A fix found on the way.** A sandbox whose stream ended without `Ended` left its conversion "running" for ever, so it never ended or expired. `_convert` now ends every conversion it ran, and ends it as failed unless the sandbox said otherwise. Every way a conversion ends now goes through `Conversions._end`, which ticket 08 can use to give pages back on failure but not on cancel.

**2026-10-21, after code review**

**Fixed:**
- "Delete now" sent the visitor straight to the "not found" page. It now shows that the outputs were deleted.
- The delete test posted without checking that the result page has the button.
- `kept_for` (seconds left) beside `keep_for` (the whole time) became `time_left`, which `forget_expired` uses too.
- `_outcome` no longer sets the outputs; `_end` does, and only for a finished conversion.

**Left for later:**
- The countdown (ticket 11).
- A test for the background loop.
