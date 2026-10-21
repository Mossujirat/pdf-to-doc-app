# 07: Bot check (Cloudflare Turnstile)

**Parent:** Web service MVP spec, in this feature folder.

**What to build:** An upload is accepted only after Cloudflare Turnstile's token has been verified on the server. The widget runs in its invisible mode, so most visitors never see it. Whenever the token cannot be verified, the upload is refused: Chatbot's mistake of letting everything through is not repeated. A test mode with Cloudflare's test keys exists for local development and staging, and production refuses to start with test keys.

**Blocked by:** 03

**Status:** ready-for-agent

**Branch:** `feat/web-core`

**Checking**
- [ ] The home page carries the widget in its invisible mode, and sends the token with the upload.
- [ ] The server verifies the token before it accepts the file, checking the hostname and the action.
- [ ] The upload is refused, with a message, when:
  - verification fails
  - the secret key is missing
  - Cloudflare cannot be reached or does not answer in time
  - the hostname or the action does not match

**Test mode**
- [ ] Test mode is switched on by an explicit setting, and uses Cloudflare's test keys.
- [ ] A setting marks the production environment. With it, the app refuses to start when the keys are test keys or missing.

**Tests**
- [ ] HTTP tests with a fake verifier that passes, fails, is unreachable, or has no key. They check that the upload is accepted only when the verifier passes.
- [ ] The app refuses to start in production with test keys.
