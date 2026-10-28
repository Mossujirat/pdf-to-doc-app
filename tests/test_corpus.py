"""The committed synthetic corpus: reproducible, up to date, and free of broken text."""

from pathlib import Path

import pytest
from docx_reader import page_texts
from fake_ocr import BlankEngine
from generate import DEGRADED, NOTE_ABOVE, NOTE_BELOW, SYNTHETIC, generate, generate_degraded
from markdown_reader import page_texts as markdown_page_texts

from pdf_to_doc import convert
from pdf_to_doc.quality import evaluate, reference_file_name, score_page

# OCR pages are read with real PaddleOCR. Their gate comes with the OCR baseline
# (ticket 17); until then, a page this far off means OCR has stopped working.
OCR_PAGE_MAX_CER = 0.05
# The share of the cells of tables on OCR pages that must be in place: 152 of 181 were (ticket 05).
OCR_CELLS_IN_PLACE = 0.8


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
    # Ruled tables come out as tables; the cells out of place are misread, as a word that lost its tone mark.
    assert report.cells_right >= OCR_CELLS_IN_PLACE * report.cells


@pytest.mark.ocr
def test_a_page_whose_text_layer_reads_kar_as_kam_comes_out_right() -> None:
    # Its font's ToUnicode map turns sara aa into sara am; OCR reads what the page shows.
    markdown = convert((SYNTHETIC / "wrong-unicode-map.pdf").read_bytes()).output.decode("utf-8")

    assert "การ" in markdown
    assert "กำร" not in markdown


@pytest.mark.ocr
def test_a_note_typed_over_a_rotated_scan_comes_out_once_and_no_line_is_lost() -> None:
    # Page 1 is turned upright by 270 degrees and page 2 by 90, each with a note in its text layer.
    markdown = convert((SYNTHETIC / "rotated-scans.pdf").read_bytes()).output.decode("utf-8")

    pages = markdown_page_texts(markdown)
    for number, (page, note) in enumerate(zip(pages, [NOTE_BELOW, NOTE_ABOVE], strict=True), start=1):
        reference = (SYNTHETIC / "rotated-scans" / reference_file_name(number)).read_text(encoding="utf-8-sig")
        assert page.count(note) == 1, f"page {number}"
        assert score_page(page, reference).cer < OCR_PAGE_MAX_CER, f"page {number}"


@pytest.mark.ocr
def test_two_columns_are_read_one_after_the_other_and_a_cover_sheet_row_by_row() -> None:
    # Pages 1 and 2 are set in two columns; page 3 sets labels apart from their values.
    # Read across the columns, or labels apart from their values, such a page is off by a third or more.
    markdown = convert((SYNTHETIC / "two-column-scans.pdf").read_bytes()).output.decode("utf-8")

    for number, page in enumerate(markdown_page_texts(markdown), start=1):
        reference = (SYNTHETIC / "two-column-scans" / reference_file_name(number)).read_text(encoding="utf-8-sig")
        assert score_page(page, reference).cer < OCR_PAGE_MAX_CER, f"page {number}"
