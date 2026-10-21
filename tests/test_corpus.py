"""The committed synthetic corpus: reproducible, up to date, and free of broken text."""

from pathlib import Path

import pytest
from docx_reader import page_texts
from fake_ocr import BlankEngine
from generate import DEGRADED, SYNTHETIC, generate, generate_degraded

from pdf_to_doc import convert
from pdf_to_doc.quality import evaluate, reference_file_name, score_page

# OCR pages are read with real PaddleOCR. Their gate comes with the OCR baseline
# (ticket 17); until then, a page this far off means OCR has stopped working.
OCR_PAGE_MAX_CER = 0.05


def files(folder: Path) -> dict[str, bytes]:
    return {str(path.relative_to(folder)): path.read_bytes() for path in folder.rglob("*") if path.is_file()}


def test_generating_twice_gives_identical_files(tmp_path: Path) -> None:
    generate(tmp_path / "first")
    generate(tmp_path / "second")

    assert files(tmp_path / "first") == files(tmp_path / "second")


def test_the_committed_corpus_is_what_the_generator_makes(tmp_path: Path) -> None:
    generate(tmp_path)

    assert files(tmp_path) == files(SYNTHETIC), "run: uv run python corpus/generate.py"


def test_the_committed_damaged_scans_are_what_the_generator_makes(tmp_path: Path) -> None:
    generate_degraded(tmp_path)

    assert files(tmp_path) == files(DEGRADED), "run: uv run python corpus/generate.py"


def test_the_text_pages_of_the_committed_corpus_have_no_broken_text() -> None:
    report = evaluate(SYNTHETIC, ocr=BlankEngine()).of_kind("text")

    assert len(report.pages) >= 4
    assert report.broken.total == 0
    assert report.cer == 0


def test_the_docx_of_each_text_page_of_the_committed_corpus_reads_as_its_reference_text() -> None:
    scored = []
    for source in sorted(SYNTHETIC.glob("*.pdf")):
        result = convert(source.read_bytes(), to="docx", ocr=BlankEngine())
        for text, page in zip(page_texts(result.output), result.summary.pages, strict=True):
            reference = SYNTHETIC / source.stem / reference_file_name(page.number)
            if page.kind == "text" and reference.exists():
                score = score_page(text, reference.read_text(encoding="utf-8-sig"))
                assert (score.cer, score.broken.total) == (0, 0), f"{source.name} page {page.number}"
                scored.append(page)

    assert len(scored) >= 4


@pytest.mark.ocr
def test_paddleocr_reads_the_scanned_pages_of_the_committed_corpus() -> None:
    report = evaluate(SYNTHETIC).of_kind("ocr")

    for page in report.pages:
        print(f"{page.source} page {page.number}: CER {page.score.cer:.4f}, Thai CER {page.score.thai_cer:.4f}")
    assert len(report.pages) >= 4
    assert {page.engine for page in report.pages} == {"PaddleOCR"}
    assert all(page.score.cer <= OCR_PAGE_MAX_CER for page in report.pages)
    assert report.broken.total == 0


@pytest.mark.ocr
def test_a_page_whose_text_layer_reads_kar_as_kam_comes_out_right() -> None:
    # Its font's ToUnicode map turns sara aa into sara am; OCR reads what the page shows.
    markdown = convert((SYNTHETIC / "wrong-unicode-map.pdf").read_bytes()).output.decode("utf-8")

    assert "การ" in markdown
    assert "กำร" not in markdown
