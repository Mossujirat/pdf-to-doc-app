# 10: Security headers, logs, statistics and health

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** Every page and download carries the security and privacy headers, and requests that change state check where they came from. The logs could be published without harm: no content, file names, IP addresses or conversion links. The operator can see how the service is used through counters on a listener bound to the server's own loopback address, which Tailscale never reaches. A health address answers whether the service is up.

**Blocked by:** 04, 07, 08, 09

**Status:** done

**Branch:** `feat/web-sandbox`

**Headers**
- [x] The Content-Security-Policy allows this site only, plus Cloudflare's Turnstile origin for its script and frame. There is no inline script.
- [x] Conversion pages and downloads send:
  - `Referrer-Policy`: `no-referrer` on downloads, `same-origin` on pages (see Comments)
  - `Cache-Control: no-store`
  - `X-Robots-Tag: noindex`
- [x] Upload, cancel and delete refuse a request whose `Origin` is not the site's.

**Logs**
- [x] The web server's access log is off.
- [x] The app logs only:
  - start and stop
  - refusals, by kind
  - failures, by error type and place, without messages
- [x] Docker log rotation is set in compose.

**Statistics**
- [x] Counters, since start and for today:
  - conversions by outcome
  - pages by kind
  - durations and queue waits
  - queue length, now and at its highest
  - refusals by kind
  - bot-check failures
  - allowance refusals
  - timeouts and failures
  - the highest sandbox memory and CPU time
- [x] They are served on a second listener bound to loopback, never on the public one.

**Health**
- [x] A health address says whether the service is up, with no details.

**Tests**
- [x] The headers on each kind of page and download.
- [x] A request with a wrong `Origin` is refused.
- [x] The logs of a full conversion, a refusal and a failure hold no fragment of the document, its file name, the client IP or the link. This reuses the privacy tests' fragment search.
- [x] After scripted conversions, the counters are right, and the public app does not serve the statistics.

## Comments

**2026-10-21, from ticket 09**
- `Ended.usage` carries each sandbox's highest memory use and its CPU time, from the launcher. It is `None` when Docker's stats said nothing, as for a sandbox shorter than one sample.
- The launcher logs only `started`, `stopped`, how many leftover sandboxes it removed, a failed conversion by error type, and stats it could not read, by error type. httpx's line for each request to Docker is turned off.

**2026-10-21, decided with the user: pages send `Referrer-Policy: same-origin`, downloads `no-referrer`**
- The Fetch standard (read 2026-10-21) says that for a request that is neither GET nor HEAD, a `no-referrer` policy sets the `Origin` header to `null`. Every cancel and delete is a form on a conversion page, so the `Origin` check would refuse them all.
- With `same-origin`, no other site learns a page's address either. Only this site does, and it logs no request.
- The spec's security section now says so.

**2026-10-21, how it works**

**Headers.** One middleware in `create_app` sets them on every response, unless a route has set its own:
- `Content-Security-Policy: default-src 'self'; script-src 'self' https://challenges.cloudflare.com; frame-src https://challenges.cloudflare.com; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`. Turnstile asks for its origin in `script-src` and `frame-src` (Cloudflare's docs, read 2026-10-21). Whether its widget needs anything more shows only in a real browser (ticket 11).
- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy: same-origin`. A download sets `no-referrer` itself.
- Under `/conversions/`, on pages, state, downloads and the "not found" page alike: `Cache-Control: no-store` and `X-Robots-Tag: noindex`. The home page may be cached and indexed.

**Where a request came from.** Upload, cancel and delete need an `Origin` whose host is the site's. That is `hostname` when it is set, and otherwise the `Host` the request was sent to, as in local development. The scheme is not compared, because a proxy ends TLS before the app. Anything else, a missing origin or `null` included, gets 403 with a page of its own, before the upload is read.

**Health:** `GET /health` answers `ok`.

**Statistics** live in `web/statistics.py`, in memory, since the start and for Bangkok's day:
- conversions by how they ended (`finished`, `refused`, `failed`, `timed_out`, `cancelled`, `over_allowance`), the last being the allowance refusals
- pages of finished conversions, by kind
- refusals by kind: the upload's own (`another site`, `too large`, `not an upload`, `one at a time`, `queue full`) and the sandbox's (`UnsupportedFormat` and the rest)
- bot-check failures, by verdict
- durations from leaving the queue to ending, and queue waits: count, total and longest
- the longest queue, and the queue now
- the highest sandbox memory and CPU time, from `Ended.usage`

`statistics_app` serves them as JSON. `pdf-to-doc-web` runs it on a second uvicorn server bound to `127.0.0.1:8001` inside the web app's container. Only the first server takes the signals, and the second stops after it. Nothing outside the container reaches that address, the Tailscale container included. `pdf-to-doc-statistics` prints the counters there, as `docker compose exec web pdf-to-doc-statistics`.

**Logs:**
- **What is logged:** `started`, `stopped`, each refusal by kind (`refused: <kind>`), bot-check refusals by verdict, and failures by error type and place:
  - `conversion failed in the sandbox: <type>`
  - `conversion failed: <type>`
  - `failed: <type> at <route>`, where the route is its template, such as `/conversions/{identifier}`
- **Unexpected errors:** the middleware catches any error from a route, logs only its type and route, and answers 500 with a page of its own. Before, uvicorn logged a traceback with the error's message.
- **Not logged:** uvicorn's access log stays off. httpx's line for each request to Cloudflare is turned off.
- **The tests:** `tests/test_web_logs.py` searches the log of a finished conversion, a refusal and a failure for fragments of the document, with the privacy tests' search, now in `tests/fragments.py`. It also searches for the file name, the client's address and the link.
- **Log rotation:** set in `compose.local.yaml` (json-file, 3 files of 10 MB). The server's compose files come with ticket 14.

**2026-10-21, after code review**

**Fixed:**
- The answer to `POST /conversions` (each upload refusal page, and the redirect) lacked `no-store` and `noindex`. Every path under `/conversions` now carries them.
- A conversion over the allowance was counted, but not logged. It is now a refusal like any other: `refused: over the allowance`.
- Today's longest queue started each day at none, even with conversions waiting. It now starts from the queue as it is.
- The origin check was repeated in each route. The middleware now refuses any request but GET and HEAD that comes from elsewhere.
- Tidied: `Conversion.outcome` tells a time-out from a failure for the page and the counters alike, the run time is `run_times`, and the second server is `_SecondServer`.

**Decided by the implementer, for the user to overrule:** the spec said the counters listen on "the server's own loopback address". They listen on the web app's container's own loopback address instead, and the operator reads them over SSH with `docker compose exec web pdf-to-doc-statistics`. Publishing the port on the server's loopback would also expose it to every container on the compose network, the Tailscale container included. This holds only while the Tailscale container keeps a network namespace of its own (ticket 14).

**Kept:** refusal kinds are plain strings, the web's own (`too large`) beside the sandbox's (`UnsupportedFormat`). They are labels for the operator, and the sandbox's come from its validated event.

**2026-10-21, checked by hand in the image**
`pdf-to-doc-web --dev` ran in a container with a read-only root:
- `/health` gave `ok`.
- `/statistics` on the public port gave 404.
- `pdf-to-doc-statistics` inside the container printed the counters.
- The home page carried the CSP, `nosniff` and `same-origin`.
- `docker stop` ended both servers in 2 seconds, with exit code 0.
