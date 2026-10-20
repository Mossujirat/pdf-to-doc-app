"""Measures broken text: how far each output page is from its reference text."""

import html
import re
import unicodedata
from dataclasses import dataclass, fields
from pathlib import Path

from rapidfuzz.distance import Indel, Levenshtein, Opcode

from pdf_to_doc.conversion import convert
from pdf_to_doc.markdown import split_pages
from pdf_to_doc.model import PageKind
from pdf_to_doc.ocr import OcrEngine
from pdf_to_doc.thai import MARK, THAI_LETTER, is_thai

# Reference text of at least this many characters that the output lacks altogether.
MISSING_TEXT_MIN_LENGTH = 10

_ORPHAN_MARK = re.compile(rf"(?<!{THAI_LETTER}){MARK}")
_PRIVATE_USE = re.compile(r"[\ue000-\uf8ff]")
_DECOMPOSED_SARA_AM = re.compile(r"\u0e4d\u0e32|\u0e32\u0e4d")
_REFERENCE_FILE = re.compile(r"^page-(\d{3})\.reference\.md$")


class CorpusError(ValueError):
    """The corpus cannot be evaluated as laid out."""


@dataclass(frozen=True)
class BrokenText:
    """Broken text in an output page, counted by kind, beyond what the reference text has."""

    orphan_marks: int = 0
    spaces_inside_words: int = 0
    pua_characters: int = 0
    decomposed_sara_am: int = 0
    missing_text: int = 0

    @property
    def total(self) -> int:
        return sum(getattr(self, field.name) for field in fields(self))

    def __add__(self, other: "BrokenText") -> "BrokenText":
        return BrokenText(
            **{field.name: getattr(self, field.name) + getattr(other, field.name) for field in fields(self)}
        )


@dataclass(frozen=True)
class PageScore:
    edits: int
    characters: int
    thai_edits: int
    thai_characters: int
    broken: BrokenText

    @property
    def cer(self) -> float:
        return error_rate(self.edits, self.characters)

    @property
    def thai_cer(self) -> float:
        return error_rate(self.thai_edits, self.thai_characters)


def error_rate(edits: int, characters: int) -> float:
    """Edits per reference character. With no reference text, any output is all error."""
    if characters:
        return edits / characters
    return 1.0 if edits else 0.0


def score_page(output: str, reference: str) -> PageScore:
    """Score one page. Both sides are compared as visible text: markup and spacing are ignored."""
    output, reference = visible_text(output), visible_text(reference)
    thai_output, thai_reference = _thai_only(output), _thai_only(reference)
    return PageScore(
        edits=Levenshtein.distance(output, reference),
        characters=len(reference),
        thai_edits=Levenshtein.distance(thai_output, thai_reference),
        thai_characters=len(thai_reference),
        broken=_broken_text(output, reference),
    )


def _broken_text(output: str, reference: str) -> BrokenText:
    return BrokenText(
        orphan_marks=_extra(_ORPHAN_MARK, output, reference),
        spaces_inside_words=_spaces_inside_words(output, reference),
        pua_characters=_extra(_PRIVATE_USE, output, reference),
        decomposed_sara_am=_extra(_DECOMPOSED_SARA_AM, output, reference),
        missing_text=sum(1 for op in Indel.opcodes(reference, output) if _drops_text(op, reference)),
    )


def _spaces_inside_words(output: str, reference: str) -> int:
    """Spaces the output puts between two Thai letters that the reference writes together.

    The letters are aligned with the spaces taken out, so a space that moved
    shows up wherever it landed. A space before a mark is not counted here: it
    already shows as an orphan mark.
    """
    output_letters, output_spaces = _letters_and_spaces(output)
    reference_letters, reference_spaces = _letters_and_spaces(reference)
    to_reference: dict[int, int] = {}
    for block in Indel.opcodes(reference_letters, output_letters):
        if block.tag == "equal":
            for offset in range(block.dest_end - block.dest_start):
                to_reference[block.dest_start + offset] = block.src_start + offset
    count = 0
    for position in output_spaces:
        before, after = output_letters[position - 1], output_letters[position]
        if not (is_thai(before) and is_thai(after)) or re.match(MARK, after):
            continue
        start, end = to_reference.get(position - 1), to_reference.get(position)
        if start is not None and end == start + 1 and end not in reference_spaces:
            count += 1
    return count


def _letters_and_spaces(text: str) -> tuple[str, set[int]]:
    """The text without spaces, and the positions in it where a space stood between two letters."""
    letters: list[str] = []
    spaces: set[int] = set()
    for char in text:
        if not char.isspace():
            letters.append(char)
        elif letters:
            spaces.add(len(letters))
    return "".join(letters), {position for position in spaces if position < len(letters)}


