"""Thai-aware text repair: the rules that keep Thai words whole.

Never apply NFKC to Thai: it decomposes sara am into nikhahit + sara aa.
PyThaiNLP's `normalize` is not used either: its dangling-mark and
repeated-vowel steps delete characters.
"""

import re

from pythainlp.util import reorder_vowels

SARA_AM = "\u0e33"
SOFT_HYPHEN = "\u00ad"
# Zero-width space, non-joiner, joiner, word joiner and byte order mark.
ZERO_WIDTH = "\u200b\u200c\u200d\u2060\ufeff"

_INVISIBLE = re.compile(f"[{ZERO_WIDTH}{SOFT_HYPHEN}]")
# Thai consonants, vowels and marks: everything from ko kai to yamakkan.
THAI_LETTER = r"[\u0e01-\u0e4e]"
# Marks above and below a consonant (mai han-akat, sara i to phinthu,
# maitaikhu to yamakkan) and sara am. None of them can start a word.
MARK = r"[\u0e31\u0e33-\u0e3a\u0e47-\u0e4e]"
_SPACE_BEFORE_MARK = re.compile(rf"(?<={THAI_LETTER})\s+(?={MARK})")
# Sara aa stored before nikhahit instead of after it.
_SARA_AA_NIKHAHIT = "\u0e32\u0e4d"


def repair(text: str) -> str:
    """Fix character-level damage in running text, without deleting any letter.

    Removes invisible characters and spaces in front of Thai marks,
    recomposes sara am and puts vowels and tone marks in standard order.
    """
    text = _INVISIBLE.sub("", text)
    text = _SPACE_BEFORE_MARK.sub("", text)
    text = text.replace(_SARA_AA_NIKHAHIT, SARA_AM)
    return reorder_vowels(text)


def is_thai(char: str) -> bool:
    return "\u0e00" <= char <= "\u0e7f"


def join_lines(lines: list[str]) -> str:
    """Rejoin the printed lines of one paragraph into running text.

    - Thai + Thai: no space. Thai has no spaces between words, so a line
      break between two Thai characters is not a word boundary.
    - A line that wrapped at a real space keeps exactly one space.
    - A hyphen inside a word is kept and the word rejoined; Word breaks lines
      after hyphens that belong to the word, such as "long-term".
    - A soft hyphen is dropped and the word rejoined.
    - Anything else: one space.
    """
    text = ""
    for line in lines:
        line = line.strip(ZERO_WIDTH).lstrip()
        if not line:
            continue
        text = text.rstrip(ZERO_WIDTH)
        if not text:
            text = line
        elif text[-1].isspace():
            text = text.rstrip() + " " + line
        elif text[-1] == SOFT_HYPHEN:
            text = text[:-1] + line
        elif _ends_with_hyphen_inside_a_word(text) and line[0].isalnum():
            text += line
        elif is_thai(text[-1]) and is_thai(line[0]):
            text += line
        else:
            text += " " + line
    return text.rstrip()


def _ends_with_hyphen_inside_a_word(text: str) -> bool:
    return len(text) > 1 and text[-1] == "-" and text[-2].isalnum()
