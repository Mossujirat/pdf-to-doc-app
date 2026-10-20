# 12: Conversion leaves nothing behind

**Parent:** Converter engine and CLI (v1) spec, in this feature folder.

**What to build:** A user can rely on two guarantees. A conversion never touches the network. Nothing from their file outlives it except the output they asked for. These are the runtime half of ADR 0001's privacy promise, verified by tests.

**Blocked by:** 08

**Status:** done

**Branch:** `feat/ocr`

**No network**
- [x] Conversion runs with all network access blocked and still succeeds, in default mode with real PaddleOCR. No model or resource is fetched on first use.

**No leftovers**
- [x] Temporary files, such as rendered page images, go into a private temporary directory. It is removed when a conversion ends, whether it succeeds, fails partway, or raises an intake error. (A conversion writes no temporary files at all; see the comments.)

**No content in logs**
- [x] Logs and error messages never contain document text or page images. They may contain page numbers, counts and timings.

**Tests**
- [x] One test blocks sockets and converts a mixed fixture.
- [x] One test checks that the temp area is empty after success and after a forced failure.
- [x] One test captures log output from a full conversion and confirms that no reference-text fragment appears in it.

## Comments

**2026-10-19, handed over from ticket 08 (OCR pages)**

- PaddleX writes working files (`func_ret`, `locks`, `temp`) under `PADDLE_PDX_CACHE_HOME`: `~/.paddlex` by default, `/tmp/paddlex` in the image. The leftovers check should include that folder.
- Pages are rendered in memory, and no image file is written. The engine is kept between conversions in one process, so nothing of a document should stay in it; check that too.
- The models download separately (`pdf-to-doc-models`, or at image build). The no-network test should run with them in place.

**2026-10-20, implementation notes**

- **How it is tested.** `tests/test_privacy.py` runs each conversion in a fresh Python process (`tests/fresh_process.py`), as a user's first conversion runs:
  - From the start, an audit hook refuses every call that reaches beyond the machine: connecting, sending, and name lookups. Creating a socket, binding it on the machine and asking the machine's name stay allowed, because urllib3 binds a socket on `::1` at import to learn whether IPv6 works. Each call tried is recorded, so a library that swallows the refusal still fails the test.
  - The process has a temp area of its own (`TMPDIR`, `TEMP`, `TMP`), and PaddleX's working folder (`PADDLE_PDX_CACHE_HOME`) sits inside it, as in the image.
  - When the conversion ends, the process lists the files left in the temp area and counts the Paddle predictors and tensors still alive. It does this before it exits, because a web service's process keeps running.
  - The predictors and tensors are found by searching every object reachable from those the garbage collector tracks. The collector tracks neither Paddle's objects nor a dict or tuple that holds only such objects, so the objects one step from a tracked one are not enough.
  - The root logger logs at DEBUG, as when a deployment turns logging up. Paddle's own loggers stay at ERROR, where the OCR adapter sets them. A conversion that fails is logged with its message and traceback. The test reads everything the process wrote to stdout and stderr.
- **Tests.** The fixture is a text page and two scans.
  - With real PaddleOCR and the network cut off, the conversion succeeds and tries no network call. The text page comes out exact, and each scan has a CER under 5%.
  - Nothing is left behind after a conversion that succeeds, after one that fails partway, and after a refusal at intake: no file in the temp area, no Paddle predictor or tensor, and no 8-character run of the document's text in the log. To fail partway, the progress callback raises before the second OCR page. The refusal is a locked PDF without its password. It needs no models, so it runs in the fast suite.
- **Each test was seen to fail on a deliberate break, which was then removed:**
  - Without the recogniser's model folder, PaddleX looked up huggingface.co, and the network test failed.
  - When `convert` wrote the source file to a temporary file, all three leftover tests failed.
  - When the output was logged at DEBUG, the log test found 205 fragments.
  - With the engine kept between conversions, as before this ticket, 6 Paddle objects were alive after a conversion that succeeded and after one that failed partway.
- **No temporary files.** The ticket asked for a private temp directory. A conversion writes no temporary file at all: pages are rendered in memory and handed to PaddleOCR as arrays. At the user's choice, no temp directory was added; instead, the tests fail if a file is left in the temp area.
  - When Paddle is imported, PaddleX creates three empty folders in its working folder (`temp`, `func_ret`, `locks`), and Paddle creates `~/.cache/paddle/dataset`. Nothing is written into them while converting.
- **The OCR engine is no longer kept between conversions.**
  - After a conversion, the engine kept for the next one still held these, in Paddle's native tensors:
    - the last OCR page, scaled to 1280 px;
    - the detector's map of that page;
    - the last batch of line images;
    - the recogniser's output for them, from which their text can be decoded.
  - They stayed until the next OCR page was read. The Python objects the engine held contained no document text.
  - At the user's choice, a conversion now loads its own engine when its first OCR page needs one, and drops it when it ends. Afterwards no predictor or tensor is alive. PaddleX keeps no predictor anywhere else; only a stateless `PaddleStaticEngine` remains.
  - Loading the engine again takes 0.73–0.80 s on Windows. Importing Paddle, about 7 s, still happens once per process.
  - This replaces ticket 08's "loaded when the first page needs OCR, and kept for the rest of the process"; ticket 08's comments have a note.
- **The network needed no code change.**
  - PaddleX checks its model hosts only when it has to find a model itself, and the adapter gives it the model folders.
  - PyThaiNLP uses only the word list it ships with.
- **Checked in the Linux image** (no network, read-only, `/tmp` in memory): mypy, the fast suite, `pytest -m ocr`, the harness gate, and a mounted conversion all pass.
- **Left open:**
  - The audit hook sees only the network calls Python makes. A native library that opened a socket itself would go unseen. In CI, the image runs with `--network none`, which blocks those too.
  - Memory that Python or Paddle has freed is not overwritten. After a conversion nothing refers to it, but a dump of the process's memory could still find it. The container is the boundary for that.
  - A native library could write a temporary file outside `TMPDIR`; glibc's `tmpfile()`, for example, uses `/tmp`. None was seen, and in the image `/tmp` is in memory.

**2026-10-20, changes after code review**

- **The search for Paddle objects went only one step** from the objects the collector tracks, so a predictor kept in a dict or tuple of its own would have been missed. It now searches everything reachable from them; with `datetime.date` standing in, it finds objects in both. Each run takes about 6 s longer.
- **The run that fails partway and the refusal are searched for document text too.** The failure is logged with its message and traceback.
- **The notes no longer say that every logger logs at DEBUG.**
- **Tidying:** `loaded_models` is renamed `paddle_objects_alive`, since it counts tensors too. `stop` no longer names three things in `fresh_process.py`. The test compares the failure with `ConversionStopped.__name__`. `read_pdf` says why its engine lives only as long as the call.
- **Not changed:**
  - The temp area check counts files, not folders. PaddleX's empty working folders hold nothing of a document.
  - The home folder is not searched. Paddle creates an empty `~/.cache/paddle/dataset` there when it is imported.
