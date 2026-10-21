# 08: Client IP and the daily page allowance

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** Each client IP address may convert 500 pages a day. The day runs from midnight to midnight, Bangkok time, and every page of the source file counts. The pages are charged when the sandbox reports the page count. A source file that would go over the allowance is stopped before any page is read, with a message that says how many pages remain and when the allowance resets.

The client IP comes only from the header that the Tailscale proxy sets, and only on requests that arrive from the Tailscale container. A visitor cannot change it with a header of their own. IP addresses are held in memory only.

**Blocked by:** 03

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Client IP**
- [ ] Two settings say where the address comes from:
  - the trusted proxy's address
  - the header it sets

  Staging (ticket 14) confirms which header Tailscale uses.
- [ ] The header is read only on requests from the trusted proxy. Any other request uses its connection's address.
- [ ] No other header is read, `CF-Connecting-IP` included.

**Allowance**
- [ ] 500 pages a day by default, as a setting, counting every page. The day resets at midnight, Bangkok time.
- [ ] Pages are charged at the "opened" event. If they would go over the allowance, the sandbox is told to stop, and the visitor sees the pages remaining and the reset time.
- [ ] The pages are given back when a conversion fails, or hits the time limit, for the service's own reasons. They are not given back when the visitor cancels.
- [ ] IP addresses are held in memory only, never logged, and lost on restart.

**Tests**
- [ ] HTTP tests with a fake clock:
  - from an untrusted peer, forged headers change nothing
  - through the trusted proxy, two clients are counted apart
  - the allowance runs out, and the message shows what remains
  - the allowance resets the next day
  - a failed conversion gives its pages back
