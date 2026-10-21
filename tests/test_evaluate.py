"""Evaluating a corpus: converting each source file and scoring its pages against reference text."""

import json
from pathlib import Path

import pytest
from fake_ocr import FakeEngine
from pdf_builder import Scan, pdf
from word_builder import Heading, PageBreak, document

from pdf_to_doc.evaluate_cli import main
from pdf_to_doc.quality import CorpusError, evaluate, reference_file_name


def add_document(corpus: Path, name: str, source: bytes, references: dict[int, str], suffix: str = ".pdf") -> None:
    corpus.mkdir(exist_ok=True)
    (corpus / f"{name}{suffix}").write_bytes(source)
    (corpus / name).mkdir()
    for page, text in references.items():
        (corpus / name / reference_file_name(page)).write_text(text, encoding="utf-8")


def test_a_page_that_matches_its_reference_scores_perfect(tmp_path: Path) -> None:
    add_document(tmp_path, "contract", pdf(["สัญญาให้ทุนโครงการ"]), {1: "สัญญาให้ทุนโครงการ"})

    report = evaluate(tmp_path)

    [page] = report.pages
    assert (page.source, page.number, page.kind) == ("contract", 1, "text")
    assert page.score.cer == 0
    assert report.broken.total == 0


def test_a_docx_source_is_scored_page_by_page_like_a_pdf(tmp_path: Path) -> None:
    source = document("หน้าแรก", PageBreak(), Heading("บทที่สอง"), "หน้าที่สอง")
    add_document(tmp_path, "letter", source, {1: "หน้าแรก", 2: "# บทที่สอง\n\nหน้าที่สอง"}, suffix=".docx")

    report = evaluate(tmp_path)

    assert [(page.source, page.number, page.kind, page.score.cer) for page in report.pages] == [
        ("letter", 1, "text", 0),
        ("letter", 2, "text", 0),
    ]


def test_only_pages_with_reference_text_are_scored(tmp_path: Path) -> None:
    add_document(tmp_path, "report", pdf(["หน้าแรก"], ["หน้าที่สอง"]), {2: "หน้าที่สาม"})
    add_document(tmp_path, "draft", pdf(["ยังไม่มีข้อความอ้างอิง"]), {})

    report = evaluate(tmp_path)

    assert [(page.source, page.number) for page in report.pages] == [("report", 2)]
    assert report.pages[0].score.cer > 0


def test_the_total_cer_is_all_edits_over_all_reference_characters(tmp_path: Path) -> None:
    # 10 + 10 reference characters, one error in total: 1 / 20
    add_document(
        tmp_path,
        "letters",
        pdf(["abcdefghij"], ["klmnopqrst"]),
        {1: "abcdefghij", 2: "klmnopqrsX"},
    )

    assert evaluate(tmp_path).cer == 1 / 20


def test_output_on_a_page_whose_reference_is_empty_still_counts_as_error(tmp_path: Path) -> None:
    add_document(tmp_path, "pages", pdf(["abcdefghij"], ["ขยะ"]), {1: "abcdefghij", 2: ""})

    assert evaluate(tmp_path).cer == 3 / 10


def test_a_reference_file_saved_with_a_byte_order_mark_reads_the_same(tmp_path: Path) -> None:
    add_document(tmp_path, "contract", pdf(["สัญญาให้ทุนโครงการ"]), {})
    (tmp_path / "contract" / "page-001.reference.md").write_text("สัญญาให้ทุนโครงการ", encoding="utf-8-sig")

    assert evaluate(tmp_path).cer == 0


def test_a_badly_named_reference_file_stops_the_evaluation(tmp_path: Path) -> None:
    add_document(tmp_path, "contract", pdf(["สัญญาให้ทุนโครงการ"]), {})
    (tmp_path / "contract" / "page-1.reference.md").write_text("สัญญาให้ทุนโครงการ", encoding="utf-8")

    with pytest.raises(CorpusError, match="page-1.reference.md"):
        evaluate(tmp_path)


def test_reference_text_for_a_page_the_source_does_not_have_stops_the_evaluation(tmp_path: Path) -> None:
    add_document(tmp_path, "contract", pdf(["หน้าเดียว"]), {1: "หน้าเดียว", 5: "หน้าที่ห้า"})

    with pytest.raises(CorpusError, match="page 5"):
        evaluate(tmp_path)


def test_a_corpus_with_no_reference_text_at_all_stops_the_evaluation(tmp_path: Path) -> None:
    add_document(tmp_path, "draft", pdf(["ยังไม่มีข้อความอ้างอิง"]), {})

    with pytest.raises(CorpusError, match="no reference text"):
        evaluate(tmp_path)


