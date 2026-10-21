# pdf-to-doc

Converts PDF files into Markdown or DOCX, and DOCX files into Markdown, whose Thai and English text reads exactly as the original: no floating or missing vowels and tone marks, no spaces inside words, no sentences cut at every printed line. The Markdown is meant to be pasted into AI chats, the DOCX to be edited in Word.

Status: early development. PDF pages are read from their text layer, and scanned pages with OCR (PaddleOCR, on the CPU). Accurate mode is planned (see `.scratch/converter-engine/`), and the web service is being built (see `.scratch/web-service/`).

## Usage

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pdf-to-doc-models                         # once: fetch the OCR models (about 13 MB)
uv run pdf-to-doc document.pdf -o document.md
uv run pdf-to-doc document.pdf --to docx         # writes document.docx; -o document.docx does the same
uv run pdf-to-doc locked.pdf --password "..."   # a PDF that needs a password to open
```

Each page is read on its own: from its text layer, or with OCR when the page is a scan, its text is drawn as shapes, or its text layer is wrong (such as "กำร" where the page shows "การ"). Legacy Thai fonts' Private Use Area characters are mapped back to Thai. Images on text pages become short Thai placeholders where they sit: `[รูปภาพ]`, or `[ลายเซ็น]` and `[ตราประทับ]` where the image is clearly a signature on its signature line or a round coloured stamp. Text read with OCR that the converter cannot confirm is marked as uncertain: a word the dictionary does not hold, which a misread mark or letter usually leaves, or a stretch the OCR engine read with low confidence. Markdown wraps it in `<mark>`, and DOCX highlights it yellow. A misread that is itself a word is not caught. The CLI shows progress while OCR runs, and the summary at the top of the output names the OCR pages, counts the placeholders, and counts the uncertain text and the pages it is on. The models live in `~/.cache/pdf-to-doc/models`, or wherever `PDF_TO_DOC_MODELS` points; nothing is downloaded while converting.

A DOCX source is read from the structure Word saved: headings from heading styles, lists with the numbers Word draws (Thai digits and letters too), tables with merged cells, and pictures as placeholders. Its pages are where Word last laid them out, as Word records on saving; a file without those records breaks pages where breaks were typed. Text deleted with tracked changes on is left out.

The DOCX output keeps the original's structure, not its page layout: headings in Word's heading styles, lists, and tables with real merged cells. Each page of the original starts a new page. Text is set in TH Sarabun New 16 pt, with Thai marked as complex script so that Word breaks its lines between words; the font must be installed for Word to show it.

The source type is read from the file's content, not its name. These files are refused with a Thai message and an exit code of their own, listed by `pdf-to-doc --help`:

- legacy Word `.doc` files, Office files locked with a password, and anything that is not a PDF or DOCX
- a DOCX asked to become a DOCX
- files over 50 MB or 150 pages, and a DOCX that unpacks to more than 200 MB
- PDFs that need a password, when none or a wrong one is given
- PDFs whose permissions forbid copying text
- damaged files

### Docker

The image runs the converter on Linux, with the OCR models built in. Nothing is downloaded while converting, so it works with networking off:

```sh
docker build -t pdf-to-doc .
docker run --rm --network none -v "$PWD:/work" pdf-to-doc pdf-to-doc /work/document.pdf -o /work/document.md
```

The container runs as a non-root user. On a Linux host, add `--user "$(id -u):$(id -g)"` so it can write to your folder and the output belongs to you. It can also run with a read-only file system: add `--read-only --tmpfs /tmp`.

OCR starts 10 CPU threads, whatever the CPUs. When you limit the container's CPUs, set `PDF_TO_DOC_OCR_THREADS` to the same number, or OCR runs several times slower: add `--cpus 4 -e PDF_TO_DOC_OCR_THREADS=4`.

The image also holds `pdf-to-doc-sandbox`, which the web service runs in a throwaway container for each conversion. It takes the source file's bytes on stdin and no other input, writes both outputs to stdout, each after a line with its format and length in bytes, and reports progress on stderr as one JSON object per line:

```sh
docker run --rm -i --network none --read-only --tmpfs /tmp pdf-to-doc pdf-to-doc-sandbox < document.pdf > parts
```

## Development

```sh
uv run pytest                            # fast tests (a fake OCR engine stands in for PaddleOCR)
uv run pytest -m ocr                     # real PaddleOCR on the corpus scans
uv run mypy                              # type checking
uv run pdf-to-doc-eval corpus/synthetic  # measure broken text on the test corpus
uv run pdf-to-doc-web --dev              # the web service at http://127.0.0.1:8000, without Docker
docker compose -f compose.local.yaml up --build  # the whole web service on Docker, at the same address
```

The web service is in development (see `.scratch/web-service/`). There are two ways to run it on your machine:

- `pdf-to-doc-web --dev` runs each conversion in a process of its own on your machine, with no sandbox, and its cookie works over plain HTTP.
- `compose.local.yaml` runs the web app and the launcher on Docker Desktop, as on the server. The launcher starts each conversion in a throwaway container of its own, with no network, and removes it when the conversion ends. The one difference from the server is the runtime: Docker's own, instead of gVisor.

Either way, the bot check, Cloudflare Turnstile, runs with Cloudflare's test keys, so it needs the internet. `/health` answers `ok` while the service is up. The operator's counters are served only on the loopback address of the web app's machine or container, port 8001, and `pdf-to-doc-statistics` prints them there: `docker compose -f compose.local.yaml exec web pdf-to-doc-statistics`. Without `--dev`, `pdf-to-doc-web` takes its settings from the environment, as its container does: each setting in `src/pdf_to_doc/web/settings.py` as `PDF_TO_DOC_` and its name in capitals, such as `PDF_TO_DOC_MAX_RUNNING`.

CI (`.github/workflows/ci.yml`) builds the Docker image for every pull request and every push to `main`. It runs these checks inside the image, with no network and a read-only file system, and fails on any broken text on the corpus's text pages.

The test corpus and the reference-text format are described in `corpus/README.md`.

## Licence

AGPL-3.0-only (see `LICENSE` and `docs/adr/0002-open-source-under-agpl.md`). The test fonts Sarabun and Niramit are under the SIL Open Font License (`corpus/fonts/`).
