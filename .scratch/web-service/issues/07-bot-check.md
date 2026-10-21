# 07: Bot check (Cloudflare Turnstile)

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** An upload is accepted only after Cloudflare Turnstile's token has been verified on the server. The widget runs in its invisible mode, so most visitors never see it. Whenever the token cannot be verified, the upload is refused: Chatbot's mistake of letting everything through is not repeated. A test mode with Cloudflare's test keys exists for local development and staging, and production refuses to start with test keys.

**Blocked by:** 03

**Status:** done

**Branch:** `feat/web-core`

**Checking**
- [x] The home page carries the widget in its invisible mode, and sends the token with the upload.
- [x] The server verifies the token before it accepts the file, checking the hostname and the action.
- [x] The upload is refused, with a message, when:
  - verification fails
  - the secret key is missing
  - Cloudflare cannot be reached or does not answer in time
  - the hostname or the action does not match

**Test mode**
- [x] Test mode is switched on by an explicit setting, and uses Cloudflare's test keys.
- [x] A setting marks the production environment. With it, the app refuses to start when the keys are test keys or missing.

**Tests**
- [x] HTTP tests with a fake verifier that passes, fails, is unreachable, or has no key. They check that the upload is accepted only when the verifier passes.
- [x] The app refuses to start in production with test keys.

## Comments

**2026-10-21, what Cloudflare does, checked**

From Cloudflare's docs (fetched 2026-10-21):
- **siteverify** is `POST https://challenges.cloudflare.com/turnstile/v0/siteverify`, with `secret` and `response`.
- **A token** is at most 2048 characters, good for 5 minutes and for one use. The widget puts it in the form field `cf-turnstile-response`.
- **Timeout:** Cloudflare's examples wait 10 seconds.

**The test keys:** the invisible site key `1x00000000000000000000BB` and the secret `1x0000000000000000000000000000000AA` always pass.
- The docs' example answer shows hostname "localhost" and action "test", and warns that real values may differ.
- Asked by hand on 2026-10-21, the passing secret answered for any token, made-up ones too. It gave hostname "example.com" and no action at all.
- **So test mode checks neither the hostname nor the action.** Outside test mode, both must match.

**Invisible mode is not set in the page.** It is the widget mode chosen when the widget is created in Cloudflare's dashboard. Ticket 15 and the spec's launch checklist now say so.

**2026-10-21, how it is built**

`web/bot_check.py` holds `BotCheck`, built from the settings: `bot_check_test_mode`, `turnstile_site_key`, `turnstile_secret_key`, `hostname` and `production`.

**`BotCheck.check(token)` returns a verdict.** Only "passed" lets an upload in:

| Verdict | When |
|---|---|
| `not configured` | no secret key, or no hostname outside test mode |
| `no token` | the token is missing or too long |
| `failed` | Cloudflare says no |
| `unreachable` | Cloudflare cannot be reached, gives no JSON, or takes more than 10 seconds in all |
| `another site` | the hostname or the action is not ours |
| `passed` | |

- **Refusals:** every other verdict gives 403 and "ตรวจสอบไม่ได้ว่าไฟล์นี้ส่งมาจากผู้ใช้จริง". The file is dropped, and no conversion or cookie is made.
- **Log:** a refusal is logged as `upload refused by the bot check: <verdict>`, so an outage reads differently from bots. The token is never logged. Ticket 10 can count verdicts from here.
- **What goes to Cloudflare:** only the token and the secret. Not the file, and not the visitor's address, as the spec's privacy page says.

**Production** refuses to start, with `Misconfigured`, when any of these holds:
- test mode is on
- a key is missing
- a key has the shape of a test key (`[123]x0+[A-F]{2}`), which also covers test keys Cloudflare adds later
- the hostname is missing

Nothing reads the settings from the environment yet; that is ticket 09's.

**The page:**
- The widget's `div` sits inside the upload form, with `data-action="upload"`. The script comes from Cloudflare's own address, as Cloudflare requires.
- A file sent before the widget has put its token in the form waits for it, for up to 15 seconds.
- A page the browser shows again from its history resets the widget, because the old token is spent.
- None of this script has run in a browser yet.

**Local development:** `pdf-to-doc-web` runs in test mode, so it needs the internet. The README says so.

**Tests** stand in for Cloudflare with `tests/fake_cloudflare.py`, an `httpx.MockTransport` that answers, fails or cannot be reached. The real `BotCheck` code runs in every case. Every other web test passes the bot check through `tests/web_browser.py`.

**Dependencies:**
- `httpx` 0.28.1 moved from the dev group to the runtime dependencies, as the spec planned for the bot check.
- Starlette's test client uses `httpx2` when it is installed. It was already in the lock through PaddleX, and is now a pinned dev dependency, 2.14.0, because the tests import it.

**2026-10-21, after code review**

**Fixed:**
- Outside test mode, a missing hostname matched an answer without one (`None == None`). It now counts as not configured.
- The 10 seconds were per step of the request. They are now the whole request's.
- The check returned only yes or no. It now returns why, for the logs.
- Production matched test keys from a fixed list. It now matches their shape.
- The comment on the test keys contradicted what Cloudflare answered.
- The widget is now reset on a page the browser restores, so that a second upload after Back does not send a spent token.
- A form with two file parts now keeps the first, as before this ticket.
- Names were tidied: `TOKEN_FIELD` and `_FILE_FIELD`, where both had been `FIELD`, and the Cloudflare stand-in now lives in `BotCheck`.
