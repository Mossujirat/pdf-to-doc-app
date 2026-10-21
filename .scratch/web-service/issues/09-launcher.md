# 09: Launcher: each conversion in its own locked-down container

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** The production sandbox (ADR 0004). The launcher is a small service, the only part with access to Docker. It starts one throwaway container per conversion, from the image it was deployed with, under every restriction in the spec, and streams the source file in and the events and outputs out. Stopping a container is how a conversion is cancelled.

A compose file for local development runs the web app and the launcher on Docker Desktop with the normal runtime, so that the whole service runs as it will on `gmt`, except for gVisor and Tailscale.

**Blocked by:** 02, 03

**Status:** done

**Branch:** `feat/web-sandbox`

**Launcher**
- [x] The launcher listens on a Unix socket, on a volume shared only with the web app. It offers two operations:
  - run: stream a source file in, and stream events and outputs back
  - cancel
- [x] It reaches Docker through the mounted Docker socket, and has no network of its own.
- [x] It starts nothing but the sandbox, from the image it was deployed with.
- [x] Every sandbox container gets:
  - the runtime named by a setting: gVisor in production, the normal runtime locally
  - no network
  - a read-only root, with a small in-memory scratch area
  - the image's non-root user
  - no capabilities, and no-new-privileges
  - 4 CPUs, 2 GB of memory and no swap
  - a process limit
  - no volumes, and no environment beyond the OCR thread count, which is set to the CPU limit
  - stdin attached
- [x] Containers are named for their environment, production or staging.
- [x] Each container is removed when its conversion ends, however it ends. At start, the launcher removes any leftover containers of its own environment.
- [x] At most 3 sandboxes run at once, as a backstop to the web app's queue.
- [x] The time limit is a setting, 30 minutes by default. When it is reached, the container is stopped and the conversion is reported as timed out.
- [x] Output from a sandbox is untrusted:
  - event lines are capped in length and checked against their schema
  - outputs are capped at 50 MB in total
  - anything malformed ends the conversion as failed
- [x] It records each sandbox's highest memory use and its CPU time, for the statistics in ticket 10.

**Web app**
- [x] A setting selects the launcher as the web app's sandbox.
- [x] The web app's server runs with uvicorn's proxy headers off (`proxy_headers=False`), as `pdf-to-doc-web` does: only the app's own rule may read the client's address from a header (ticket 08).

**Local development**
- [x] A compose file runs the web app and the launcher on Docker Desktop, with the normal runtime and Turnstile in test mode.
- [x] The README and CLAUDE.md say how to start it.

**Tests**
- [x] The launcher's handling of streams, limits and caps is tested with a stand-in for Docker. The stand-in runs the entry point as a subprocess, or a scripted process that misbehaves: too much output, malformed events, never ending.
- [x] By hand on Docker Desktop:
  - convert a corpus file through the local compose
  - inspect a running sandbox, and confirm every restriction above

  Record the results in this ticket's comments.

## Comments

**2026-10-21, how it is built**

**The code** is in `src/pdf_to_doc/web/`:
- `launcher.py`: the launcher (`Launcher`), its socket (`serve`, `serve_connection`), the web app's side of that socket (`LauncherSandbox`), and `pdf-to-doc-launcher`
- `docker.py`: sandboxes in Docker (`DockerEngine`), and what each container is created with (`sandbox_config`)
- `settings.py`: `from_environment` and `LauncherSettings`

**The launcher's socket.** Each side sends frames: a line with the frame's kind and its payload's length in bytes, then the payload, as the sandbox frames its parts.
- The web app opens one connection per conversion, and sends `run` with the source file.
- The launcher sends `event` for each event line, then `stdout`, then `ended`: JSON with the exit code, `timed_out` and the usage.
- A conversion that fails in the launcher ends without `ended`.
- **Cancelling:** the web app sends `cancel`, then waits until the launcher closes the connection, which it does once the sandbox has been removed. It waits 60 seconds at most. Anything else the web app sends, or its closing the connection before `ended`, cancels too, so a web app that stops leaves no sandbox running.
- **A launcher that does not listen yet** is waited for, 30 seconds at most. It listens only some seconds after it starts, and Python 3.13 removes the socket file as the old launcher stops, so a file sent during a restart would otherwise fail.

