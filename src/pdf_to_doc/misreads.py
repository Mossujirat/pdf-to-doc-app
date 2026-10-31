"""Misread shapes: words and numbers whose shape shows a typical OCR misread, though the engine
read them with confidence. English words and numbers are not looked up in a word list, since a
contract's names, codes and abbreviations would fill it with false alarms."""

import re

from pdf_to_doc.model import Span
from pdf_to_doc.thai import DIGIT, DIGITS, THAI_DIGIT, THAI_LETTER
from pdf_to_doc.words import NOT_WORDS

# Letters OCR reads in place of a digit, and the digit each stands for. o, O, l and I count
# anywhere in a number; S, B and Z only between two digits, so that codes such as "S1" pass.
_LOOK_ALIKE_DIGITS = {"o": "0", "O": "0", "l": "1", "I": "1"}
_LOOK_ALIKE_BETWEEN_DIGITS = {"S": "5", "B": "8", "Z": "2"}
_LOOK_ALIKE_LETTERS = "".join(_LOOK_ALIKE_DIGITS | _LOOK_ALIKE_BETWEEN_DIGITS)
_NUMBER_CHARACTER = rf"(?:{DIGIT}|[{_LOOK_ALIKE_LETTERS}])"
# Digits and the letters above, with the separators between them, as a whole: a match never stops
# short of the end of a longer word or code, such as "1O1A".
_NUMBER_LIKE = re.compile(
    rf"(?<![A-Za-z]|{DIGIT})(?>{_NUMBER_CHARACTER}+(?:[.,]{_NUMBER_CHARACTER}+)*)%?(?![A-Za-z]|{DIGIT})"
)
# Look-alike letters before a separator lead a clause's number, as the Roman numerals of "I.2" do.
_ROMAN_NUMERAL_BEFORE_A_NUMBER = re.compile(rf"[{_LOOK_ALIKE_LETTERS}]+[.,]")
_NUMBER = re.compile(rf"{DIGITS}(?:[.,]{DIGITS})*")
_LATIN_WORD = re.compile(r"[A-Za-z]+")
# Small letters shaped like their capitals, and l, which OCR reads in place of I.
_LOOK_ALIKE_SMALL = frozenset("cosuvwxzkpl")
_O_FOR_OF = re.compile(r"(?<=[A-Z])o(?=[A-Z])")
# Runs of Latin letters, and of Thai letters, marks and digits.
_SCRIPT_RUN = re.compile(rf"[A-Za-z]+|(?:{THAI_LETTER}|{THAI_DIGIT})+")


def misread_spans(text: str) -> tuple[Span, ...]:
    """Where the text's words and numbers are shaped like a misread, in order."""
    numbers = [match.span() for match in _NUMBER_LIKE.finditer(text) if _letters_in_a_number(match.group())]
    numbers += [match.span() for match in _NUMBER.finditer(text) if _thai_and_arabic_digits(match.group())]
    words = [
        match.span()
        for match in _LATIN_WORD.finditer(text)
        if _l_read_for_i(match.group()) or _small_letter_among_capitals(match.group())
    ]
    return tuple(sorted(numbers + words + _thai_letters_in_latin_words(text)))


def _thai_letters_in_latin_words(text: str) -> list[Span]:
    """Latin words that hold a single Thai letter or digit, or are joined to one, such as "Teamร":
    the Thai recogniser reads s as ร, n as ท, u as น and o as Thai zero. Thai text joined to a
    Latin word on purpose, such as "บริษัทABC", is longer than one letter."""
    runs = list(_SCRIPT_RUN.finditer(text))
    spans = []
    for before, run, after in zip([None, *runs], runs, [*runs[1:], None]):
        if run.group().isascii() or len(run.group()) != 1 or run.group() in NOT_WORDS:
            continue
        latin_before = before if before and before.end() == run.start() and before.group().isascii() else None
        latin_after = after if after and after.start() == run.end() and after.group().isascii() else None
        if latin_before or latin_after:
            spans.append(((latin_before or run).start(), (latin_after or run).end()))
    return spans


def _letters_in_a_number(candidate: str) -> bool:
    """Whether the candidate holds a digit, and becomes a number when its look-alike letters are read as digits."""
    if not re.search(DIGIT, candidate) or _ROMAN_NUMERAL_BEFORE_A_NUMBER.match(candidate):
        return False
    read = "".join(
        _LOOK_ALIKE_DIGITS.get(character)
        or (
            _LOOK_ALIKE_BETWEEN_DIGITS.get(character)
            if 0 < index < len(candidate) - 1 and candidate[index - 1].isdigit() and candidate[index + 1].isdigit()
            else None
        )
        or character
        for index, character in enumerate(candidate)
    )
    return read != candidate and _NUMBER.fullmatch(read.removesuffix("%")) is not None


def _thai_and_arabic_digits(number: str) -> bool:
    """Whether a number is written in both Thai and Arabic digits, as when one digit was misread."""
    return len({digit.isascii() for digit in number if digit.isdigit()}) == 2


def _l_read_for_i(word: str) -> bool:
    """Whether a word spelt only with l and I holds an l, such as "l" or "Il" for the Roman
    numerals I and II. "Ill" is the only English word spelt so."""
    return "l" in word and set(word) <= {"l", "I"} and word != "Ill"


def _small_letter_among_capitals(word: str) -> bool:
    """Whether a word in capitals holds small letters, each shaped like its capital, such as "BKk".
    A plural s ("PDFs"), hertz ("MHz") and an o between capitals that stands for "of" ("ToR",
    "MoU") are written small on purpose."""
    word = _O_FOR_OF.sub("", word)
    if word.endswith("Hz"):
        word = word[:-2]
    elif word.endswith("s") and word[:-1].isupper():
        word = word[:-1]
    small = {letter for letter in word if letter.islower()}
    return sum(letter.isupper() for letter in word) >= 2 and bool(small) and small <= _LOOK_ALIKE_SMALL
