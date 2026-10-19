# pdf-to-doc

Converts PDF files into Markdown whose Thai and English text reads exactly as the original: no floating or missing vowels and tone marks, no spaces inside words, no sentences cut at every printed line. The Markdown is meant to be pasted into AI chats.

Status: early development. Only PDF pages that carry a text layer are converted so far. OCR pages, DOCX output and the web service are planned (see `.scratch/converter-engine/`).

## Usage

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pdf-to-doc document.pdf -o document.md
uv run pdf-to-doc locked.pdf --password "..."   # a PDF that needs a password to open
```

The source type is read from the file's content, not its name. These files are refused with a Thai message and an exit code of their own, listed by `pdf-to-doc --help`:

- legacy Word `.doc` files, and anything that is not a PDF or DOCX (DOCX conversion is not built yet)
- files over 50 MB or 150 pages
- PDFs that need a password, when none or a wrong one is given
- PDFs whose permissions forbid copying text
- damaged files

### Docker

The image runs the converter on Linux. Nothing is downloaded while converting, so it works with networking off:

```sh
docker build -t pdf-to-doc .
docker run --rm --network none -v "$PWD:/work" pdf-to-doc pdf-to-doc /work/document.pdf -o /work/document.md
```

The container runs as a non-root user. On a Linux host, add `--user "$(id -u):$(id -g)"` so it can write to your folder and the output belongs to you. It can also run with a read-only file system: add `--read-only --tmpfs /tmp`.

## Development

```sh
uv run pytest                            # tests
uv run mypy                              # type checking
uv run pdf-to-doc-eval corpus/synthetic  # measure broken text on the test corpus
```

CI (`.github/workflows/ci.yml`) builds the Docker image on every push and pull request. It runs the same three checks inside the image, with no network and a read-only file system, and fails on any broken text in the corpus.

The test corpus and the reference-text format are described in `corpus/README.md`.

## Licence

AGPL-3.0-only (see `LICENSE` and `docs/adr/0002-open-source-under-agpl.md`). The test fonts Sarabun and Niramit are under the SIL Open Font License (`corpus/fonts/`).
