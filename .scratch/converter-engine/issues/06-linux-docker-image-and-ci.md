# 06: Linux Docker image + CI

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** The test suite and the quality harness run in a Linux Docker container, both locally and in GitHub Actions. Results then reflect the future server, not only the Windows development machine. The same image can run the CLI on a mounted file, so anyone can self-host the converter.

**Blocked by:** 02

**Status:** done

**Branch:** `feat/text-pages`

**Image**
- [x] A Dockerfile builds a Linux image with the pinned dependencies.
- [x] Models are downloaded at build time and baked into the image, never at conversion time. Later tickets add OCR models the same way.
- [x] The image runs the CLI on a mounted source file and writes the output to a mounted folder.

**Tests in the container**
- [x] Tests and the harness run inside the container with networking disabled, and pass.
- [x] Line endings stay LF inside the image even when it is built from a Windows checkout.

**CI**
- [x] A GitHub Actions workflow builds the image on each push and pull request, then runs the fast tests and the harness on the committed corpus. A failing harness threshold fails the build.
- [x] Confidential local files are never referenced by CI.

## Comments

**2026-10-19, implementation notes**

- **Image.**
  - It is built in two stages, and uv stays in the build stage.
  - The base image is Python 3.13.16 on Debian trixie, pinned by digest. uv is 0.9.13, the same as on the development machine, also pinned by digest.
  - Dependencies come from `uv.lock` with `uv sync --frozen`. The dev group is included, because one image runs the tests as well as the CLI.
  - The image is 116 MB.
- **Build context.** `.dockerignore` lists what may go in, and nothing else can. The confidential contracts under `docs/example_pdf/` can never reach the image.
- **Line endings.**
  - This machine's working copy had CRLF in 25 files, although `.gitattributes` asks for LF. Editing tools write CRLF, and git converts it only on commit.
  - A first build stage lets git rewrite the copied files by `.gitattributes`. Git decides what is text and leaves binary files alone, so the rules live in one place.
  - The files are deleted before `git checkout-index` writes them back, because it skips any file whose stat already matches the index, even with `--force`.
  - Checked: all 50 files in the image are byte-identical to their committed blobs, including the PDFs and fonts. On the host, `layout.py` alone has 307 CRs.
- **Nothing is downloaded at conversion time.**
  - There are no models yet. OCR models (ticket 08) should be downloaded in the build stage.
  - PyThaiNLP creates `~/pythainlp-data` when it is imported, and downloads any corpus it lacks on first use. The image sets `PYTHAINLP_READ_ONLY=1` and `PYTHAINLP_OFFLINE=1`, so a missing corpus fails instead of being fetched.
  - This came to light when the import crashed for a user with no home directory, and on a read-only file system.
- **Runs as a non-root user** (`converter`, uid 1000), because source files are untrusted input.
  - `/app` belongs to root. The pytest cache is off, and mypy's cache goes to `/tmp`.
  - On a Linux host, `--user "$(id -u):$(id -g)"` lets the container write to the user's folder. A uid with no account in the image also works.
- **Read-only file system.** Tests, mypy and the harness also pass with `--read-only --tmpfs /tmp`, which is how the spec says the server will run conversions. CI uses those flags too.
- **Checked locally (Docker Desktop on Windows), with networking off:**
  - 131 tests pass, mypy is clean, and the harness finds zero broken text.
  - The test that regenerates the corpus passes on Linux, so PyMuPDF writes the same bytes on Linux as on Windows.
  - The CLI converted a corpus PDF from a read-only mount into a mounted output folder.
  - A refusal keeps its exit code inside the container (3 for a TOML file).
- **CI** (`.github/workflows/ci.yml`).
  - It runs on `ubuntu-24.04`, with `actions/checkout` pinned by commit and only read access to the repository.
  - It builds the image, then runs mypy, pytest and the harness in a sandbox: no network, a read-only file system, `/tmp` in memory.
  - The harness gate is `--max-broken 0`, the spec's "zero broken text". A CER target is left to ticket 17. `test_corpus.py` still requires a CER of 0 on the committed corpus, so ticket 08 must change that test when it adds scans.
  - A harness over its threshold exits 1 and fails the step; this was checked locally with `--max-cer -1`.
  - It also converts a committed PDF from a read-only mount into a mounted folder as the runner's own user, and checks that the output holds the table.
  - actionlint 1.7.7 finds no problems.
  - Added beyond the ticket: mypy. It is one of the repo's three standard checks, and it takes seconds.
- **Left open:**
  - CI does not cache Docker layers, so every run builds the image from scratch.
  - A pull request from a branch in this repository runs CI twice, once for the push and once for the pull request. That is what "each push and pull request" asks for.
  - There is no model download step yet, only the place for it. Ticket 08 adds the first one.

**2026-10-19, changes after code review**

- **Line endings come from git**, not from a copied list of binary extensions. With that list, a future binary fixture such as a `.jpg` scan would have lost bytes silently.
- **Pinning.** The unpinned `# syntax=` frontend line is gone; nothing needed it. The base image is named once, in an `ARG`.
- **CI.**
  - The harness gate is broken text only (see above).
  - The mounted-file conversion runs in CI, not only by hand.
  - The sandbox flags are written once, in a shell function.
- **Docs point to one place.** The Dockerfile header points to the README and the workflow. CLAUDE.md points to the workflow and keeps only the Git Bash path gotcha.
