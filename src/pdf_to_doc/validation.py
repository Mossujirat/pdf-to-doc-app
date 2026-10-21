"""Text-layer validation: whether a page's text layer says what the page shows."""

import re

from pdf_to_doc.layout import PageRows
from pdf_to_doc.thai import MARK, SARA_AM, THAI_CONSONANT, repair
from pdf_to_doc.words import in_word_list, thai_words_in

# Thai words are checked against PyThaiNLP's word list. A text layer whose words
# are dictionary words less often than this is wrong, as when a font's ToUnicode
# map turns "การ" into "กำร". On the real contract, text pages scored 0.982 or
# more, and the four pages with that broken map 0.781 to 0.910.
_MIN_DICTIONARY_SHARE = 0.95
# Fewer Thai words than this are too few to judge, such as a page of names.
_MIN_WORDS_TO_JUDGE = 20
# A correct text layer never holds these: the replacement character and NUL,
# which glyphs without a Unicode mapping become, and Private Use Area
# characters that are neither legacy Thai glyphs (repair maps those back) nor
# symbol-font glyphs such as bullets.
_UNREADABLE = re.compile(f"[{chr(0xFFFD)}{chr(0)}{chr(0xE000)}-{chr(0xEFFF)}{chr(0xF100)}-{chr(0xF8FF)}]")
# Sara am follows a consonant or a tone mark, and nothing but a letter follows it.
_TONE_MARK = f"[{chr(0x0E48)}-{chr(0x0E4B)}]"
_SARA_AM_ANOMALY = re.compile(f"{SARA_AM}{MARK}|(?<!{THAI_CONSONANT})(?<!{_TONE_MARK}){SARA_AM}")


def trusted(page: PageRows) -> bool:
    """Whether the page's text layer can be read as it is."""
    text = repair(" ".join([row.text for row in page.rows] + _cell_lines(page)))
    if _UNREADABLE.search(text) or _SARA_AM_ANOMALY.search(text):
        return False
    words = thai_words_in(text)
    if len(words) < _MIN_WORDS_TO_JUDGE:
        return True
    return sum(1 for word in words if in_word_list(word)) / len(words) >= _MIN_DICTIONARY_SHARE


def _cell_lines(page: PageRows) -> list[str]:
    return [line for table in page.tables for row in table.rows for cell in row for line in cell.lines]
