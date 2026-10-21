# 04: Queue, one file at a time, and cancelling

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** At most 3 conversions run at once and up to 20 wait their turn. A waiting conversion's page shows its place in the queue. A file that arrives when 20 are waiting is refused with "queue full, try again shortly". A browser with a conversion waiting or running cannot start another. A visitor can cancel a conversion while it waits or runs. The tab's title shows the state, so that a visitor in another tab notices when it is done.

**Blocked by:** 03

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Queue**
- [ ] The queue is first in, first out, held in memory.
- [ ] The limits are settings: 3 running and 20 waiting by default.
- [ ] A waiting conversion's page shows its place, updated as the queue moves.
- [ ] A file that would be the 21st waiting gets the "queue full" message, and nothing of it is kept.

**One at a time**
- [ ] A browser whose token has a conversion waiting or running gets a message instead of a second conversion. A different browser is not affected.

**Cancelling**
- [ ] A waiting conversion that is cancelled leaves the queue.
- [ ] A running conversion that is cancelled asks the sandbox to stop. Its place goes to the next one waiting.
- [ ] The page says that the conversion was cancelled.

**Tab title**
- [ ] The title shows waiting, converting (with the OCR page) or done.

**Tests**
- [ ] HTTP tests with a scripted fake sandbox that lets each test decide when a conversion starts and ends:
  - a fourth conversion waits in first place
  - the 24th upload is refused as queue full
  - a second upload from the same browser is refused, and one from another browser is accepted
  - cancelling a waiting conversion and a running one frees its place, and the next conversion starts
