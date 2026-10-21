# Web service MVP

Status: ready-for-agent

## Problem Statement

Thai office workers need the converter, but the command line and Docker are out of reach for most of them. They need a web page: drop a file in, get text out that reads exactly as the original, and paste it into an AI chat or edit it in Word.

The files they convert are often confidential: contracts, with names, ID numbers and addresses inside. Before they upload, they need to know where the file goes, who can see it, and when it is gone. Most free converters cannot answer this.

The service has costs of its own. It runs on `gmt`, the server that also runs the Chatbot project with its database and keys. Anyone on the internet can send it a file, and a crafted PDF could attack the parser. OCR is heavy, so one careless or hostile visitor could keep the CPU busy for everyone.

## Solution

A free Thai web page, with no sign-up, at `https://pdf.taila2e363.ts.net`.

**Converting a file**
- A visitor drops in a PDF or DOCX and passes an invisible bot check.
- The page shows the file's place in the queue, then its progress, such as "OCR หน้า 23/85".
- When it is done, the visitor gets:
  - the summary: pages read by OCR, uncertain spots, placeholders
  - a button that copies the Markdown, ready to paste into an AI chat
  - a DOCX download for Word
- Both outputs come from one conversion. A DOCX source gives Markdown only.

**Where the file goes**
- The file travels encrypted from the browser to our own server. Cloudflare is not on the path (ADR 0005).
- It is converted in a throwaway container that has no network and is destroyed when the conversion ends (ADR 0004).
- The outputs are kept for 10 minutes, or until the visitor deletes them. Only the browser that sent the file can open them.
- Nothing about the content is logged.
- The page explains all of this in plain Thai, with pictures that also show how the converter reads each page and how it catches broken text.

**Protecting the server**
- At most 3 conversions run at once, each limited to 4 CPUs and 2 GB.
- At most 20 more can wait in the queue.
- Each IP address may convert 500 pages a day.
- Each browser converts one file at a time.

**Launch.** The service launches as soon as it is ready and ticket 11 of the converter (uncertain text) is done. It does not wait for the quality gate (tickets 16–17), which goes on measuring the converter. The repo becomes public before launch, as the AGPL requires.

## User Stories

**Converting a file**
1. As a document user, I want to convert a file on a web page without installing anything or signing up, so that I can use the converter from any computer or phone.
2. As a document user, I want to drop a file onto the page or pick it with a button, so that starting is obvious.
3. As a document user, I want to use the page comfortably on my phone, so that I can convert a file someone sent me in a chat app.
4. As a document user, I want one conversion to give me both Markdown and DOCX, so that I never wait for OCR twice.
5. As a document user, I want a DOCX source converted to Markdown, so that Word files can go into an AI chat too.
6. As a document user, I want to see my place in the queue, so that I know why my conversion has not started.
7. As a document user, I want to see progress, such as which OCR page is being read out of how many, so that I know how long to wait.
8. As a document user, I want the conversion to carry on when I close the tab or switch to another app, so that I do not lose a 15-minute wait.
9. As a document user, I want to come back to the same link and find my result, so that I can leave the page while I wait.
10. As a document user, I want the browser tab's title to show when my conversion is done, so that I notice from another tab.
11. As a document user, I want to cancel a conversion that is waiting or running, so that I can stop a wrong file.

**The result**
12. As a document user, I want the summary on the result page (pages read by OCR, pages whose text layer was untrustworthy, uncertain spots, placeholders), so that I can judge how far to trust the output before using it.
13. As a document user, I want uncertain text marked inside the outputs, so that I know exactly which words to check.
14. As a document user, I want a button that copies the Markdown, so that I can paste it into an AI chat in one step.
15. As a document user, I want to download the Markdown file too, so that I can keep it or attach it.
16. As a document user, I want to download the DOCX, so that I can edit the content in Word.
17. As a document user, I want the downloads named after my source file, so that I can find them later.
18. As a document user, I want to download again if a download failed, within the 10 minutes, so that a dropped connection does not cost me the conversion.
19. As a document user, I want to see how long my result will be kept, so that I download it in time.
20. As a document user, I want a button that deletes my result at once, so that I do not have to trust the timer.
21. As a document user, I want a clear message when my result has expired, been deleted, or been lost to a restart, so that I know to convert again.

