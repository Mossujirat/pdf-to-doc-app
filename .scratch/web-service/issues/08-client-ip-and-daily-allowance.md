# 08: Client IP and the daily page allowance

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** Each client IP address may convert 500 pages a day. The day runs from midnight to midnight, Bangkok time, and every page of the source file counts. The pages are charged when the sandbox reports the page count. A source file that would go over the allowance is stopped before any page is read, with a message that says how many pages remain and when the allowance resets.

The client IP comes only from the header that the Tailscale proxy sets, and only on requests that arrive from the Tailscale container. A visitor cannot change it with a header of their own. IP addresses are held in memory only.

**Blocked by:** 03

**Status:** done

**Branch:** `feat/web-core`

**Client IP**
- [x] Two settings say where the address comes from:
  - the trusted proxy's address
  - the header it sets

  Staging (ticket 14) confirms which header Tailscale uses.
- [x] The header is read only on requests from the trusted proxy. Any other request uses its connection's address.
- [x] No other header is read, `CF-Connecting-IP` included.

**Allowance**
- [x] 500 pages a day by default, as a setting, counting every page. The day resets at midnight, Bangkok time.
- [x] Pages are charged at the "opened" event. If they would go over the allowance, the sandbox is told to stop, and the visitor sees the pages remaining and the reset time.
- [x] The pages are given back when a conversion fails, or hits the time limit, for the service's own reasons. They are not given back when the visitor cancels.
- [x] IP addresses are held in memory only, never logged, and lost on restart.

**Tests**
- [x] HTTP tests with a fake clock:
  - from an untrusted peer, forged headers change nothing
  - through the trusted proxy, two clients are counted apart
  - the allowance runs out, and the message shows what remains
  - the allowance resets the next day
  - a failed conversion gives its pages back

## Comments

**2026-10-21, decided with the user: an IPv6 client counts as its /64 block.**
- A home or phone is usually given a whole /64. Counting each address would let one visitor change address within it and get a fresh allowance each time.
- IPv4 counts by its address, as before.
- An IPv4 address carried in IPv6 (`::ffff:a.b.c.d`) counts as that IPv4 address.
- Staging (ticket 14) will show whether Funnel passes IPv6 addresses on at all.

**2026-10-21, how it works**

**The client's address** is worked out in `web/client_ip.py`, from the settings `trusted_proxy` and `client_ip_header`.
- **Which value:** on a request whose connection comes from the trusted proxy, the address is the header's last value: the last of its lines, and the last of the comma-separated values on that line. A proxy adds the address it saw after anything the visitor sent, whether it appends to the visitor's line or adds a line of its own. Tests cover both, and the case where `CF-Connecting-IP` is sent through the proxy.
- **If the header is missing or not an address,** the request counts against the proxy's own address. Every such request then shares one allowance: stricter, never looser.
- **Every other request** counts against its connection's address.
- **Production refuses to start** (`Misconfigured`, now in `settings.py` for the bot check too) without both settings. Without them, every visitor would share the proxy's one allowance.

**uvicorn reads `X-Forwarded-For` itself by default,** from local connections. `pdf-to-doc-web` turns that off (`proxy_headers=False`), and ticket 09 now says the deployed server must too.

**The allowance** lives in `web/allowance.py`, in memory.
- Bangkok's day uses a fixed UTC+7 offset, as Thailand keeps no daylight saving time. That needs no time zone database, which Windows lacks.
- A new day starts the counts afresh and drops the old ones.
- The app takes a wall clock beside its monotonic one, as ticket 05 noted. `tests/fake_clock.py` moves both.

**Charging:**
- A conversion's pages are charged when its "opened" event comes. A second "opened" is malformed.
- If the pages do not fit, the conversion ends in a new state, "over_allowance". Leaving the loop that reads the sandbox closes its stream, which stops it before any page is read. That holds even if stopping it raises.
- The page says how many pages the file has, how many are left today, and that the count starts again at midnight Bangkok time.
- The spec's states table now has this state. Ticket 06's note asked that this stop not reuse "refused".

**Giving back:**
- A failure, a time-out included, gives the pages back.
- A cancel and a finished conversion keep them charged.
- Pages charged on a day that has passed are not given back to the new day.
- When a conversion ends, its client address and its charge are dropped from it. Addresses are never logged; a test searches the log for them.

**2026-10-21, after code review**

**Fixed:**
- Only the first header line was read, so a visitor's own `X-Forwarded-For` line could win over the proxy's.
- Production could start without the proxy settings.
- A failure while stopping for the allowance showed "failed" instead of what was left.
- Tests were added for `CF-Connecting-IP` through the proxy, and for a time-out giving its pages back.
- Names were tidied: `client_ip`, which is `None` once the conversion ends. The address rule moved into a module of its own. The tests' upload helpers take headers per request, and one helper, `converted`, now serves the message and allowance tests.
