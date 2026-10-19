"""The committed synthetic corpus: reproducible, up to date, and free of broken text."""

from pathlib import Path

from generate import SYNTHETIC, generate

from pdf_to_doc.quality import evaluate


def files(folder: Path) -> dict[str, bytes]:
    return {str(path.relative_to(folder)): path.read_bytes() for path in folder.rglob("*") if path.is_file()}


def test_generating_twice_gives_identical_files(tmp_path: Path) -> None:
    generate(tmp_path / "first")
    generate(tmp_path / "second")

    assert files(tmp_path / "first") == files(tmp_path / "second")


def test_the_committed_corpus_is_what_the_generator_makes(tmp_path: Path) -> None:
    generate(tmp_path)

    assert files(tmp_path) == files(SYNTHETIC), "run: uv run python corpus/generate.py"


def test_the_committed_corpus_converts_without_broken_text() -> None:
    report = evaluate(SYNTHETIC)

    assert len(report.pages) >= 4
    assert report.broken.total == 0
    assert report.cer == 0
