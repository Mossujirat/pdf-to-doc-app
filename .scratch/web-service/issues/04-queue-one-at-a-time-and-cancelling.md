# 04: Queue, one file at a time, and cancelling

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** At most 3 conversions run at once and up to 20 wait their turn. A waiting conversion's page shows its place in the queue. A file that arrives when 20 are waiting is refused with "queue full, try again shortly". A browser with a conversion waiting or running cannot start another. A visitor can cancel a conversion while it waits or runs. The tab's title shows the state, so that a visitor in another tab notices when it is done.

**Blocked by:** 03

**Status:** done

**Branch:** `feat/web-core`

**Queue**
- [x] The queue is first in, first out, held in memory.
- [x] The limits are settings: 3 running and 20 waiting by default.
- [x] A waiting conversion's page shows its place, updated as the queue moves.
- [x] A file that would be the 21st waiting gets the "queue full" message, and nothing of it is kept.

**One at a time**
- [x] A browser whose token has a conversion waiting or running gets a message instead of a second conversion. A different browser is not affected.

**Cancelling**
- [x] A waiting conversion that is cancelled leaves the queue.
- [x] A running conversion that is cancelled asks the sandbox to stop. Its place goes to the next one waiting.
- [x] The page says that the conversion was cancelled.

**Tab title**
- [x] The title shows waiting, converting (with the OCR page) or done.

**Tests**
- [x] HTTP tests with a scripted fake sandbox that lets each test decide when a conversion starts and ends:
  - a fourth conversion waits in first place
  - the 24th upload is refused as queue full
  - a second upload from the same browser is refused, and one from another browser is accepted
  - cancelling a waiting conversion and a running one frees its place, and the next conversion starts

## Comments

**2026-10-21, how it works**

**The queue** lives in `Conversions`. Waiting conversions hold their source file's bytes, in the order they came. Running ones hold the task that reads their sandbox.

**A place is freed when the conversion's sandbox has stopped,** not when the visitor presses cancel. That keeps the number of live sandboxes at 3 or below, which the launcher (ticket 09) also enforces. While a cancelled sandbox stops, it still holds its place.

**A cancel never turns into a failure.** If stopping the sandbox raises an error, the conversion still reads as cancelled. Ticket 08 relies on that: pages charged for a cancelled conversion are not given back, but those of a failed one are.

**Refusals:**
- When the queue is full, the upload gets 503 and "คิวเต็ม".
- When the browser already has a conversion, it gets 409. The page says so and links to that conversion. A conversion counts only while it waits or runs, so a browser may send another file as soon as it cancels.
- Either way, the file is read and dropped.

**Cancelling:**
- The page's cancel button is a form that posts to `/conversions/{id}/cancel`. It needs no script.
- The cancel route has no `Origin` check yet. Ticket 10 adds one to upload, cancel and delete.

**The state JSON** now has `ongoing`, so `app.js` keeps asking without knowing the state names.
- The tab's title is the status text: "รอคิว ลำดับที่ 2", "OCR หน้า 3/10", "แปลงเสร็จแล้ว".
- The script updates the title each time it asks.
- The status shows in the page's heading.

**Settings:** `Settings` in `web/settings.py` holds `max_running`, `max_waiting` and `secure_cookies`, and `create_app` takes it. Nothing reads them from the environment yet. That comes with the deployment settings (tickets 09 and 14), and later tickets add their settings here.

**When the app stops,** it cancels every running conversion, so that no sandbox outlives it. Without this, the test client's teardown logged an error for conversions still held. With `pdf-to-doc-web`, Ctrl+C would otherwise leave subprocesses running.

**By hand with the local sandbox on Windows:**
- During OCR, a conversion has two processes: the venv's `python.exe`, and the interpreter it starts.
- Cancelling left neither, checked at once and after 1 and 2 seconds.
- Through the real server, a conversion cancelled during OCR read "ยกเลิกการแปลงแล้ว", and the same browser's next file started at once.

**2026-10-21, after code review**

**Fixed:**
- A cancelled conversion counted as converting until its sandbox had stopped, so the browser got 409 meanwhile. The check now looks at the state.
- If stopping the sandbox failed, a cancel turned into "failed".
- The queue-full test would have passed even if the refused file had been queued. It now ends all 23 conversions and checks that the next file starts in 24th place.
- The 409 page told the visitor to cancel the earlier file, but gave no link to it.
- The test helpers were tidied:
  - the held sandbox's conversions are `held.started`
  - each sent file's token and link travel together
  - one polling helper serves every wait

**Kept:** the queue tests check what the held sandbox recorded, such as which file started and whether one was told to stop. The spec's Testing Decisions prefer what a visitor sees. This ticket asks for "asks the sandbox to stop" and "nothing of it is kept", which only the sandbox can show.
