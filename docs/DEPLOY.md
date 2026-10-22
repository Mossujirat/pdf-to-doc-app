# Deploying the web service

How the web service runs on `gmt`, how a change reaches it, and what never to do. After Chatbot's `docs/DEPLOY.md`, whose server it shares. ADR 0004 (sandboxes) and ADR 0005 (Tailscale Funnel) explain the choices.

## 1. Where it runs

| What | Where |
|---|---|
| Server | `gmt`, reached as `ssh gmt` (100.99.33.19) over Tailscale only. Chatbot runs on it too. |
| Tailnet | `tail46a117.ts.net`, the operator's own, on Tailscale's free plan. `gmt` belongs to Chatbot's tailnet (`gmt.taila2e363.ts.net`) and is shared into this one; this service's nodes are containers on `gmt` that join this one. |
| Production | `/srv/pdf-to-doc`, a clone of `main`. Compose project `pdf-to-doc`, from `compose.yaml`. |
| Staging | `/srv/pdf-to-doc-staging`, a second clone, at the commit last deployed to it. Compose project `pdf-to-doc-staging`, from `compose.yaml` and `compose.staging.yaml`. |
| Public address | `https://pdf.tail46a117.ts.net`, the production node `pdf` through Tailscale Funnel |
| Staging address | `https://pdf-staging.tail46a117.ts.net`, the node `pdf-staging` through Tailscale Serve: inside the tailnet only |
| Secrets | `.env` in each folder, on `gmt` only (`.env.example` lists them) |
| Sandboxes | one container per conversion, in gVisor (`runsc`), started by the launcher; named `pdf-to-doc-sandbox-<environment>-…` |

**Each environment has three containers:**
- `tailscale`: the node, and the only way in
- `web`: the web app, on port 8000 of a network it shares with the Tailscale container alone
- `launcher`: no network, and Docker's socket

**What production and staging share:** nothing but `gmt`'s Docker. Nothing is shared with Chatbot either: no network, no volume, no secret.

## 2. Setting up for the first time

The steps that need `sudo` run on `gmt` as its owner, who types the password. Each step leaves Chatbot running.

**What `gmt` must have, as checked on 2026-10-22:**
- **Docker 25.0 or later:** the launcher speaks Engine API 1.44. `gmt` runs 29.8.2.
- **Linux 5.6 or later:** for gVisor. `gmt` runs 7.0.
- **The docker group's ID in `compose.yaml`:** `group_add: ["983"]`, so that the launcher may use Docker's socket. `getent group docker` gives it; check it on a new server.

### 1. Install gVisor

This downloads a pinned release, checks it against the checksum in the script, and registers `runsc` beside `runc` and `nvidia`. Docker is reloaded, not restarted.

```bash
scp scripts/install-gvisor.sh gmt:/tmp/ && ssh -t gmt sudo bash /tmp/install-gvisor.sh
```

### 2. Make the two folders

```bash
ssh -t gmt sudo install -d -o gmt -g gmt /srv/pdf-to-doc /srv/pdf-to-doc-staging
```

### 3. Give gmt a read-only deploy key

GitHub takes a deploy key for one repository only, so this is a key of its own, beside Chatbot's.

1. Make the key:

   ```bash
   ssh gmt 'ssh-keygen -t ed25519 -N "" -C "gmt pdf-to-doc deploy" -f ~/.ssh/pdf-to-doc_deploy'
   ```

2. Add this to `~/.ssh/config` on `gmt`:

   ```
   Host github.com-pdf-to-doc
       HostName github.com
       User git
       IdentityFile ~/.ssh/pdf-to-doc_deploy
       IdentitiesOnly yes
   ```

3. Add `~/.ssh/pdf-to-doc_deploy.pub` to the repository's deploy keys, read-only.
4. Clone into both folders:

   ```bash
   ssh gmt 'git clone git@github.com-pdf-to-doc:Mossujirat/pdf-to-doc-app.git /srv/pdf-to-doc-staging'
   ```

   Do the same with `/srv/pdf-to-doc`.

### 4. In Tailscale's admin console

1. **DNS:** MagicDNS and HTTPS certificates must be on. MagicDNS was on already; HTTPS was turned on for this service on 2026-10-22.
2. **Access controls:** add the tags, Funnel for production alone, and tests that keep the tagged nodes away from the operator's PC:

   ```json
   "tagOwners": {
     "tag:pdf-staging": ["autogroup:admin"],
     "tag:pdf-prod":    ["autogroup:admin"]
   },
   "nodeAttrs": [
     {"target": ["tag:pdf-prod"], "attr": ["funnel"]}
   ],
   "tests": [
     {"src": "tag:pdf-staging", "deny": ["100.114.200.81:22", "100.114.200.81:445"]},
     {"src": "tag:pdf-prod",    "deny": ["100.114.200.81:22", "100.114.200.81:445"]}
   ]
   ```

   **No rule may let a `tag:pdf-*` node reach anything:**
   - A rule from `"*"` to `"*"`, as in the default policy, lets every tagged node reach every device. Narrow its source to `autogroup:member`, as was done: people's devices still reach everything, staging among it.
   - The tests make the console refuse to save a policy that lets either tag reach the operator's PC, `switchoff`.
3. **Auth keys:** make one auth key for each node:
   - one-off, pre-approved, not ephemeral
   - tagged `tag:pdf-staging` or `tag:pdf-prod`

   Tagged nodes do not expire, and each node keeps its identity in its volume.