**Refusals and limits**
22. As a document user, I want a clear Thai message when my file is refused (legacy .doc, a locked Office file, not a PDF or DOCX, over 50 MB, over 150 pages, copying forbidden, or damaged), so that I know what to do instead.
23. As a document user, I want a clear message that password-protected PDFs are not supported yet, and that I should remove the password and try again, so that I am not stuck.
24. As a document user, I want a clear message when the queue is full, so that I know to try again shortly.
25. As a document user, I want a clear message when my daily page allowance is used up, saying when it resets, so that I know when I can continue.
26. As a document user, I want a clear message when I already have a file converting in this browser, so that I understand why a second one is not accepted.
27. As a document user, I want a clear message when a conversion takes too long and is stopped, or fails, so that I am never left waiting on a page that will not finish.
28. As a document user, I want the bot check to be invisible most of the time, so that it does not slow me down.

**Privacy and trust**
29. As a document user, I want to read in plain Thai where my file goes, who can see it and when it is deleted, so that I can decide whether to upload a confidential document.
30. As a document user, I want my file to reach the server without any third party able to read it on the way, so that a contract stays between me and the service.
31. As a document user, I want only my own browser to open my result, so that a link that leaks into a chat shows nothing.
32. As a document user, I want no analytics, tracking or advertising, so that using the service reveals nothing about me.
33. As a document user, I want the page to load nothing from other sites except the bot check, so that other companies do not learn that I visited.
34. As a document user, I want to know who runs the service and how to contact them about my personal data, so that I can exercise my rights under the PDPA.
35. As a document user, I want a link to the source code of the version that is running, so that I can check the claims, as the AGPL intends.
36. As a document user, I want to report a problem on GitHub, so that bugs get fixed.

**How it works**
37. As a document user, I want a section with pictures that explains how a conversion works, so that I understand why the output can be trusted.
38. As a document user, I want to see that each page is read either from the file's own text or with OCR, and why, so that I understand the OCR pages in the summary.
39. As a document user, I want to see how the converter catches text that is wrong inside the file (such as "กำร" for "การ"), so that I understand why some text pages are read with OCR.
40. As a document user, I want to see what the Thai repair fixes, so that I know what problems other converters leave in.
41. As a document user, I want to see that signatures, stamps and images become placeholders instead of invented text, so that I understand the brackets in the output.
42. As a document user, I want to see where my file travels and when it is deleted, in the same pictures, so that privacy is part of how it works rather than small print.

**Running the service**
43. As the operator, I want each conversion to run in its own throwaway gVisor container with no network, so that a crafted PDF cannot reach Chatbot, the server, or other visitors' files.
44. As the operator, I want each conversion limited to 4 CPUs and 2 GB, and at most 3 at once, so that Chatbot always keeps the rest of the server.
45. As the operator, I want OCR to use as many threads as its container has CPUs, so that a 4-CPU limit does not make it three times slower.
46. As the operator, I want a time limit on each conversion, so that a stuck one frees its place.
47. As the operator, I want at most 20 conversions waiting, so that the server's memory stays bounded.
48. As the operator, I want each IP address limited to 500 pages a day, kept in memory only, so that no one visitor takes over the service and no IP address is stored.
49. As the operator, I want the bot check verified on the server, and refused whenever it cannot be verified, so that a missing key or a network error never lets bots through.
50. As the operator, I want the client IP taken only from what the Tailscale proxy sets, and proven unforgeable on staging and on production, so that the daily limit cannot be dodged with a header.
51. As the operator, I want logs that hold no content, file names, IP addresses or conversion links, so that the logs could be published without harm.
52. As the operator, I want overall numbers (conversions by outcome, pages by kind, durations, queue length, refusals by kind, sandbox memory and CPU), visible only from the server itself, so that I can see how the service is used without collecting anything personal.
53. As the operator, I want a health address, so that an uptime check can be added later.
54. As the operator, I want to deploy as I deploy Chatbot, with `git pull` and `docker compose`, so that there is one way of working on the server.
55. As the operator, I want a staging copy reachable only inside my tailnet, and a deploy script that refuses production until staging has run the same files and passed its smoke test, so that a broken change never reaches users.
56. As the operator, I want the smoke test to send a synthetic file through the real path (Tailscale, web app, launcher, gVisor container), so that what CI cannot test is tested before every release.
57. As the operator, I want the service's Tailscale node unable to reach any other device in my tailnet, so that a compromised web app cannot reach my laptop or Chatbot.
58. As the operator, I want nothing of this service to share a network, a volume or a secret with Chatbot, so that each can fail or be breached alone.
59. As the operator, I want a deploy or restart to drop running conversions cleanly, with a message to the visitor, so that nothing hangs.