# The command line


def test_the_command_prints_a_table_and_writes_a_json_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    add_document(corpus, "contract", pdf(["สัญญาให้ทุนโครงการ"]), {1: "สัญญาให้ทุนโครงการ"})
    json_path = tmp_path / "report.json"

    exit_code = main([str(corpus), "--json", str(json_path)])

    assert exit_code == 0
    table = capsys.readouterr().out
    assert "contract" in table
    assert "unmarked" in table.splitlines()[0]
    report = json.loads(json_path.read_text(encoding="utf-8"))
    categories = {
        "orphan_marks",
        "spaces_inside_words",
        "pua_characters",
        "decomposed_sara_am",
        "missing_text",
        "total",
    }
    assert report["total"]["cer"] == 0
    assert set(report["total"]["broken"]) == categories
    assert report["total"]["broken"]["total"] == 0
    assert "uncertain" in report["total"]
    [page] = report["pages"]
    assert (page["source"], page["page"], page["kind"]) == ("contract", 1, "text")
    assert set(page["broken"]) == categories
    assert {"engine", "uncertain", "cer", "thai_cer"} <= set(page)


def test_the_command_fails_when_broken_text_exceeds_the_limit(tmp_path: Path) -> None:
    # The page draws a real space inside the word, so the output keeps it.
    add_document(tmp_path, "report", pdf(["หรื อ"]), {1: "หรือ"})

    assert main([str(tmp_path), "--max-broken", "0"]) == 1
    assert main([str(tmp_path), "--max-broken", "1"]) == 0


def test_the_command_fails_when_the_cer_exceeds_the_limit(tmp_path: Path) -> None:
    add_document(tmp_path, "letters", pdf(["abcdefghij"]), {1: "abcdefghiX"})

    assert main([str(tmp_path), "--max-cer", "0"]) == 1
    assert main([str(tmp_path), "--max-cer", "0.1"]) == 0


def test_the_command_fails_when_there_is_nothing_to_measure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "no-such-folder"), "--max-broken", "0"]) == 2
    assert main([str(tmp_path), "--max-broken", "0"]) == 2
    assert "no reference text" in capsys.readouterr().out


# OCR pages


def test_ocr_pages_are_measured_with_their_engine_but_the_limits_cover_text_pages_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The engine misses the scan's second line: measured as broken text, but not gated yet.
    source = pdf(["หน้าที่มีข้อความในไฟล์"], Scan(["บรรทัดแรกของหน้าสแกน", "บรรทัดที่สองที่อ่านไม่ออก"], dpi=50))
    add_document(
        tmp_path / "corpus", "mixed", source, {1: "หน้าที่มีข้อความในไฟล์", 2: "บรรทัดแรกของหน้าสแกนบรรทัดที่สองที่อ่านไม่ออก"}
    )
    json_path = tmp_path / "report.json"

    exit_code = main(
        [str(tmp_path / "corpus"), "--max-broken", "0", "--max-cer", "0", "--json", str(json_path)],
        ocr=FakeEngine(["บรรทัดแรกของหน้าสแกน"]),
    )

    assert exit_code == 0
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert [(page["kind"], page["engine"]) for page in report["pages"]] == [("text", None), ("ocr", "fake")]
    assert report["by_kind"]["text"]["broken"]["total"] == 0
    assert report["by_kind"]["ocr"]["broken"]["missing_text"] == 1
    table = capsys.readouterr().out
    assert "TOTAL text" in table
    assert "TOTAL ocr" in table


def test_uncertain_text_on_ocr_pages_is_counted_and_errors_left_unmarked_are_reported(tmp_path: Path) -> None:
    # Two misreads: "เคือน" is not a word and gets marked; "ทาก" for "หาก" is a word and does not.
    source = pdf(Scan(["สแกน"], dpi=50))
    add_document(tmp_path / "corpus", "scan", source, {1: "ส่งรายงานทุกหกเดือน หากล่าช้าต้องแจ้ง"})
    json_path = tmp_path / "report.json"

    main([str(tmp_path / "corpus"), "--json", str(json_path)], ocr=FakeEngine(["ส่งรายงานทุกหกเคือน ทากล่าช้าต้องแจ้ง"]))

    report = json.loads(json_path.read_text(encoding="utf-8"))
    [page] = report["pages"]
    assert page["uncertain"] == 1
    assert page["edits"] == 2
    assert page["unmarked_edits"] == 1
    assert page["marked_characters"] == len("เคือน")
    assert report["by_kind"]["ocr"]["unmarked_share"] == 0.5