### 5. Write each folder's .env

Write it on `gmt`, with `chmod 600`, from `.env.example`:
- **Staging:** `TS_AUTHKEY` alone.
- **Production:** its own `TS_AUTHKEY`, and the Turnstile widget's keys for `pdf.tail46a117.ts.net`.

### 6. Deploy staging, then production

Follow section 3.

## 3. Deploying

Push first: `gmt` pulls from GitHub.

**The machine that deploys** must be in the tailnet, with Tailscale's "Use Tailscale DNS settings" on (`tailscale set --accept-dns=true`). The smoke test reaches staging by its name, which only Tailscale's DNS knows.

```bash
scripts/deploy.sh staging <branch>    # build and start staging at origin/<branch>, then run the smoke test
scripts/deploy.sh check <A> <B>       # whether two commits differ in files the server uses (changes nothing)
scripts/deploy.sh                     # production: origin/main, if staging passed with the same server files
scripts/deploy.sh staging --stop      # stop staging
```

**A staging deploy:**
1. Refuses unless this machine has the same commit checked out, with no changes. The smoke test runs from here, so it must be that commit's.
2. Checks out the commit on `gmt`, builds the image with it, and takes staging down and up again. The web app's counts in memory start empty.
3. Runs `scripts/smoke_test.py` from this machine, over the tailnet.
4. Records the commit on `gmt` as `refs/staging/passed`, only if every check passed. It clears that record first, so a deploy that fails leaves none.

**A production deploy:**
- It refuses unless the files the server uses are those staging last passed with. The files that do not count are:
  - `docs/`, `.scratch/`, `.claude/`, `.impeccable/`, `.github/`, `tests/`, `corpus/`, `scripts/`
  - Markdown files at the top level
- `DEPLOY_WITHOUT_STAGING=1 scripts/deploy.sh` skips that check, for hotfixes only.
- It refuses a commit behind what production runs. A rollback is a revert on `main`, deployed like any change.

**Running conversions:** a deploy recreates the launcher, which cancels the conversions running. Their pages say that they ended, and nothing of them is left.
- **Sandboxes left behind:** the new launcher removes any sandbox of its environment as it starts.
- **Compose:** sandboxes carry the image's compose labels, but `docker compose ps` does not list them as its own (ticket 09). Whether or not compose touches them, the launcher removes them.

## 4. The smoke test

`uv run python scripts/smoke_test.py <site> --commit <sha> --ssh gmt` goes through the real path:

```text
Tailscale → web app → launcher → gVisor sandbox
```

**It checks:**
- `/health`, the bot check on the home page, and that `/source-code` opens the commit deployed
- two corpus files, `mixed-text-and-scan` and `stamped-scans`: both outputs, Markdown and DOCX, against their reference text, with no broken text and a CER of 1% at most
- one sandbox, inspected while it runs: every restriction the launcher asks for (`sandbox_config()`), with the runtime `runsc`, the user `converter` and no network
- that each upload forges a different `X-Forwarded-For`, yet a file over the allowance finds it reduced by what this visitor had used. Staging's allowance is 60 pages a day, for this.
- that no sandbox is left afterwards

It prints the seconds an OCR page takes.

**What staging measured on gmt (2026-10-22):**
- **OCR speed:** 1.5 to 3.1 seconds a page in gVisor, through the whole path.
- **Converting a whole file:** two scanned pages took 3.4 seconds, the models' loading included. That was the same whether the sandbox ran on performance cores (0–3) or efficiency cores (8–11), so sandboxes are not pinned to either.
- **Sandbox use:** at most about 550 MB of memory. Docker's statistics work under gVisor.

## 5. Running it

- **Logs:** `ssh gmt 'cd /srv/pdf-to-doc && docker compose -p pdf-to-doc logs --tail 100 web launcher'`. They never hold a document's content, a file name, an address or a link.
  - Production's Tailscale container keeps no log at all, and uploads none to Tailscale (`--no-logs-no-support`). Its error lines can hold a visitor's address.
- **Counters:** `ssh gmt 'cd /srv/pdf-to-doc && docker compose -p pdf-to-doc exec web pdf-to-doc-statistics'`.
- **Health:** `/health` answers `ok`.

## 6. Never

- Never publish a port. The Tailscale container is the only way in.
- Never run `docker compose` in these folders without `-p` and the files that `scripts/deploy.sh` names.
- Never edit the code on `gmt`. `git status` there stays clean.
- Never make `runsc` Docker's default runtime. Chatbot's containers keep theirs.
- Never give a `tag:pdf-*` node a way to reach other devices, or staging a Funnel.

## 7. When something goes wrong

- **A node joins, then shows offline minutes later, with "map response long-poll timed out" in its log:** `gmt`'s network cuts long-lived connections on port 80, where tailscaled starts. `TS_FORCE_NOISE_443` in `compose.yaml` keeps it on port 443, as `gmt`'s own tailscaled does. Check that the setting is still there.
- **"Address already in use" as the Tailscale container starts:** another container took its fixed address. Docker hands out only the lower half of each subnet (`ip_range`), so the fixed `.254` stays free. Check that both are still there.
- **The smoke test cannot find staging (`getaddrinfo failed`):** this machine is not using Tailscale's DNS. See section 3.