**Developing it**
60. As a developer, I want web tests that run without Docker, with a fake sandbox, clock and bot check, so that they are fast and run in CI.
61. As a developer, I want to run the whole service on my own machine with Docker Desktop (normal runtime instead of gVisor, no Funnel, bot check in test mode), so that I can work on it locally.

## Implementation Decisions

### Shape

- **Three roles, one image.** The image the repo already builds gains the web dependencies and serves every role:
  - **the web app**, which faces the internet through Tailscale
  - **the launcher**, which starts containers
  - **the sandbox**, which converts one source file

  Only the sandbox ever parses a source file. The web app and the launcher pass its bytes along and never open them.
- **A Tailscale container** in the same compose project gives the service its own node and name, and its own Funnel on port 443 (ADR 0005).
- **Its own compose project on `gmt`.** It has its own network and volumes, and its own secrets in its own server-side env file. Nothing is shared with Chatbot.
- **New dependencies** are pinned and AGPL-compatible: an ASGI web framework and server (FastAPI and uvicorn, as Chatbot uses), multipart parsing, and an HTTP client for the bot check and the Docker Engine API.

### Converter changes

- **Both outputs from one conversion.** The conversion function takes the set of output formats wanted, and returns an output for each, with one summary.
  - When a DOCX source is asked for both formats, it gets Markdown only.
  - A DOCX source asked for DOCX alone is still refused, as now.
  - The CLI keeps asking for one format.
- **Progress through every stage:**
  - **opened:** reported as soon as the source passes intake, with its type and page count. The web app needs the page count for the daily allowance before any page is read.
  - **reading:** text pages.
  - **ocr:** each OCR page, as "current of total".
  - **writing:** the outputs.
- **OCR thread count.** The default OCR engine uses a configured number of CPU threads instead of PaddleOCR's fixed 10. The sandbox sets it to its CPU limit.
  - Measured: at a 4-CPU limit, 10 threads read a page in 8.8 seconds, and 4 threads in 3.3.
  - Environment variables such as `OMP_NUM_THREADS` do not work; PaddleOCR overrides them.
- **Uncertain text (converter ticket 11)** adds the uncertain count to the summary. The web shows it. This ticket must be done before launch.

### Sandbox entry point

A command in the package that the sandbox container runs. It is a thin wrapper around the conversion function, like the CLI.

- **Input:** the source file's bytes on stdin. No file name, no path and no settings other than the OCR thread count reach it.
- **Output:** each output on stdout, as a named, length-prefixed part.
- **Events:** on stderr, one JSON object per line:
  - opened, with source type and page count
  - progress, with stage, current and total
  - the summary, as structured data
  - or a refusal, with its kind, which matches the intake error types

  Events never carry file content.
- **Exit codes** match the CLI's. A refusal is not a crash.
- **Cancellation:** a conversion stops when its container is stopped. No cancellation exists inside the converter, and none is needed.

### Launcher

A small service, the only part with access to Docker. It reaches the Docker Engine through the mounted Docker socket, and has no network of its own.

- **Interface:** a Unix socket on a volume shared only with the web app. It offers two operations:
  - **run:** stream a source file in, and stream events and outputs back
  - **cancel:** stop a running conversion

  It starts nothing but the sandbox, from the image it was deployed with.
