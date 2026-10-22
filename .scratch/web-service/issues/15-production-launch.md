# 15: Production launch

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The service goes live at `https://pdf.tail46a117.ts.net`. It runs on its own Tailscale node, `pdf`, with Funnel on port 443 (ADR 0005), and the launch checklist in the spec is completed. Most of the steps are the user's: the Tailscale admin console, Cloudflare's Turnstile settings, and making the repo public.

**Blocked by:** 12, 13, 14, converter ticket 11 (uncertain text, in `.scratch/converter-engine/`)

**Status:** ready-for-human

**Branch:** `chore/web-deploy`

**Production**
- [ ] The production compose project on `gmt` runs:
  - the web app
  - the launcher, with the gVisor runtime (or the fallback recorded in ticket 14)
  - the Tailscale node `pdf`, with Funnel on 443
- [ ] The tailnet policy gives the node's tag the `funnel` attribute, and grants it no access to any other device.
- [ ] Turnstile's production keys are in the server's env file. The widget's hostname list holds `pdf.tail46a117.ts.net`, and it was created with the widget mode "Invisible": the page cannot choose the mode, the dashboard does (ticket 07).
- [ ] The first production deploy goes through the deploy gate from ticket 14.

**Launch checklist**
- [ ] Converter ticket 11 (uncertain text) is merged, and the web shows the uncertain count.
- [ ] The git history is checked for anything confidential: excerpts of the sample contracts, names, ID numbers. The repo is then made public.
- [ ] Through Funnel, a forged client-IP header changes nothing.
- [ ] The privacy page and the "how it works" section are reviewed by the user.
- [ ] The README describes the web service, and links to it.
- [ ] On a real phone, through Funnel: picking a file, dropping one where the browser allows it, and the copy button all work (from ticket 14).

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
