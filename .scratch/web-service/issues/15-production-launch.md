# 15: Production launch

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The service goes live at `https://pdf.taila2e363.ts.net`. It runs on its own Tailscale node, `pdf`, with Funnel on port 443 (ADR 0005), and the launch checklist in the spec is completed. Most of the steps are the user's: the Tailscale admin console, Cloudflare's Turnstile settings, and making the repo public.

**Blocked by:** 12, 13, 14, converter ticket 11 (uncertain text, in `.scratch/converter-engine/`)

**Status:** ready-for-human

**Branch:** `chore/web-deploy`

**Production**
- [ ] The production compose project on `gmt` runs:
  - the web app
  - the launcher, with the gVisor runtime (or the fallback recorded in ticket 14)
  - the Tailscale node `pdf`, with Funnel on 443
- [ ] The tailnet policy gives the node's tag the `funnel` attribute, and grants it no access to any other device.
- [ ] Turnstile's production keys are in the server's env file. The widget's hostname list holds `pdf.taila2e363.ts.net`.
- [ ] The first production deploy goes through the deploy gate from ticket 14.

**Launch checklist**
- [ ] Converter ticket 11 (uncertain text) is merged, and the web shows the uncertain count.
- [ ] The git history is checked for anything confidential: excerpts of the sample contracts, names, ID numbers. The repo is then made public.
- [ ] Through Funnel, a forged client-IP header changes nothing.
- [ ] The privacy page and the "how it works" section are reviewed by the user.
- [ ] The README describes the web service, and links to it.