- **Every sandbox container gets:**
  - the gVisor runtime (`runsc`)
  - no network
  - a read-only root file system, with a small in-memory scratch area
  - the image's non-root user
  - no capabilities, and no-new-privileges
  - 4 CPUs, 2 GB of memory and no swap
  - a process limit
  - no volumes, no environment secrets, and stdin attached
- **Clean-up:**
  - Each container is removed when its conversion ends, however it ends.
  - At start, the launcher removes any leftover sandbox containers of its own environment. Container names carry the environment (production or staging).
- **Limits:**
  - At most 3 sandboxes at a time, as a backstop to the web app's queue.
  - A time limit per conversion, starting at 30 minutes and tuned from staging measurements, after which the container is stopped.
- **Untrusted output:** the sandbox's output is treated as untrusted.
  - Event lines are capped in length and validated against their schema.
  - Outputs are capped at 50 MB in total.
  - Anything malformed ends the conversion as failed.
- **Statistics:** the launcher records each sandbox's highest memory use and its CPU time, from Docker's stats, for the statistics page.
- **Runtime setting:** a setting selects the runtime.
  - Production uses gVisor.
  - The normal runtime (`runc`), with every other restriction kept, is the fallback if PaddleOCR cannot run under gVisor (ADR 0004).
  - Local development uses the normal runtime too.

### Web app: conversions

**States.** A conversion moves through these states, all held in memory:

| State | What it holds |
|---|---|
| waiting | the source file's bytes |
| running | the bytes stream to the launcher, then are released |
| finished | the outputs and the summary |
| refused | the refusal's kind |
| failed | — (also covers timed out) |
| cancelled | — |

- **Expiry:** finished outputs are dropped 10 minutes after the conversion finishes, or at once when the visitor deletes them. Downloading does not delete them (ADR 0001).
- **Restarts:** a restart or deploy loses every conversion. A link to an unknown conversion shows a page explaining that it expired, was deleted, or was lost to a restart, and offers to convert again.

**Access**
- Each conversion has a random identifier of at least 128 bits, in its link.
- The browser holds a random token in a cookie:
  - strictly necessary, so no consent banner
  - HttpOnly, Secure, SameSite=Strict, lasting one day
- Every request about a conversion needs both its link and the token that created it. Anyone else gets the same "not found" page as for an expired conversion.

**Queue**
- First in, first out, in memory.
- 3 running and at most 20 waiting. A file that arrives when 20 are waiting is refused with a "queue full, try again shortly" message.
- The conversion page shows its place in the queue.

**One at a time.** A browser with a conversion waiting or running cannot start another.

**Daily allowance**
- 500 pages per client IP per day, counting every page of the source file (text pages and OCR pages alike). The day runs from midnight to midnight, Bangkok time.
- The pages are charged when the sandbox reports the page count. A source file that would go over the allowance is stopped at that point, with a message saying how many pages remain and when the allowance resets.
- The counts are held in memory only and lost on restart.

**Bot check (Cloudflare Turnstile)**
- The page uses the invisible mode.
- The token is verified on the server before the upload is accepted, checking the hostname and the action.
- The upload is refused when:
  - verification fails
  - the secret key is missing
  - Cloudflare cannot be reached
- A local test mode, using Cloudflare's test keys, is switched on explicitly. Production refuses to start with test keys.

**Client IP**
- The address comes from the header that the Tailscale proxy sets, and only from requests that arrive from the Tailscale container.
- No other header is read; in particular, `CF-Connecting-IP` is ignored.
- Staging's smoke test and the launch checklist both prove that a forged header changes nothing.

**Upload**
- Multipart, refused as soon as it passes 50 MB. A `Content-Length` over the limit is refused before anything is read.
- The file name is kept in memory with the conversion, only to name the downloads.

**Results**
- The Markdown is fetched for the copy button and for its download.
- The DOCX is downloaded.
- Both are named after the source file, with a header that carries a Thai name correctly.
- The result page shows:
  - the summary
  - the time left before the outputs are deleted
  - a button that deletes them now

**Progress**
- The conversion page asks for its state every 2 seconds. This survives a phone suspending the tab.
- The tab's title shows the state.

