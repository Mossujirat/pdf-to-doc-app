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
THAI_CONSONANT = r"[\u0e01-\u0e2e]"
# Arabic or Thai digits; int() reads both.
DIGITS = r"[0-9\u0e50-\u0e59]+"
# Marks above and below a consonant (mai han-akat, sara i to phinthu,
# maitaikhu to yamakkan) and sara am. None of them can start a word.
MARK = r"[\u0e31\u0e33-\u0e3a\u0e47-\u0e4e]"
_SPACE_BEFORE_MARK = re.compile(rf"(?<={THAI_LETTER})\s+(?={MARK})")
# Sara aa stored before nikhahit instead of after it.
_SARA_AA_NIKHAHIT = "\u0e32\u0e4d"


# Legacy Thai fonts draw marks shifted left or down, and consonants without their
# lower part, as glyphs of their own, and report them as Private Use Area
# characters: Windows fonts in U+F700-F71A, Mac fonts in U+F884-F89E. This is
# HarfBuzz's Thai shaper table (src/hb-ot-shaper-thai.cc) as (Thai, Windows, Mac).
_LEGACY_GLYPHS = (
    # Shifted down
    (0x0E48, 0xF70A, 0xF88B), (0x0E49, 0xF70B, 0xF88E), (0x0E4A, 0xF70C, 0xF891), (0x0E4B, 0xF70D, 0xF894),
    (0x0E4C, 0xF70E, 0xF897), (0x0E38, 0xF718, 0xF89B), (0x0E39, 0xF719, 0xF89C), (0x0E3A, 0xF71A, 0xF89D),
    # Shifted down and left
    (0x0E48, 0xF705, 0xF88C), (0x0E49, 0xF706, 0xF88F), (0x0E4A, 0xF707, 0xF892), (0x0E4B, 0xF708, 0xF895),
    (0x0E4C, 0xF709, 0xF898),
    # Shifted left
    (0x0E48, 0xF713, 0xF88A), (0x0E49, 0xF714, 0xF88D), (0x0E4A, 0xF715, 0xF890), (0x0E4B, 0xF716, 0xF893),
    (0x0E4C, 0xF717, 0xF896), (0x0E31, 0xF710, 0xF884), (0x0E34, 0xF701, 0xF885), (0x0E35, 0xF702, 0xF886),
    (0x0E36, 0xF703, 0xF887), (0x0E37, 0xF704, 0xF888), (0x0E47, 0xF712, 0xF889), (0x0E4D, 0xF711, 0xF899),
    # Without the lower part: yo ying and tho than
    (0x0E0D, 0xF70F, 0xF89A), (0x0E10, 0xF700, 0xF89E),
)
_FROM_LEGACY_GLYPHS = str.maketrans(
    {legacy: thai for thai, windows, mac in _LEGACY_GLYPHS for legacy in (windows, mac)}
)


def repair(text: str) -> str:
    """Fix character-level damage in running text, without deleting any letter.

    Maps legacy fonts' Private Use Area glyphs back to Thai, removes invisible
    characters and spaces in front of Thai marks, recomposes sara am and puts
    vowels and tone marks in standard order.
    """
    text = text.translate(_FROM_LEGACY_GLYPHS)
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
