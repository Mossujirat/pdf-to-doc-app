"""Word's list numbers: the number or bullet Word draws before a list paragraph, which the
text does not hold, worked out from the numbering definitions the way Word counts.

Counters belong to an abstract definition, so every list instance of one definition
counts on from the last, unless the instance overrides a level's start, as Word's
"Restart at 1" does, or redraws the level. Numbering a level restarts the levels below it.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement

_THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙"
# The Thai consonants Word numbers with, leaving out the obsolete ฃ and ฅ.
_THAI_LETTERS = "กขคงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ"
_ROMAN = (
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"),
    (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
)  # fmt: skip
_DEEPEST_LEVEL = 9


@dataclass(frozen=True)
class Label:
    """What Word draws before a list paragraph: a number such as "1.", "๑." or "(ก)", or a bullet."""

    text: str
    bullet: bool = False
    spaced: bool = True  # Word sets the text apart from the label, unless told to add nothing


@dataclass(frozen=True)
class _Level:
    start: int
    format: str
    pattern: str
    legal: bool  # every number in the pattern is drawn in Arabic digits
    restarts_after: int | None  # numbering this level, or one above it, restarts this one; None for never
    spaced: bool
    style: str | None  # the paragraph style the level numbers, in a heading list


@dataclass
class _Instance:
    abstract: str
    starts: dict[int, int]  # level to the start its overrides set
    levels: dict[int, _Level]  # levels the instance redraws
    used: bool = False


@dataclass
class Numbering:
    """The numbering definitions of one document, and the counts so far."""

    definitions: BaseOxmlElement | None
    # A list style's own numbering instance, for definitions that link to one.
    list_style_instance: Callable[[str], str | None]
    _levels: dict[str, dict[int, _Level]] = field(default_factory=dict)
    _links: dict[str, str] = field(default_factory=dict)  # definition to the list style it links to
    _instances: dict[str, _Instance] = field(default_factory=dict)
    _counts: dict[str, list[int | None]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.definitions is None:
            return
        for abstract in self.definitions.findall(qn("w:abstractNum")):
            abstract_id = abstract.get(qn("w:abstractNumId"))
            self._levels[abstract_id] = {_ilvl(level): _read_level(level) for level in abstract.findall(qn("w:lvl"))}
            link = abstract.find(qn("w:numStyleLink"))
            if link is not None:
                self._links[abstract_id] = link.get(qn("w:val"))
        for instance in self.definitions.findall(qn("w:num")):
            abstract = instance.find(qn("w:abstractNumId"))
            if abstract is None:
                continue
            overrides = instance.findall(qn("w:lvlOverride"))
            starts = {
                _ilvl(override): int(start.get(qn("w:val"), "1"))
                for override in overrides
                if (start := override.find(qn("w:startOverride"))) is not None
            }
            levels = {
                _ilvl(override): _read_level(level)
                for override in overrides
                if (level := override.find(qn("w:lvl"))) is not None
            }
            self._instances[instance.get(qn("w:numId"))] = _Instance(abstract.get(qn("w:val")), starts, levels)

    def label(self, instance_id: str, level: int, style: str | None) -> Label | None:
        """Count the paragraph in its list, and return what Word draws before it; None when it draws nothing.

        `style` is the paragraph's style when the style, not the paragraph, puts it in the list:
        a level that numbers some other style then neither numbers nor counts it, as in Word.
        """
        instance = self._instances.get(instance_id)
        abstract = self._abstract(instance)
        if instance is None or abstract is None:
            return None
        levels = self._levels[abstract] | instance.levels
        current = levels.get(level)
        if current is None or (style is not None and current.style is not None and current.style != style):
            return None
        counts = self._counts.setdefault(abstract, [None] * _DEEPEST_LEVEL)
        if not instance.used:
            instance.used = True
            for overridden, start in instance.starts.items():
                counts[overridden] = start - 1
        count = counts[level]
        counts[level] = current.start if count is None else count + 1
        for deeper, definition in levels.items():
            if deeper > level and definition.restarts_after is not None and level <= definition.restarts_after:
                counts[deeper] = None
        if current.format == "bullet":
            return Label(current.pattern, bullet=True, spaced=current.spaced)
        if current.format == "none":
            return Label("", spaced=False)
        text = current.pattern
        # From %9 down, so that %1 does not match the start of %10 and the like.
        for shown in range(_DEEPEST_LEVEL, 0, -1):
            placeholder = f"%{shown}"
            if placeholder in text and (shown_level := levels.get(shown - 1)) is not None:
                shown_count = counts[shown - 1]
                number = shown_level.start if shown_count is None else shown_count
                text = text.replace(placeholder, _format(number, "decimal" if current.legal else shown_level.format))
        return Label(text, spaced=current.spaced)

    def _abstract(self, instance: _Instance | None) -> str | None:
        """The definition the instance counts in, following a definition that only links to a list style."""
        seen: set[str] = set()
        while instance is not None and instance.abstract not in seen:
            seen.add(instance.abstract)
            if self._levels.get(instance.abstract):
                return instance.abstract
            linked = self._links.get(instance.abstract)
            instance = self._instances.get(self.list_style_instance(linked) or "") if linked else None
        return None


def _ilvl(element: BaseOxmlElement) -> int:
    return int(element.get(qn("w:ilvl"), "0"))


def _read_level(level: BaseOxmlElement) -> _Level:
    def value(tag: str, default: str) -> str:
        element = level.find(qn(tag))
        return default if element is None else element.get(qn("w:val"), default)

    restart = level.find(qn("w:lvlRestart"))
    ilvl = _ilvl(level)
    if restart is None:
        restarts_after: int | None = ilvl - 1 if ilvl > 0 else None  # any level above restarts it
    else:
        after = int(restart.get(qn("w:val"), "0"))  # Word counts these levels from 1; 0 is never
        restarts_after = None if after == 0 else after - 1
    style = level.find(qn("w:pStyle"))
    return _Level(
        start=int(value("w:start", "0")),
        format=value("w:numFmt", "decimal"),
        pattern=value("w:lvlText", ""),
        legal=level.find(qn("w:isLgl")) is not None,
        restarts_after=restarts_after,
        spaced=value("w:suff", "tab") != "nothing",
        style=None if style is None else style.get(qn("w:val")),
    )


def _format(number: int, number_format: str) -> str:
    """A count written in a Word number format; formats this reader does not know are written in Arabic digits."""
    match number_format:
        case "thaiNumbers":
            return str(number).translate(str.maketrans("0123456789", _THAI_DIGITS))
        case "thaiLetters":
            return _letters(number, _THAI_LETTERS)
        case "lowerLetter":
            return _letters(number, "abcdefghijklmnopqrstuvwxyz")
        case "upperLetter":
            return _letters(number, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        case "lowerRoman":
            return _roman(number)
        case "upperRoman":
            return _roman(number).upper()
        case "decimalZero":
            return f"{number:02d}"
    return str(number)


def _letters(number: int, alphabet: str) -> str:
    """Word's letter numbering: a, b, … z, then aa, bb, … zz, and so on."""
    if number < 1:
        return str(number)
    repeat, index = divmod(number - 1, len(alphabet))
    return alphabet[index] * (repeat + 1)


def _roman(number: int) -> str:
    if number < 1:
        return str(number)
    text = ""
    for value, letters in _ROMAN:
        while number >= value:
            text += letters
            number -= value
    return text
