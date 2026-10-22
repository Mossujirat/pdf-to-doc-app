# 14: Staging on gmt, gVisor, and the deploy gate

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The service runs on `gmt` in a staging copy that only the tailnet can reach. A deploy script, adapted from Chatbot's, refuses to deploy to production until staging has run the same server files and passed a smoke test through the real path:

Tailscale → web app → launcher → gVisor sandbox

This ticket also installs gVisor on `gmt`, and settles the spec's open questions about the server.

**Needs the user:**
- **Approve each change to `gmt`** before it is made. The steps are summarised first, as the user's working rules require.
- **Do the Tailscale admin steps:**
  - create a tag and a tagged auth key
  - set the policy
  - enable HTTPS

**Blocked by:** 08, 09, 10

**Status:** ready-for-agent

**Branch:** `chore/web-deploy`

**gVisor**
- [ ] Written steps install gVisor on `gmt`, register its runtime with Docker, and check it. The steps reload Docker without a restart where that is possible, so that Chatbot is not interrupted. Chatbot's containers keep the normal runtime.
- [ ] PaddleOCR is shown to run under gVisor, and its speed is recorded. If it cannot run, the fallback in ADR 0004 is taken, and the ADR is updated.

**Staging**
- [ ] Staging is its own compose project on `gmt`, beside Chatbot's. It shares nothing with Chatbot.
- [ ] It has its own Tailscale node, `pdf-staging`, reachable only inside the tailnet through Tailscale Serve, never through Funnel.
- [ ] It uses Turnstile in test mode.
- [ ] Its sandbox containers are named for staging.
- [ ] The clone is pulled with a read-only deploy key while the repo is private. Secrets live only in the server's env file.

**Deploy script**
- [ ] `staging <branch>` deploys to staging and runs the smoke test. It records the commit as passed only when every check passes.
- [ ] A production deploy refuses unless staging passed the same server-used files. An override exists for emergencies.

**Smoke test** (runs against staging over the tailnet)
- [ ] A synthetic corpus file with OCR pages goes through the real path. Both outputs' text is checked against reference text.
- [ ] A forged client-IP header does not change whose allowance is charged. This settles which header Tailscale sets, and the setting from ticket 08 is updated.
- [ ] The sandbox containers were started with every restriction in ticket 09.
- [ ] Seconds per OCR page on `gmt` are recorded.
- [ ] Whether sandboxes on efficiency cores are much slower is recorded, with a decision on pinning them to performance cores.
- [ ] On a real phone, through staging: picking a file, dropping one where the browser allows it, and the copy button all work. Carried over from ticket 11, whose local server a phone cannot reach.

**Docs**
- [ ] A deploy guide in the repo, after Chatbot's, covers setup, deploys, staging, gVisor and Tailscale.

## Comments

**2026-10-21, from ticket 09**
- The launcher speaks the Engine API version 1.44, so `gmt`'s Docker must be 25.0 or later.
- On `gmt`, the launcher needs the group that owns `/var/run/docker.sock` (`group_add`). The local compose gives it root's, which owns Docker Desktop's.
- `compose.local.yaml` is a starting point for staging's and production's compose files. Each sets `PDF_TO_DOC_ENVIRONMENT`, and leaves the launcher's runtime at its default, `runsc`.
- See whether Docker's stats work under gVisor. Without them, the launcher logs "sandbox statistics unavailable", and the memory and CPU statistics stay empty.
- Sandboxes inherit compose's labels from the image (ticket 09's comments). Confirm that a deploy leaves running sandboxes alone.

**2026-10-21, from ticket 10**
- Copy the log rotation from `compose.local.yaml` (`x-logging`) into staging's and production's compose files.
- The counters are read with `docker compose exec web pdf-to-doc-statistics`. Do not publish port 8001: it listens on the container's own loopback address, which nothing else reaches. Keep it so: do not give the Tailscale container the web app's network namespace (`network_mode: service:web`), or it would share that loopback address.
- `/health` answers `ok`, for an uptime check later.