**Messages**
- Refusals use the CLI's Thai wording, from one shared table of refusal messages.
- The web adds its own messages:
  - password-protected PDFs are not supported yet
  - queue full
  - daily allowance used
  - one file at a time
  - bot check failed
  - timed out
  - failed
  - expired, deleted or lost to a restart
- The sandbox's own text is never shown: the web maps refusal kinds to its own messages.

### Web app: pages

- **Home:** the upload area, the limits in one line, and the "how it works" section.
- **Conversion page:** queue place, progress, result, refusal, or failure.
- **Privacy page** (นโยบายความเป็นส่วนตัว):
  - who runs the service: Sujirat Attawibulkul, as an individual
  - contact for personal data: sujirat.attawibulkul@gmail.com
  - bugs: GitHub Issues
  - what is received, and that the source file is deleted when its conversion ends
  - that the outputs are deleted after 10 minutes or on request, and that a restart deletes everything
  - that content, file names and IP addresses are never logged
  - that IP addresses are held in memory only, for the daily allowance
  - that the file travels encrypted to our own server and through no third party
  - that the bot check shows Cloudflare browser data but never the file
  - that the only cookie is the strictly necessary one
  - that there are no analytics
- **Footer, on every page:** a link to the source code at the exact commit the server runs (AGPL), a link to the privacy page, and a link to GitHub Issues.
- **Thai only for now.** English comes later.

### "How it works" section

A section of the home page that explains a conversion with pictures, in plain Thai for readers with no technical background. The pictures are inline SVG and HTML, with no external images.

**What it shows**
1. **The file is checked:** its type is read from the content, and the limits are applied.
2. **Each page is read in one of two ways.**
   - From the file's own text, when there is any and it can be trusted.
   - With OCR, when the page is a scan, its text is drawn as shapes, or its own text is wrong.
3. **How wrong text is caught,** using the example "กำร" where the page shows "การ".
   - Characters that cannot be read.
   - Sara am in the wrong place.
   - Too few dictionary words: fewer than 95%.
4. **The Thai repair:**
   - marks put back in order
   - sara am made one character
   - legacy-font characters mapped back
   - no spaces inside words
   - printed lines joined back into paragraphs
5. **Structure and placeholders:**
   - headings, lists and tables kept
   - repeated headers and page numbers removed
   - signatures, stamps and images replaced by placeholders, never by invented text
6. **One document model, two outputs.** Uncertain text is marked in both.
7. **Where the file goes:** browser → our server, encrypted all the way → a throwaway container with no network → deleted.

**Rules for the section**
- It describes what the converter actually does. When a rule it shows changes in the converter, the section changes in the same ticket.
- Every example is synthetic, never taken from a real document.

### Design

- The visual design is made with the impeccable skill. That work records the repo's first `DESIGN.md`.
- **The approach is Chatbot's:**
  - plain HTML, CSS and JavaScript with no build step, served by the web app
  - a JSON interface for the conversion page
  - the same readability rules: Thai text at least 13 px, inputs at least 16 px, WCAG AA contrast, 44 px touch targets
- **The look is the service's own:** its own name (chosen during design), its own colours, and none of the NSTDA colours.
- Fonts are served by the service itself.

### Security of the web app

- **Content-Security-Policy:** this site only, plus Cloudflare's Turnstile origin for its script and frame. No inline script.
- **Headers on conversion pages and downloads:**
  - `Referrer-Policy: no-referrer`
  - `Cache-Control: no-store`
  - `X-Robots-Tag: noindex`
- **Requests that change state** (upload, cancel, delete) check the `Origin` header.

### Logs, statistics and health

- **Logs** record events without content:
  - start and stop
  - refusals, by kind
  - failures, by error type and place, with no messages that could quote content
  - The web server's access log is off: it would record IP addresses and conversion links.
  - Docker log rotation is set in compose.
- **Statistics** are counters in memory, since start and for today:
  - conversions by outcome
  - pages by kind
  - durations
  - queue waits
  - queue length now and at its highest
  - refusals by kind
  - bot-check failures
  - allowance refusals
  - sandbox timeouts and failures
  - the highest sandbox memory and CPU time

  They are served on a second listener bound to the server's own loopback address. The operator reads them over SSH. Tailscale never forwards to this listener.
