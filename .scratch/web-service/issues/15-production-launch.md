# 15: Production launch

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The service goes live at `https://pdf.tail46a117.ts.net`. It runs on its own Tailscale node, `pdf`, with Funnel on port 443 (ADR 0005), and the launch checklist in the spec is completed. Most of the steps are the user's: the Tailscale admin console, Cloudflare's Turnstile settings, and making the repo public.

**Blocked by:** 12, 13, 14, converter ticket 11 (uncertain text, in `.scratch/converter-engine/`)

**Status:** ready-for-human

**Branch:** `chore/web-deploy`

**Production**
- [x] The production compose project on `gmt` runs:
  - the web app
  - the launcher, with the gVisor runtime (or the fallback recorded in ticket 14)
  - the Tailscale node `pdf`, with Funnel on 443
- [x] The tailnet policy gives the node's tag the `funnel` attribute, and grants it no access to any other device.
- [x] Turnstile's production keys are in the server's env file. The widget's hostname list holds `pdf.tail46a117.ts.net`, and it was created with the widget mode "Invisible": the page cannot choose the mode, the dashboard does (ticket 07).
- [x] The first production deploy goes through the deploy gate from ticket 14.

**Launch checklist**
- [x] Converter ticket 11 (uncertain text) is merged, and the web shows the uncertain count.
- [x] The git history is checked for anything confidential: excerpts of the sample contracts, names, ID numbers. The repo is then made public.
- [x] Through Funnel, a forged client-IP header changes nothing.
- [ ] The privacy page and the "how it works" section are reviewed by the user.
- [x] The README describes the web service, and links to it.
- [x] On a real phone, through Funnel: picking a file, dropping one where the browser allows it, and the copy button all work (from ticket 14).

## Comments

**2026-10-22, from ticket 14**
- **Already in place:**
  - `compose.yaml` is production: the web app, the launcher (gVisor), and the node `pdf` with Funnel on 443
  - the tailnet policy gives `tag:pdf-prod` the `funnel` attribute, and reaches no device
  - `/srv/pdf-to-doc` exists, empty, and `scripts/deploy.sh` with its gate is ready

  What is left: clone into `/srv/pdf-to-doc`; make the production auth key (`tag:pdf-prod`); write `.env` with it and Turnstile's production keys; merge to `main`; deploy. The steps are in `docs/DEPLOY.md`.
- **The client-IP header with two clients:** staging's smoke test showed that a forged `X-Forwarded-For` changes nothing. It cannot show that Tailscale sends the header at all: without it, every visitor would be charged to the proxy's address and share one allowance.
  - Through Funnel, convert a file from the PC, then from a phone on mobile data, with Wi-Fi off.
  - Each must see its own allowance. A file over what is left shows the count, so each count must start from the full allowance.
- **IPv6:** ticket 08 left whether Funnel passes IPv6 addresses on. Staging uses Serve, so it cannot tell. Look at it with the two clients above.
- **Bandwidth:** Funnel's bandwidth limits are not published. Send a file near 50 MB through Funnel once.

**2026-10-22, launch**
- **Live:** production runs `9a0087c` (`main`), deployed through the gate after staging passed the same server files at `969d17f`. Funnel reaches it from the internet, and uploads pass the bot check with the production keys.
- **Git history:** checked before the repo went public:
  - no sample PDF was ever committed
  - no ID or phone numbers
  - only the operator's email, which is published on purpose

  Two names in a converter test were not found in the sample contracts. They were still replaced with plainly made-up ones (`fab626e`); the old ones stay in history.
- **The client-IP header through Funnel:**
  - **The test:** a temporary capture in the web container's network namespace (removed afterwards) watched one request sent from the PC through Funnel's public address, carrying `X-Forwarded-For: 203.0.113.99`.
  - **What the web app received:** one `X-Forwarded-For` line, holding only the PC's public address, the same one Cloudflare saw. Tailscale replaces the header and does not append to it.

  So Tailscale does send each visitor's own address, and the two-client concern above is settled for IPv4. IPv6 is still unseen: the request went to Funnel's IPv4 address.
- **Phone:** the user converted a file on a phone over mobile data, through Funnel, and it worked.
- **The watchdog (a workaround):**
  - **Why:** soon after the first deploy, the node `pdf` went offline. Its connection to Tailscale's control server had stalled on `gmt`'s network, and restarting the container fixed it.
  - **What it does:** `scripts/watch-tailscale.sh`, run by cron every 5 minutes, restarts that container when the node is offline at two checks in a row.
  - **Tested on `gmt`:** with a stand-in `docker`, it did nothing while online, waited after one offline check, restarted once after two, and left a stopped container alone. Against the real node it found it online and wrote nothing.
  - **The cause:** it lies in `gmt`'s network, outside this project, so the watchdog stays a workaround.
  - **Setting it up and stopping it:** `docs/DEPLOY.md`, section 2, step 7.
