"""Uncertain text: what OCR read that the converter cannot confirm reads as the page does."""

from collections.abc import Sequence
from dataclasses import dataclass

from pdf_to_doc.misreads import misread_spans
from pdf_to_doc.model import Span
from pdf_to_doc.thai import repair
from pdf_to_doc.words import unknown_word_spans

# An OCR engine's confidence in a box below which all of the box is uncertain.
# PaddleOCR scores a whole line, and one misread mark barely moves the score:
# on synthetic scans at six levels of damage, lines with one or two wrong
# characters scored 0.93-0.96, as did lines without any, while lines read as
# nonsense scored 0.64-0.75 (2026-10-21). So a low score catches what was not
# read at all, such as smudges and handwriting, and unknown words catch the misreads.
LOW_CONFIDENCE = 0.85


@dataclass(frozen=True)
class Piece:
    """A stretch of a printed line as it was read: a box the OCR engine read, with its
    confidence, or text taken from the text layer, which is never uncertain."""

    text: str
    confidence: float | None = None  # None for text from the text layer


def uncertain_spans(text: str, pieces: Sequence[Piece]) -> tuple[Span, ...]:
    """Where a block's text is uncertain, neighbours made one stretch. `pieces` are what
    the text was joined from, in reading order. Only what OCR read can be uncertain:
    - a box read with low confidence, all of it
    - in any other box, Thai words the word list does not hold, which a misread mark or letter usually leaves,
      and words and numbers shaped like a misread, such as letters among a number's digits
    """
    doubtful = unknown_word_spans(text) + misread_spans(text)
    spans: list[Span] = []
    for piece, (start, end) in zip(pieces, _places(text, pieces)):
        if piece.confidence is None:
            continue
        if piece.confidence < LOW_CONFIDENCE:
            spans.append(_trimmed(text, start, end))
        else:
            spans += [(max(word_start, start), min(word_end, end)) for word_start, word_end in doubtful if word_start < end and start < word_end]
    return _merged(text, spans)


def _places(text: str, pieces: Sequence[Piece]) -> list[Span]:
    """Where each piece stands in the text, searched in reading order. A piece that is not
    found, as when a list item's bullet was taken off, gets the gap between its neighbours."""
    found: list[Span | None] = []
    position = 0
    for piece in pieces:
        wanted = repair(piece.text.strip())
        start = text.find(wanted, position) if wanted else -1
        if start < 0:
            found.append(None)
        else:
            position = start + len(wanted)
            found.append((start, position))
    places: list[Span] = []
    for index, place in enumerate(found):
        if place is None:
            after = next((later[0] for later in found[index + 1 :] if later), len(text))
            place = (places[-1][1] if places else 0, after)
        places.append(place)
    return places


def _trimmed(text: str, start: int, end: int) -> Span:
    """The span without the whitespace at either end."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _merged(text: str, spans: list[Span]) -> tuple[Span, ...]:
    """The spans in order, empty ones dropped, and those that touch, overlap or lie only
    spaces apart made one. A line break kept in a table's cell parts its items, so stretches
    either side of it stay two."""
    merged: list[Span] = []
    for start, end in sorted(span for span in spans if span[0] < span[1]):
        between = text[merged[-1][1] : start] if merged else ""
        if merged and (start <= merged[-1][1] or (between.isspace() and "\n" not in between)):
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return tuple(merged)
