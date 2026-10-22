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
- [x] Written steps install gVisor on `gmt`, register its runtime with Docker, and check it. The steps reload Docker without a restart where that is possible, so that Chatbot is not interrupted. Chatbot's containers keep the normal runtime.
- [x] PaddleOCR is shown to run under gVisor, and its speed is recorded. If it cannot run, the fallback in ADR 0004 is taken, and the ADR is updated.

**Staging**
- [x] Staging is its own compose project on `gmt`, beside Chatbot's. It shares nothing with Chatbot.
- [x] It has its own Tailscale node, `pdf-staging`, reachable only inside the tailnet through Tailscale Serve, never through Funnel.
- [x] It uses Turnstile in test mode.
- [x] Its sandbox containers are named for staging.
- [x] The clone is pulled with a read-only deploy key while the repo is private. Secrets live only in the server's env file.

**Deploy script**
- [x] `staging <branch>` deploys to staging and runs the smoke test. It records the commit as passed only when every check passes.
- [x] A production deploy refuses unless staging passed the same server-used files. An override exists for emergencies.

**Smoke test** (runs against staging over the tailnet)
- [x] A synthetic corpus file with OCR pages goes through the real path. Both outputs' text is checked against reference text.
- [x] A forged client-IP header does not change whose allowance is charged. This settles which header Tailscale sets, and the setting from ticket 08 is updated.
- [x] The sandbox containers were started with every restriction in ticket 09.
- [x] Seconds per OCR page on `gmt` are recorded.
- [x] Whether sandboxes on efficiency cores are much slower is recorded, with a decision on pinning them to performance cores.
- [ ] On a real phone, through staging: picking a file, dropping one where the browser allows it, and the copy button all work. Carried over from ticket 11, whose local server a phone cannot reach.

**Docs**
- [x] A deploy guide in the repo, after Chatbot's, covers setup, deploys, staging, gVisor and Tailscale.

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

**2026-10-22, from ticket 13**
- **Build with the commit:** build the image with `--build-arg BUILD_COMMIT=$(git rev-parse HEAD)`. In compose, use `build.args`, giving the web app and the launcher the same value, since they share one image.
- **Production refuses without it:** the public service will not start without that commit. Staging should pass it too, so that its footer's source code link is checked.
- **Smoke test:** `/source-code` redirects to `github.com/Mossujirat/pdf-to-doc-app/tree/<commit>`. Check that the commit is the one deployed. The repository must be public by launch, or the link fails.
- **Tailscale's logs:** the privacy page says no log holds a visitor's IP address. That is checked for the web app and the launcher, not for the Tailscale container. Check what `tailscaled` logs, and what it uploads to Tailscale by default, and turn off whatever holds client addresses. If anything cannot be turned off, change the privacy page in the same ticket.

**2026-10-22, staging runs and passes its smoke test**

**What was built:**
- **Compose files:** `compose.yaml` is production, and `compose.staging.yaml` adds staging. Each runs three containers: Tailscale, the web app and the launcher.
- **Scripts:**
  - `scripts/install-gvisor.sh`: gVisor `release-20261005.0`, with its checksum pinned
  - `scripts/deploy.sh`: after Chatbot's
  - `scripts/smoke_test.py`
- **Docs:** `docs/DEPLOY.md`.
- **Pinned images:** `tailscale/tailscale:v1.102.5` (2026-09-24), by digest.

**Done on gmt and in Tailscale, each step approved first:**
- **gVisor:** installed by the user with the script. `runsc` sits beside `runc` and `nvidia`, and the default is still `runc`. Docker was reloaded, and Chatbot's five containers kept running.
- **Folders and code:** `/srv/pdf-to-doc` and `/srv/pdf-to-doc-staging` were made, owned by `gmt`.
  - A deploy key of its own, `~/.ssh/pdf-to-doc_deploy`, read-only on GitHub, sits behind the host alias `github.com-pdf-to-doc`. Chatbot's key is untouched.
  - Staging is cloned. The production folder is still empty.
- **Tailscale policy:** in the user's tailnet:
  - the source of the allow-all rule is narrowed to `autogroup:member`
  - `tagOwners` holds `tag:pdf-staging` and `tag:pdf-prod`
  - `nodeAttrs` gives `funnel` to `tag:pdf-prod` alone
  - tests deny both tags the user's PC

  HTTPS certificates are on. Staging's auth key was one-off and tagged. A first key showed in a screenshot, so it was revoked and replaced.

**Found on the way:**
- **The tailnet:**
  - **The surprise:** `gmt` is *shared in* from Chatbot's tailnet (`taila2e363`). The user's own tailnet is `tail46a117.ts.net`.
  - **The consequence:** the service's nodes join the user's tailnet, so the addresses are `pdf.tail46a117.ts.net` and `pdf-staging.tail46a117.ts.net`.
  - **What changed:** the spec, ticket 15 and every file were updated.
  - **The benefit:** Chatbot and this service no longer share a tailnet.
- **Port 80:**
  - **The symptom:** the staging node joined, got its certificate, and went offline five minutes later, with every map poll timing out.
  - **The cause:** `gmt`'s network cuts long-lived connections on port 80, where tailscaled starts. A connection to port 80 sat in `FIN-WAIT-1`, and `gmt`'s own tailscaled was already on 443.
  - **The fix:** `TS_FORCE_NOISE_443`, Tailscale's own switch for such networks (`control/controlhttp/client.go`). The node has stayed online since.