- **A health address** answers whether the service is up, with no details. It is for an uptime check later.

### Hosting and deploy

- **Server:** `gmt`, following Chatbot's pattern.
  - A clone of the repo beside Chatbot's, pulled with a read-only deploy key while the repo is private.
  - The image is built on the server with `docker compose`. The OCR models are fetched at build time.
- **Production:** the web app, the launcher and the Tailscale container. Sandbox containers are not in compose: the launcher starts them.
- **Staging:**
  - its own compose project on `gmt`
  - its own Tailscale node (`pdf-staging`), reachable only inside the tailnet with Tailscale Serve, never with Funnel
  - Turnstile in test mode, so its smoke test can pass the bot check
  - container names carrying the environment
- **The deploy script,** adapted from Chatbot's:
  - `staging <branch>` deploys to staging and runs the smoke test. It records the commit as passed only if every check passes.
  - Production refuses to deploy unless staging passed the same server-used files. An override exists for emergencies.
- **The smoke test** runs against staging over the tailnet:
  - It sends a synthetic corpus file with OCR pages through the real path, and checks both outputs' text against reference text.
  - It checks that a forged client-IP header does not change whose allowance is charged.
  - It checks that the sandbox containers were started with every restriction listed above.
  - It records seconds per OCR page on `gmt`.
- **gVisor** is installed on `gmt` once, by hand, following written steps. Where Docker can reload its runtimes without a restart, it does, so Chatbot's containers are not interrupted. The steps cover:
  - installing the runtime
  - registering it with Docker
  - checking it

  Chatbot's containers keep the normal runtime.
- **Tailscale:** the service's nodes join with a tagged auth key kept in the server-side env file. The tailnet policy:
  - gives the tag the `funnel` attribute (production only)
  - grants the tag no access to any other device
- **Secrets** live only in the server's env files, never in git: the Turnstile keys and the Tailscale auth key.

### Launch checklist

- Converter ticket 11 (uncertain text) is merged.
- The git history has been checked for anything confidential, and the repo is public.
- Staging's smoke test passes, including on `gmt`'s speed.
- On production, before the link is shared:
  - the forged-header check passes through Funnel
  - Turnstile's hostname list holds `pdf.taila2e363.ts.net`, and its widget mode is "Invisible"
  - the tailnet policy is in place
- The privacy page and the "how it works" section are reviewed.

## Testing Decisions

- **A good test uses the service the way a browser does.** It sends HTTP requests to the web app and asserts only on what a visitor would see:
  - status codes, and the text of pages and messages
  - the downloaded outputs, read back with the existing Markdown and DOCX test readers
  - whether a link opens or not

  It never inspects the queue's internals, the stored state, or which helper ran.
- **Web app tests run without Docker.** Three fakes replace the outside world:
  - **A fake sandbox,** in place of the launcher. It runs the real conversion function in process with the fake OCR engine, so the outputs are real. A scripted variant lets queue and timing tests control when a conversion starts and ends.
  - **A fake clock,** for the 10-minute expiry and the day's allowance.
  - **A fake bot check:** pass, fail, unreachable, or no key.
- **The web app tests cover:**
  - a PDF giving both outputs, and a DOCX giving Markdown only
  - the summary on the result page
  - every refusal's message, including password-protected PDFs
  - queue position, the queue limit and one-at-a-time
  - the daily allowance and its reset
  - cancelling while waiting and while running
  - deleting
  - expiry after 10 minutes
  - another browser being denied a valid link
  - an unknown link after a restart
  - the bot check failing closed in every case
  - a forged IP header being ignored
  - download names with Thai characters
  - the privacy and security headers
  - the logs holding no content, file names, IP addresses or links. This reuses the fragment search of the privacy tests.
- **The converter changes** are tested through the conversion function, as now: both outputs from one conversion, progress stages including the page count, and the OCR thread count.
- **The sandbox entry point** is tested in a fresh process, as the privacy tests run conversions:
  - bytes in, then parts out, with events and exit codes
  - a refusal
  - no network, and nothing left behind
