# 06: Linux Docker image + CI

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** The test suite and the quality harness run in a Linux Docker container, both locally and in GitHub Actions. Results then reflect the future server, not only the Windows development machine. The same image can run the CLI on a mounted file, so anyone can self-host the converter.

**Blocked by:** 02

**Status:** ready-for-agent

**Branch:** `feat/text-pages`

**Image**
- [ ] A Dockerfile builds a Linux image with the pinned dependencies.
- [ ] Models are downloaded at build time and baked into the image, never at conversion time. Later tickets add OCR models the same way.
- [ ] The image runs the CLI on a mounted source file and writes the output to a mounted folder.

**Tests in the container**
- [ ] Tests and the harness run inside the container with networking disabled, and pass.
- [ ] Line endings stay LF inside the image even when it is built from a Windows checkout.

**CI**
- [ ] A GitHub Actions workflow builds the image on each push and pull request, then runs the fast tests and the harness on the committed corpus. A failing harness threshold fails the build.
- [ ] Confidential local files are never referenced by CI.