- **The fixed address:** the web app, started first, was handed `.2`, the Tailscale container's fixed address. Docker now hands out the lower half of each subnet (`ip_range`), and the Tailscale container is `.254`. A staging deploy takes staging down before starting it, so the network always takes the files' settings.
- **DNS on the deploying machine:** the user's PC did not use Tailscale's DNS (`CorpDNS: false`), so it could not find `pdf-staging`. It was turned on with `tailscale set --accept-dns=true`. The guide now says the deploying machine needs it.
- **The smoke test's DOCX check:** read back, the summary that opens the DOCX output is page 1's first paragraph, so page 1 scored a CER of 2.1. The smoke test now drops it, as `tests/docx_reader.py` does. The converter was right.

**The smoke test at `a8eee89`:** 32 of 32 checks passed:
- **The path:** Tailscale → web app → launcher → gVisor, with `/health`, the bot check and the source code link.
- **The sandbox:** `runsc`, under every restriction in `sandbox_config()`, as `converter` with no network.
- **The outputs:** both outputs of `mixed-text-and-scan` and `stamped-scans`, with a CER of 0 and no broken text on every page.
- **The forged header:** three uploads each forged `X-Forwarded-For`, and the file over the allowance found 56 of 60 pages left. Tailscale sets `X-Forwarded-For` to the visitor's own address, replacing any the visitor sent (`ipn/ipnlocal/serve.go`, v1.102.5).
- **Leftovers:** no sandbox was left behind.

Staging's record is `refs/staging/passed` = `a8eee89`.

**Measured on gmt:**
- **OCR:** 1.5 to 3.1 seconds a page through the whole path.
- **Cores:** a whole two-page scanned file took 3.4 seconds in gVisor, models included, on performance cores (0–3) and efficiency cores (8–11) alike (3.41–3.49 s against 3.40–3.62 s).
  - **Decision:** sandboxes are not pinned.
- **Sandbox use:** at most about 550 MB of memory, and 5.5 seconds of CPU.
- **Statistics:** Docker's statistics work under gVisor.

**The production gate:** `scripts/deploy.sh` refused production. `origin/main` differs from what staging passed with in 13 server files. It stopped before touching gmt, and `/srv/pdf-to-doc` is still empty.

**Tailscale's logs:**
- **Production's node:** it uploads no log (`--no-logs-no-support`), and keeps none (`logging: driver: none`). In v1.102.5 tailscaled logs a client's address only on error paths.
- **Staging's node:** it keeps rotated logs. It has no visitors.

**Left:** the phone check through staging, which needs the user's phone in the tailnet.

**2026-10-22, after code review**

**The smoke test could pass without checking. Fixed:**
- **DOCX as written:** the DOCX output was checked only as read back, which repairs Thai text first. Its paragraphs are now also checked for broken text as written.
- **Missing references:** a corpus folder without reference text checked nothing. It now fails.
- **ssh:** a failed ssh read as "no sandbox left behind". Any failed ssh now stops the test with FAIL.
- **Old sandboxes:** a stopped sandbox from an earlier run could be the one inspected. Only running sandboxes are inspected now, and only while the conversion runs.
- **Waiting for staging:** `/health` is retried after any answer that is not `ok`.
- **More of ticket 09's restrictions:** the sandbox is also checked for:
  - stdin opened once
  - no mount
  - an environment that is the image's own, plus the launcher's `PDF_TO_DOC_OCR_THREADS`

  An earlier check by variable names caught the Python image's own `GPG_KEY`, the public fingerprint of Python's release key, and was replaced.

**The deploy script. Fixed:**
- **A staging deploy:**
  - It refuses unless this machine has the deployed commit checked out, unchanged. The smoke test runs from this checkout, and its checks must be the commit's.
  - `gmt` checks out exactly that commit.
- **A production deploy:** it refuses a target behind what production runs. That would otherwise build newer code labelled with an older commit. A rollback is a revert on `main`.
- **Commands without the commit:** `BUILD_COMMIT` may be left out of compose commands, so the guide's log and counter commands work. A build without it makes an image the public service refuses.
- **File modes:** both scripts are executable in git.

**Corrected:**
- **`compose.staging.yaml`'s comment:** it now describes the policy that was applied.
- **The guide:**
  - the Markdown exemption is the top level's
  - it records `gmt`'s Docker (29.8.2) and kernel (7.0), and where the docker group's ID 983 comes from (`getent group docker`)
  - it says what a deploy does to running sandboxes: the new launcher removes them, and `docker compose ps` does not list them
- **The spec:** its open questions about the server are now answered.
- **ADR 0005:** it names `X-Forwarded-For` (replaced, not appended), and the operator's own tailnet.
- **Ticket 15:** it now holds the checks only production can make:
  - two clients through Funnel, since staging's test cannot tell a missing header from a replaced one
  - IPv6
  - Funnel's bandwidth with a file near 50 MB

**Kept:** the remote steps in `deploy.sh` repeat a `/health` loop and a `dc()` helper, as Chatbot's do. Each heredoc runs on `gmt` on its own.

**The smoke test after the review:** all 35 checks passed at `5578a38`, and staging's record is `refs/staging/passed` = `5578a38`.
- **On the way:** the remote `docker image inspect` had split on the space in `{{json .Config.Env}}`. ssh hands the server's shell one line, so each argument is now quoted (`shlex.join`).