**Docker** is reached through its socket, with the Engine API version 1.44. Docker 25.0 was the first to speak it, and Docker 29 still does (Docker's version table, read 2026-10-21).
- **The image** is the launcher's own. It inspects its own container, whose host name is its ID, and creates every sandbox from that image's ID. A later build that retags the image changes nothing until the launcher is recreated.
- **stdin** is the attach request's connection, which the Engine API hijacks. It is half-closed once the source file has been sent, and `StdinOnce` then closes the container's stdin. Tried by hand before it was built on.
- **Every restriction** is in `sandbox_config`, and `tests/test_docker.py` guards them. Beyond the ticket's:
  - `LogConfig: none`. Docker would otherwise keep what the sandbox writes, the outputs included, in a log file.
  - `IpcMode: none`.
  - The user is named, `converter`, so that a changed image fails to start rather than run as root.
- **Measured, to set two limits:** a conversion with an OCR page, at 4 OCR threads, had 24 processes and threads at most, so the limit is 128. Its `/tmp` stayed empty, so the scratch area is 64 MB.
- **Leftovers:** each sandbox is labelled `pdf-to-doc.sandbox=<environment>`. The launcher removes its environment's as it starts, and again as it stops.
- **Usage** comes from Docker's stats, about once a second: the highest of `usage - inactive_file`, as `docker stats` counts memory on cgroup v2, and the CPU time. `Ended.usage` carries them, for ticket 10. Whether the stats work under gVisor is for ticket 14 to see. Without them, the usage is `None` and the launcher logs a warning.

**Untrusted output** is checked in the launcher, before anything reaches the web app, and again in the web app:
- each event line against its schema, and at most 1 MB, also before the line has ended
- the outputs, at most 50 MB in all, as they come
- anything else ends the conversion as failed, and its sandbox is stopped at once

**Settings.** `from_environment` reads `PDF_TO_DOC_<NAME>` for each setting.
- An empty value counts as unset, as compose passes a variable that its own environment lacks.
- A value a setting cannot take stops the service. The message names the variable, never the value, which could be a secret.
- The launcher refuses to start without `PDF_TO_DOC_ENVIRONMENT` (`production`, `staging` or `local`). With a default, staging's launcher could take production's sandboxes for its leftovers.
- The launcher's runtime defaults to `runsc`. The local compose sets `runc`.
- The web app has a new setting, `sandbox`: `launcher` by default, or `local`. Production refuses `local`, and also a cookie that is not Secure.

**`pdf-to-doc-web`** now takes its settings from the environment, as its container does. `--dev` gives the local development settings it had before. A deployed server that lacks a setting refuses to start, instead of running as in development.

**The local compose** is `compose.local.yaml`.
- The web app and the launcher run from one image, built locally. `pull_policy: build` keeps an image of the same name from coming from a registry.
- The launcher has no network, Docker's socket, and root's group, which owns Docker Desktop's socket. On `gmt` it will be the `docker` group's ID (ticket 14).
- The web app mounts the socket's volume read-only. The image makes `/run/pdf-to-doc`, owned by `converter`, so a new volume takes that owner.
- Both containers have a read-only root.

**2026-10-21, checked by hand on Docker Desktop 29.6.2**

Through the local compose, with synthetic corpus files only:
- **Converting**, timed from the upload to the end:

  | File | Seconds |
  |---|---|
  | `mixed-text-and-scan.pdf` | 11.5 |
  | `stamped-scans.pdf` | 12.5 |
  | `multi-page.pdf`, no OCR | 4.4 |

  Each conversion with OCR pays the 5–6 second model load. Both downloads came back: Markdown 495 bytes and DOCX 36,916 bytes for the first file.
- **A running sandbox, inspected:**
  - runtime `runc` and network `none`, with only `lo` inside
  - the root read-only (`touch /written` gave "Read-only file system"), and `/tmp` a 64 MB tmpfs with `noexec,nosuid,nodev`
  - uid and gid 1000, every capability set empty, and `NoNewPrivs: 1`
  - the cgroup's `cpu.max 400000 100000` (4 CPUs), `memory.max 2147483648`, `memory.swap.max 0` and `pids.max 128`
  - no mounts or binds, and `LogConfig: none`
  - in its environment beyond the image's, `PDF_TO_DOC_OCR_THREADS=4` only. `GPG_KEY` comes from the Python base image: the public ID of Python's release key.
- **Removed** when finished, when cancelled (within a second), and when timed out. With `PDF_TO_DOC_TIME_LIMIT=3`, the page said that the conversion took too long and was stopped.
- **Leftovers:** a sandbox left by an earlier launcher was removed when the next one started.
- **A restart:** a file sent right after `docker compose restart launcher` finished.
- **CI:** the checks, run in the image as `ci.yml` runs them, all pass, the launcher's Unix-socket test included.

**Found by hand, and fixed:**
- The web app closes the connection once it has `ended`. The launcher took that for a cancel, and interrupted the sandbox's removal, so finished sandboxes stayed. The stand-in for Docker removed at once, so the tests had missed it. Its removal now takes a moment and counts only once done, which reproduced the bug before the fix.
- A file sent while the launcher restarted failed. The web app now waits for the launcher, as above.

**2026-10-21, after code review**

**Fixed:**
- Docker can create a container without a restriction its server cannot apply, such as the swap limit, and say so only in the create response's `Warnings`. The launcher now refuses to run such a sandbox (`RestrictionDropped`), and logs Docker's warnings.
- A conversion cancelled while Docker created its container could leave that container. Its removal is now arranged by name before it is created.
- A sandbox could repeat its `failure` event for the whole time limit, and the web app logged each one. A failure is now the conversion's last event, like a summary or a refusal.
- `PDF_TO_DOC_TIME_LIMIT=inf`, `nan`, `0` or a negative number turned the limit off or broke every conversion. A number of seconds must now be finite and more than none. A digit `int` cannot read, such as `³`, raised an error that quoted it; it is now refused like any other value.
- Docker's stats that came without memory use gave no warning. The launcher now logs one, which ticket 14 will look for under gVisor.
- Tidied: the `ended` frame is written and read through one model, the container class is `_Container`, the environment is typed, an unused socket parameter went, and `test_settings.py` became `test_web_settings.py`.

**Kept:**
- The sandbox keeps the image's own environment (`PATH`, `PDF_TO_DOC_MODELS` and the like). It needs them, and none is a secret. The launcher adds only the OCR thread count.
- `docker.py`'s frame reading and stats have no automated test. Their seam was left to the hand checks, as agreed before the tests were written, and they were run again by hand after these fixes.
- Beyond the ticket, and kept on purpose: `LogConfig: none`, `IpcMode: none`, read-only roots in compose, leftovers removed on stopping too, the `local` environment, `--dev`, and production refusing a cookie that is not Secure (the spec requires Secure).

**Noted, not done:**
- Each sandbox also carries the image's compose labels, such as `com.docker.compose.service: web`, which compose adds to the images it builds. `docker compose ps` does not count sandboxes as its own. Ticket 14 can confirm on `gmt` that a deploy leaves running sandboxes alone.
- The JavaScript has still not run in a browser (ticket 11).
