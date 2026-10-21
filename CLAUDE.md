# pdf-to-doc-app

## Commands

- Tests: `uv run pytest`. Real PaddleOCR tests are marked `ocr` and left out by default: `uv run pytest -m ocr`. They, the harness and any conversion with OCR pages need the models, fetched once with `uv run pdf-to-doc-models`.
- Type checking: `uv run mypy`
- Quality harness: `uv run pdf-to-doc-eval corpus/synthetic` (format in `corpus/README.md`). `corpus/degraded` holds scans damaged on purpose, outside the gate, for measuring uncertain-text marking.
- Regenerate the synthetic corpus after changing `corpus/generate.py`: `uv run python corpus/generate.py`
- Linux container: build the image and run the checks the way `.github/workflows/ci.yml` does. In Git Bash, set `MSYS_NO_PATHCONV=1`, or it rewrites container paths such as `/tmp` into Windows paths.
- Web service on this machine: `uv run pdf-to-doc-web --dev` (no Docker, no sandbox), or the web app and the launcher on Docker Desktop: `docker compose -f compose.local.yaml up --build`. Both serve http://127.0.0.1:8000. The launcher's tests on its Unix socket run only on Linux, so run them in the image.
- Escapes in Python source are easy to lose in this environment:
  - The file-writing tools turn `\uXXXX` into the literal (often invisible) character.
  - Shell heredocs collapse `\\` to `\`.

  To keep `\u` escapes and regex backslashes intact, write that code through a quoted heredoc, using raw strings.
- On this Windows machine, set `UV_LINK_MODE=copy` to silence uv's hardlink warning.

## Thai text rules

- Never apply NFKC: it splits sara am into two characters.
- Do not use PyThaiNLP's `normalize` on extracted text: its dangling-mark and repeated-vowel steps delete characters. Use the repair function in `thai.py`.

## Sample files

`docs/example_pdf/` holds real signed contracts, and one is marked confidential. Keep them git-ignored and never upload them to an external service without asking.

## Agent skills

### Issue tracker

Issues and specs live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
