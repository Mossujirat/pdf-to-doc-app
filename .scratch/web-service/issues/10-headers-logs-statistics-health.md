# 10: Security headers, logs, statistics and health

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** Every page and download carries the security and privacy headers, and requests that change state check where they came from. The logs could be published without harm: no content, file names, IP addresses or conversion links. The operator can see how the service is used through counters on a listener bound to the server's own loopback address, which Tailscale never reaches. A health address answers whether the service is up.

**Blocked by:** 04, 07, 08, 09

**Status:** ready-for-agent

**Branch:** `feat/web-sandbox`

**Headers**
- [ ] The Content-Security-Policy allows this site only, plus Cloudflare's Turnstile origin for its script and frame. There is no inline script.
- [ ] Conversion pages and downloads send:
  - `Referrer-Policy: no-referrer`
  - `Cache-Control: no-store`
  - `X-Robots-Tag: noindex`
- [ ] Upload, cancel and delete refuse a request whose `Origin` is not the site's.

**Logs**
- [ ] The web server's access log is off.
- [ ] The app logs only:
  - start and stop
  - refusals, by kind
  - failures, by error type and place, without messages
- [ ] Docker log rotation is set in compose.

**Statistics**
- [ ] Counters, since start and for today:
  - conversions by outcome
  - pages by kind
  - durations and queue waits
  - queue length, now and at its highest
  - refusals by kind
  - bot-check failures
  - allowance refusals
  - timeouts and failures
  - the highest sandbox memory and CPU time
- [ ] They are served on a second listener bound to loopback, never on the public one.

**Health**
- [ ] A health address says whether the service is up, with no details.

**Tests**
- [ ] The headers on each kind of page and download.
- [ ] A request with a wrong `Origin` is refused.
- [ ] The logs of a full conversion, a refusal and a failure hold no fragment of the document, its file name, the client IP or the link. This reuses the privacy tests' fragment search.
- [ ] After scripted conversions, the counters are right, and the public app does not serve the statistics.

## Comments

**2026-10-21, from ticket 09**
- `Ended.usage` carries each sandbox's highest memory use and its CPU time, from the launcher. It is `None` when Docker's stats said nothing, as for a sandbox shorter than one sample.
- The launcher logs only `started`, `stopped`, how many leftover sandboxes it removed, a failed conversion by error type, and stats it could not read, by error type. httpx's line for each request to Docker is turned off.
