# 13: Privacy page and footer

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** A privacy page in plain Thai (นโยบายความเป็นส่วนตัว) tells a visitor exactly what happens to their file and their data, who runs the service, and how to reach them, as the PDPA requires. Every page gets a footer linking to:
- the source code, at the exact commit the server runs, as the AGPL requires
- the privacy page
- GitHub Issues

**Blocked by:** 11

**Status:** done

**Branch:** `feat/web-design`

**Privacy page**
- [x] Who runs the service: Sujirat Attawibulkul, as an individual.
- [x] Contact for personal data: sujirat.attawibulkul@gmail.com. Bugs go to GitHub Issues.
- [x] What happens to a file:
  - what is received
  - the source file is deleted when its conversion ends
  - the outputs are deleted 10 minutes after it finishes, or on request
  - a restart deletes everything
- [x] What is not kept or seen:
  - content, file names and IP addresses are never logged
  - IP addresses are held in memory only, for the daily allowance
- [x] The file travels encrypted to our own server, through no third party.
- [x] The bot check shows Cloudflare browser data, but never the file.
- [x] The only cookie is the strictly necessary one. There are no analytics.
- [x] The visitor's rights under the PDPA, and how to exercise them.

**Footer**
- [x] The image records the commit it was built from. The footer links to the repository at that commit.
- [x] Links to the privacy page and to GitHub Issues.

**Tests**
- [x] The privacy page states the retention times from the service's settings, the operator and the contact.
- [x] The footer's source link carries the running commit.

## Comments

**2026-10-22, built**

**The privacy page** is at `/privacy` (`pages.privacy()`). It is one card of sections:
- who runs the service, and the contact
- what is received
- where a file goes and when it is deleted
- what is not kept
- the cookie
- the bot check
- the visitor's rights
- the source code

It ends with the date it was last changed. How long results are kept, and the daily allowance, come from the settings.

**Worded to match the facts rather than the ticket's shorthand:**
- **"Through no third party":** the file does pass Tailscale's relay on its way. ADR 0005 records that TLS ends on our own machine, so the relay cannot read the file. The page says that: the relay forwards the file but cannot read it.
- **What Cloudflare's bot check sees:** the page lists the IP address, the User-Agent, the TLS fingerprint and the site key with its origin. These come from Cloudflare's Turnstile Privacy Addendum (www.cloudflare.com/turnstile-privacy-policy, read 2026-10-22).
- **"Never the file":** this rests on two facts:
  - Cloudflare's Turnstile FAQ, read the same day, says Turnstile "does not access, store, or transmit user communications, form entries, or other page inputs".
  - Our server sends Cloudflare only the secret and the token (`bot_check.py`), not even the address.

  The page links to the addendum.
- **The cookie:** the page speaks only of the site's own cookie, `browser`: strictly necessary, valid for 1 day. It makes no claim about cookies Cloudflare's own frame might set.
- **The PDPC's name:** สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล (สคส.), as pdpc.or.th gives it. The page links to that site, which has no complaint page of its own.
- **The rights:** the page lists them without section numbers or promised response times, which the operator has not decided.

**The footer and the commit:**
- **The image:** the Dockerfile takes `BUILD_COMMIT` as a build argument, last, so that a new commit rebuilds only that layer. It records it as `PDF_TO_DOC_BUILD_COMMIT`, which becomes the `build_commit` setting.
- **The footer:** it links to `/source-code` on the site itself. That route redirects to `github.com/Mossujirat/pdf-to-doc-app/tree/<commit>`, or to the repository if the build named no commit.
  - **Why:** this way every page function does not need the commit passed in.
  - **The cost:** the link in the footer does not carry the commit itself, as the ticket's test words it. The redirect it leads to does, and the test checks that.
- **Checks at start:**
  - The public service refuses to start without the commit.
  - Any service refuses a value that is not a commit's hash (7 to 40 lowercase hex digits).
- **Older tests:** the production settings in the older settings and bot-check tests now carry a commit, so that each still refuses for its own reason.
- **Ticket 14:** a comment there says to pass the build argument.

**Tests:** `tests/test_web_privacy.py` covers:
- the operator, the contact, how long results are kept and the daily allowance on the privacy page
- the footer's three links on the home page, the privacy page and a "not found" page
- `/source-code` with a commit and without one
- refusal to start without a commit, or with a value that is not a hash

`shown_text()` moved to `tests/web_browser.py`, for the home and privacy tests alike.

**Checked:** the privacy page, and a notice with the footer, photographed in headless Edge at 1440 px and at 390 px.

**2026-10-22, after code review**

**Fixed in the code:**
- **Yesterday's addresses stayed in memory** until the next file came: the allowance started a new day only when it next counted pages. `Allowance.forget_past_days()` now drops them, and the 15-second sweep for expired conversions calls it. The page can therefore say that addresses are cleared within seconds of midnight.
- **Test:** `test_yesterdays_addresses_leave_memory_after_midnight_though_no_file_comes`.

**Fixed on the page:**
- It now says that Tailscale's relay sees the visitor's IP address, to forward the connection, though it cannot read the content.
- It now says that the file name is kept as long as the results.
- Cloudflare's signals are given as examples ("เช่น"), as the addendum gives them.
- The cookie's name and lifetime come from the app's own constants (`COOKIE`, `_DAY`).

**Renamed:** "source" alone means the user's file in `GLOSSARY.md`, so the link and the setting say what they are:
- `source_commit` became `build_commit`, with `BUILD_COMMIT` and `PDF_TO_DOC_BUILD_COMMIT`
- `/source` became `/source-code`

**Tidied:**
- **The repository's links:** they are built in one place, `code_at()` and `_ISSUES` in `pages.py`.
- **Test settings:** the production settings, with a commit, are one shared `PRODUCTION` in `tests/web_browser.py`, used by the settings, bot-check and privacy tests.
- **Test URLs:** the tests write the repository's URL out in full, rather than importing it.
- **The design records:** the privacy page's headings use the Title size, the footer's link gap follows the spacing scale, and `DESIGN.md` and its sidecar now describe the page to read and the footer.

**For ticket 14:** a note there says to check what Tailscale's container logs and uploads.
