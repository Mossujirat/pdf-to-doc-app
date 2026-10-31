"""Thai words: which of a text's Thai words PyThaiNLP's word list holds, and, for uncertain text,
which of them a reader should check."""

import re
from typing import NamedTuple

from pythainlp.corpus import thai_stopwords as pythainlp_common_words
from pythainlp.corpus import thai_wikipedia_titles as pythainlp_titles
from pythainlp.corpus import thai_words as pythainlp_word_list
from pythainlp.tokenize import word_tokenize

from pdf_to_doc.model import Span
from pdf_to_doc.thai import THAI_CONSONANT, THAI_LETTER, repair

_THAI = re.compile(THAI_LETTER)
_CONSONANT = re.compile(THAI_CONSONANT)
_CONSONANTS = re.compile(f"{THAI_CONSONANT}+")
_THAI_ONLY = re.compile(f"{THAI_LETTER}+")
# How many tokens either side of an unknown one may join it into a Thai Wikipedia title, and the
# shortest join: a shorter one too often makes a title of a misread, such as "ลั่ว" for "ถั่ว".
_REACH = 3
_SHORTEST_TITLE = 5
_LONGEST_ABBREVIATION = 4
# Mai yamok (repeat the word) and paiyannoi (abbreviation) are tokens of their
# own when they follow a word, and no word list has them.
NOT_WORDS = f"{chr(0x0E46)}{chr(0x0E2F)}"
# "ณ" ("at"), a word of one letter that the word list lacks.
_NA = chr(0x0E13)


def thai_words_in(text: str) -> list[str]:
    """The text's Thai words, as PyThaiNLP's dictionary-based tokenizer cuts them."""
    return [word for word in word_tokenize(text, engine="newmm", keep_whitespace=False) if _is_thai_word(word)]


def first_word(text: str) -> str:
    """The text's first word, as the word list's tokenizer cuts it: Thai by the dictionary, and
    other text at spaces and punctuation, so "(ก) ค่าวัสดุ" starts with "("."""
    return next(iter(word_tokenize(text.strip(), engine="newmm", keep_whitespace=False)), "")


def in_word_list(word: str) -> bool:
    words = pythainlp_word_list()
    return word in words or word.strip(NOT_WORDS) in words


def unknown_words(text: str) -> int:
    """How many of the text's Thai words are not in the word list."""
    return sum(1 for word in thai_words_in(repair(text)) if not in_word_list(word))


def unknown_word_spans(text: str) -> tuple[Span, ...]:
    """Where the text's Thai words that a reader should check stand, in order: those the word list
    lacks, judged as uncertain text judges OCR text. Unlike `unknown_words`, which judges a text
    layer, it accepts:
    - a word the tokenizer cut into pieces, if the pieces join into a Thai Wikipedia title, as
      "ฟอร์มัล" + "ดีไฮด์" do
    - words written so on purpose (see `_written_so_on_purpose`)
    """
    tokens = _tokens(text)
    unknown = [index for index, token in enumerate(tokens) if _is_thai_word(token.text) and not in_word_list(token.text)]
    known = {joined for index in unknown for joined in _in_a_title(text, tokens, index)}
    return tuple(
        _with_its_syllables(tokens, index)
        for index in unknown
        if index not in known and not _written_so_on_purpose(text, tokens[index])
    )


class _Token(NamedTuple):
    """A token the tokenizer cut the text into, and where it stands."""

    start: int
    end: int
    text: str


def _tokens(text: str) -> list[_Token]:
    """The tokens the tokenizer cuts the text into, whitespace included."""
    tokens = []
    position = 0
    for token in word_tokenize(text, engine="newmm", keep_whitespace=True):
        start = position if text.startswith(token, position) else text.find(token, position)
        if start < 0:
            continue
        position = start + len(token)
        tokens.append(_Token(start, position, token))
    return tokens


def _in_a_title(text: str, tokens: list[_Token], index: int) -> range:
    """The tokens around `index` that join into a Thai Wikipedia title of `_SHORTEST_TITLE`
    characters or more, or none."""
    for first in range(max(0, index - _REACH), index + 1):
        for last in range(min(len(tokens) - 1, index + _REACH), index - 1, -1):
            joined = text[tokens[first].start : tokens[last].end]
            if len(joined) >= _SHORTEST_TITLE and _THAI_ONLY.fullmatch(joined) and joined in pythainlp_titles():
                return range(first, last + 1)
    return range(0)


def _written_so_on_purpose(text: str, token: _Token) -> bool:
    """Whether a token the word list lacks is:
    - the one-letter word "ณ", standing alone, as in "ณ วันที่"; inside a word it is more likely a
      misread, as in "กุณภาพ" for "คุณภาพ"
    - a letter that lists an item, such as "(ก)"
    - in an abbreviation, consonants before a full stop, such as "บพข." or "ผพว.", which the
      tokenizer cuts as "ผ" + "พว."; not the end of a word, as "กข" in "ระบบกข."
    """
    start, end = token.start, token.end
    if token.text == _NA and (start == 0 or text[start - 1].isspace()) and (end == len(text) or text[end].isspace()):
        return True
    if _CONSONANT.fullmatch(token.text) and text[:start].endswith("(") and text[end:].startswith(")"):
        return True
    if not _CONSONANTS.fullmatch(token.text):
        return False
    while start > 0 and _CONSONANT.fullmatch(text[start - 1]):
        start -= 1
    while end < len(text) and _CONSONANT.fullmatch(text[end]):
        end += 1
    after_a_word = start > 0 and _THAI.fullmatch(text[start - 1]) is not None
    return not after_a_word and end - start <= _LONGEST_ABBREVIATION and text[end:].startswith(".")


def _with_its_syllables(tokens: list[_Token], index: int) -> Span:
    """Where an unknown token stands, with the syllables right beside it that are likely part of
    the same word: the tokenizer cuts a word it lacks into syllables of one consonant, as "ลิ" + "ก"
    + "โน" in "ลิกโนเซลลูโลสิก". Common words of one consonant, such as "ที่" and "จะ", stand
    apart."""
    start, end, _ = tokens[index]
    if index > 0 and _a_syllable_of_a_word(tokens[index - 1].text):
        start = tokens[index - 1].start
    if index + 1 < len(tokens) and _a_syllable_of_a_word(tokens[index + 1].text):
        end = tokens[index + 1].end
    return start, end


def _a_syllable_of_a_word(token: str) -> bool:
    return (
        _THAI_ONLY.fullmatch(token) is not None
        and len(_CONSONANT.findall(token)) == 1
        and token not in pythainlp_common_words()
    )


def _is_thai_word(token: str) -> bool:
    return bool(_THAI.search(token)) and bool(token.strip(NOT_WORDS))
