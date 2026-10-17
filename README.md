# pdf-to-doc

Converts PDF files into Markdown whose Thai and English text reads exactly as the original: no floating or missing vowels and tone marks, no spaces inside words, no sentences cut at every printed line. The Markdown is meant to be pasted into AI chats.

Status: early development. Only PDF pages that carry a text layer are converted so far. OCR pages, DOCX output and the web service are planned (see `.scratch/converter-engine/`).

## Usage

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pdf-to-doc document.pdf -o document.md
```

## Development

```sh
uv run pytest                            # tests
uv run mypy                              # type checking
uv run pdf-to-doc-eval corpus/synthetic  # measure broken text on the test corpus
```

The test corpus and the reference-text format are described in `corpus/README.md`.

## Licence

AGPL-3.0-only (see `LICENSE` and `docs/adr/0002-open-source-under-agpl.md`). The test fonts Sarabun and Niramit are under the SIL Open Font License (`corpus/fonts/`).
