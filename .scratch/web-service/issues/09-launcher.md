# 09: Launcher: each conversion in its own locked-down container

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The production sandbox (ADR 0004). The launcher is a small service, the only part with access to Docker. It starts one throwaway container per conversion, from the image it was deployed with, under every restriction in the spec, and streams the source file in and the events and outputs out. Stopping a container is how a conversion is cancelled.

A compose file for local development runs the web app and the launcher on Docker Desktop with the normal runtime, so that the whole service runs as it will on `gmt`, except for gVisor and Tailscale.

**Blocked by:** 02, 03

**Status:** ready-for-agent

**Branch:** `feat/web-sandbox`

**Launcher**
- [ ] The launcher listens on a Unix socket, on a volume shared only with the web app. It offers two operations:
  - run: stream a source file in, and stream events and outputs back
  - cancel
- [ ] It reaches Docker through the mounted Docker socket, and has no network of its own.
- [ ] It starts nothing but the sandbox, from the image it was deployed with.
- [ ] Every sandbox container gets:
  - the runtime named by a setting: gVisor in production, the normal runtime locally
  - no network
  - a read-only root, with a small in-memory scratch area
  - the image's non-root user
  - no capabilities, and no-new-privileges
  - 4 CPUs, 2 GB of memory and no swap
  - a process limit
  - no volumes, and no environment beyond the OCR thread count, which is set to the CPU limit
  - stdin attached
- [ ] Containers are named for their environment, production or staging.
- [ ] Each container is removed when its conversion ends, however it ends. At start, the launcher removes any leftover containers of its own environment.
- [ ] At most 3 sandboxes run at once, as a backstop to the web app's queue.
- [ ] The time limit is a setting, 30 minutes by default. When it is reached, the container is stopped and the conversion is reported as timed out.
- [ ] Output from a sandbox is untrusted:
  - event lines are capped in length and checked against their schema
  - outputs are capped at 50 MB in total
  - anything malformed ends the conversion as failed
- [ ] It records each sandbox's highest memory use and its CPU time, for the statistics in ticket 10.

**Web app**
- [ ] A setting selects the launcher as the web app's sandbox.

**Local development**
- [ ] A compose file runs the web app and the launcher on Docker Desktop, with the normal runtime and Turnstile in test mode.
- [ ] The README and CLAUDE.md say how to start it.

**Tests**
- [ ] The launcher's handling of streams, limits and caps is tested with a stand-in for Docker. The stand-in runs the entry point as a subprocess, or a scripted process that misbehaves: too much output, malformed events, never ending.
- [ ] By hand on Docker Desktop:
  - convert a corpus file through the local compose
  - inspect a running sandbox, and confirm every restriction above

  Record the results in this ticket's comments.
