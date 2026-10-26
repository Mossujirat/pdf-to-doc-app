"""Thai words: which of a text's Thai words PyThaiNLP's word list holds."""

import re

from pythainlp.corpus import thai_words as pythainlp_word_list
from pythainlp.tokenize import word_tokenize

from pdf_to_doc.model import Span
from pdf_to_doc.thai import THAI_LETTER, repair

_THAI = re.compile(THAI_LETTER)
# Mai yamok (repeat the word) and paiyannoi (abbreviation) are tokens of their
# own when they follow a word, and no word list has them.
_NOT_WORDS = f"{chr(0x0E46)}{chr(0x0E2F)}"


def thai_words_in(text: str) -> list[str]:
    """The text's Thai words, as PyThaiNLP's dictionary-based tokenizer cuts them."""
    return [word for word in word_tokenize(text, engine="newmm", keep_whitespace=False) if _is_thai_word(word)]


def first_word(text: str) -> str:
    """The text's first word: Thai as the word list's tokenizer cuts it, other text up to a space."""
    return next(iter(word_tokenize(text.strip(), engine="newmm", keep_whitespace=False)), "")


def in_word_list(word: str) -> bool:
    words = pythainlp_word_list()
    return word in words or word.strip(_NOT_WORDS) in words


def unknown_words(text: str) -> int:
    """How many of the text's Thai words are not in the word list."""
    return sum(1 for word in thai_words_in(repair(text)) if not in_word_list(word))


def unknown_word_spans(text: str) -> tuple[Span, ...]:
    """Where the text's Thai words that are not in the word list stand, in order."""
    spans = []
    position = 0
    for token in word_tokenize(text, engine="newmm", keep_whitespace=True):
        start = position if text.startswith(token, position) else text.find(token, position)
        if start < 0:
            continue
        position = start + len(token)
        if _is_thai_word(token) and not in_word_list(token):
            spans.append((start, position))
    return tuple(spans)


def _is_thai_word(token: str) -> bool:
    return bool(_THAI.search(token)) and bool(token.strip(_NOT_WORDS))