def _drops_text(op: Opcode, reference: str) -> bool:
    dropped = reference[op.src_start : op.src_end].strip()
    return op.tag == "delete" and len(dropped) >= MISSING_TEXT_MIN_LENGTH


def _extra(pattern: re.Pattern[str], output: str, reference: str) -> int:
    """How many more times the pattern occurs in the output than in the reference."""
    return max(0, len(pattern.findall(output)) - len(pattern.findall(reference)))


def _thai_only(text: str) -> str:
    return "".join(char for char in text if is_thai(char))


_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# Inline tags such as <mark> wrap part of a word, so they disappear without a trace.
_INLINE_TAG = re.compile(r"</?(?:mark|b|strong|i|em|u|s|span|sup|sub|a|font)\b[^<>]*>", re.IGNORECASE)
# Other tags, such as table cells, separate their contents.
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*\b[^<>]*>")
# Headings, quotes, list bullets and table separator rows.
_LINE_MARKUP = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+|>[ \t]?|[-*+][ \t]+|\|?[ \t:-]*-{3,}[ \t:|-]*$)", re.MULTILINE)
_EMPHASIS = re.compile(r"\*\*|__")
_TABLE_PIPE = re.compile(r"\|")
_WHITESPACE = re.compile(r"\s+")
_BYTE_ORDER_MARK = "\ufeff"


def visible_text(markdown: str) -> str:
    """The text a reader sees: no markup, NFC, every run of whitespace as one space.

    Never NFKC: it would split sara am into two characters and hide that damage.
    """
    text = _HTML_COMMENT.sub(" ", markdown.replace(_BYTE_ORDER_MARK, ""))
    text = _INLINE_TAG.sub("", text)
    text = _TAG.sub(" ", text)
    text = _LINE_MARKUP.sub("", text)
    text = _EMPHASIS.sub("", text)
    text = _TABLE_PIPE.sub(" ", text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)
    return _WHITESPACE.sub(" ", text).strip()


@dataclass(frozen=True)
class PageReport:
    source: str
    number: int
    kind: PageKind
    score: PageScore
    engine: str | None = None
    # The conversion summary does not report this yet; uncertain-text marking
    # (ticket 11) will fill it in.
    uncertain: int = 0


@dataclass(frozen=True)
class Report:
    pages: tuple[PageReport, ...]

    @property
    def broken(self) -> BrokenText:
        return sum((page.score.broken for page in self.pages), BrokenText())

    @property
    def cer(self) -> float:
        """All edits over all reference characters."""
        return error_rate(
            sum(page.score.edits for page in self.pages),
            sum(page.score.characters for page in self.pages),
        )

    @property
    def thai_cer(self) -> float:
        return error_rate(
            sum(page.score.thai_edits for page in self.pages),
            sum(page.score.thai_characters for page in self.pages),
        )

    @property
    def uncertain(self) -> int:
        return sum(page.uncertain for page in self.pages)

    def of_kind(self, kind: PageKind) -> "Report":
        """The report for text pages only, or for OCR pages only."""
        return Report(pages=tuple(page for page in self.pages if page.kind == kind))


def reference_file_name(number: int) -> str:
    return f"page-{number:03d}.reference.md"


def evaluate(corpus: Path, ocr: OcrEngine | None = None) -> Report:
    """Convert every source file in the corpus and score each page that has reference text.

    Layout: `<name>.pdf` or `<name>.docx` beside a `<name>/` folder of `page-NNN.reference.md` files.
    Raises CorpusError when the layout is wrong or there is nothing to score.
    `ocr` replaces the default OCR engine, for tests.
    """
    if not corpus.is_dir():
        raise CorpusError(f"not a folder: {corpus}")
    pages: list[PageReport] = []
    for source in sorted([*corpus.glob("*.pdf"), *corpus.glob("*.docx")]):
        references = _read_references(corpus / source.stem)
        if not references:
            continue
        result = convert(source.read_bytes(), ocr=ocr)
        outputs = split_pages(result.output.decode("utf-8"))
        summaries = {page.number: page for page in result.summary.pages}
        for number, reference in sorted(references.items()):
            if number not in summaries:
                raise CorpusError(f"{source.name} has no page {number}, but has reference text for it")
            score = score_page(outputs.get(number, ""), reference)
            summary = summaries[number]
            pages.append(PageReport(source.stem, number, summary.kind, score, summary.engine))
    if not pages:
        raise CorpusError(f"no reference text found in {corpus}")
    return Report(pages=tuple(pages))


def _read_references(folder: Path) -> dict[int, str]:
    if not folder.is_dir():
        return {}
    references = {}
    for path in folder.glob("*.reference.md"):
        match = _REFERENCE_FILE.match(path.name)
        if not match:
            raise CorpusError(f"reference file not named page-NNN.reference.md: {path}")
        references[int(match[1])] = path.read_text(encoding="utf-8-sig")
    return references
