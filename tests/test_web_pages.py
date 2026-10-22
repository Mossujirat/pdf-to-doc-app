"""What the pages say happened to a conversion, where a stage is too short for a test to catch
on a running app: a step a file skipped, and what became of a file that gave no result."""

from pdf_to_doc.web import pages
from pdf_to_doc.web.conversions import Conversion
from pdf_to_doc.web.protocol import OpenedEvent, ProgressEvent

OPENED = OpenedEvent(event="opened", source_type="pdf", pages=3)
WRITING = ProgressEvent(event="progress", stage="writing", current=None, total=None)


def test_a_file_with_no_page_for_ocr_shows_ocr_skipped_not_done() -> None:
    conversion = Conversion("token", "สัญญา.pdf", None, state="running", opened=OPENED, progress=WRITING)

    shown = pages.steps(conversion, None)

    assert 'data-step="read" data-at="done"' in shown
    assert 'data-step="ocr" data-at="skipped"' in shown


def test_a_file_read_with_ocr_shows_ocr_done() -> None:
    conversion = Conversion(
        "token", "สัญญา.pdf", None, state="running", opened=OPENED, progress=WRITING, read_with_ocr=True
    )

    assert 'data-step="ocr" data-at="done"' in pages.steps(conversion, None)


def test_a_conversion_cancelled_while_it_waited_never_had_a_sandbox_to_throw_away() -> None:
    waited = Conversion("token", "สัญญา.pdf", None, state="cancelled")
    ran = Conversion("token", "สัญญา.pdf", None, state="cancelled", started_at=1.0)

    assert "ถูกทิ้งไป" not in pages.conversion_page("abc", waited, None, 600)
    assert "ถูกทิ้งไป" in pages.conversion_page("abc", ran, None, 600)