- **The launcher, gVisor, Tailscale and Funnel are not tested in CI.** CI cannot run Docker inside its container, and has no Funnel. Staging's smoke test covers them before every production deploy, and the launch checklist covers the production-only checks.
- **CI** runs the new tests inside the image like the existing ones: no network, a read-only file system.
- **Prior art:**
  - the privacy tests' fresh-process conversion and their search of the log for fragments of the document
  - the source-intake tests for refusals
  - the fake OCR engine
  - the Markdown and DOCX readers used by the converter tests

## Out of Scope

- Accurate mode on the web, and the GPU (ADR 0004 keeps the GPU out of the sandbox).
- Password-protected PDFs: refused with a message for now.
- An English interface.
- Alerts when the service is down. The health address is ready for one.
- Accounts, history, or keeping anything beyond 10 minutes.
- Several files at once, or folders.
- A preview of the output's text on the page. The result page offers copy and downloads.
- An API for programs.
- A custom domain, and Cloudflare in front of the service (ADR 0005).
- Keeping conversions or statistics across a restart.
- Self-hosting the web service behind other proxies. The CLI and its Docker image remain the way to self-host.
- Converter tickets 14 (scanned tables) and 15 (Accurate mode). They are welcome after launch, not needed for it.

## Further Notes

**Where the decisions came from.** The web-service grilling on 2026-10-20 and 2026-10-21 settled:
- the server
- the sandbox (ADR 0004) and the public entry (ADR 0005)
- the output retention (ADR 0001, changed)
- both outputs from one conversion (glossary: a conversion yields one or both outputs)
- launching before the quality gate
- every limit above
- the privacy page's operator and contact
- the design approach

The converter spec's "Decided for the web spec" list holds the earlier ones.

**Delivery branches.** Tickets are grouped into branches. Each ticket is a commit on its branch, and each branch merges into `main` through a PR once all of its tickets are done. The spec and tickets themselves merge first, from `docs/web-service`.

| Branch | Tickets |
|---|---|
| `feat/web-core` | 01–08 |
| `feat/web-sandbox` | 09–10 |
| `feat/web-design` | 11–13 |
| `chore/web-deploy` | 14–15 |

Tickets 01–08 need nothing on `gmt`. Ticket 15 also waits for converter ticket 11.

**Measured on the converter (Docker Desktop, synthetic files, 2026-10-21)**
- Memory per conversion:
  - with OCR pages: 1.0–1.3 GB at peak, so each sandbox gets 2 GB
  - without OCR: about 125 MB
- OCR speed:
  - unrestricted: 2.6–3.0 seconds per page on 10 threads
  - at a 4-CPU limit: 3.3 seconds per page when told 4 threads, 8.8 when not
- Loading PaddleOCR takes 5–6 seconds per conversion.
- Memory grew across conversions in one process, from 1.0 to 1.27 GB over six. This is one reason each conversion gets a fresh container.
- The image is 2.58 GB.
- `gmt` has an Intel Core Ultra 9 285K (24 cores, performance and efficiency cores) and 60 GB of memory. Its speed must be measured again on staging.

**Chatbot mistakes not to copy**
- Turnstile there lets everything through when no key is set, and does not handle a network error.
- Its rate limit trusts `CF-Connecting-IP` even on the Funnel path, where a visitor can set it.
- It logs part of what users send.

**Open questions to settle during implementation**
- Does PaddleOCR run under gVisor, and how much slower? If not, use the fallback (ADR 0004).
- Do sandboxes on `gmt`'s efficiency cores run much slower, and should they be pinned to performance cores?
- Which header does Funnel use for the client IP, and does it replace or append to a client's own? Settle this on staging, then confirm on production.
- Are Funnel's unpublished bandwidth limits enough for 50 MB uploads?
- The service's name, which is chosen during design.

**References**
- Chatbot's deploy pattern: `D:\Moss_Disk\Code\Chatbot\docs\DEPLOY.md`, `docker-compose.yml`, `docker-compose.staging.yml` and `scripts/deploy.sh`. Never open Chatbot's `.env` files.
- The sample contracts in `docs/example_pdf/` are confidential. They are never used by this work without asking the user first, and never as examples in the "how it works" section.
