"""What a sandbox sends back, read as untrusted.

Each event line is checked against its schema, and the parts on stdout against their
framing (the sandbox entry point's protocol, ticket 02). Anything else is `Malformed`,
whose message never quotes what was sent, as it could hold the document.
"""

from typing import Annotated, Literal, Self, get_args

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from pdf_to_doc.conversion import DocxToDocx, OutputFormat
from pdf_to_doc.intake import (
    MAX_BYTES,
    MAX_PAGES,
    MAX_UNPACKED_BYTES,
    CopyRestricted,
    DamagedFile,
    IntakeError,
    PasswordRequired,
    SizeUnit,
    SourceType,
    TooLarge,
    Unconverted,
    UnsupportedFormat,
    WrongPassword,
)
from pdf_to_doc.model import PageKind, PlaceholderKind
from pdf_to_doc.pdf_images import KEPT_DPI
from pdf_to_doc.progress import Stage
from pdf_to_doc.summary import PageSummary, Summary

# The longest event line taken: a summary of 150 pages is about 18 KB.
MAX_EVENT_LINE = 1024 * 1024
# A name the sandbox sends that the page shows, such as an OCR engine's, can hold no Thai
# and no more than a name's length, so it cannot carry the document's text.
_NAME = "^[A-Za-z][A-Za-z0-9 ._-]{0,39}$"
# The refusals that carry nothing but their kind.
PlainRefusal = Literal["DamagedFile", "PasswordRequired", "WrongPassword", "CopyRestricted", "DocxToDocx"]
_PLAIN_REFUSALS: dict[PlainRefusal, type[IntakeError]] = {
    "DamagedFile": DamagedFile,
    "PasswordRequired": PasswordRequired,
    "WrongPassword": WrongPassword,
    "CopyRestricted": CopyRestricted,
    "DocxToDocx": DocxToDocx,
}
# A file too large is refused at the service's own limits, and its size is shown: no larger
# than this, so that a sandbox cannot send a number too long to show.
_LIMITS: dict[SizeUnit, int] = {"bytes": MAX_BYTES, "pages": MAX_PAGES, "unpacked bytes": MAX_UNPACKED_BYTES}
_LARGEST_SIZE = 2**53


class Malformed(Exception):
    """What the sandbox sent does not follow the protocol."""


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class OpenedEvent(_Event):
    event: Literal["opened"]
    source_type: SourceType
    pages: int = Field(ge=0)


class ProgressEvent(_Event):
    event: Literal["progress"]
    stage: Stage
    current: int | None = Field(ge=1)
    total: int | None = Field(ge=1)


class _Page(_Event):
    number: int = Field(ge=1)
    kind: PageKind
    engine: str | None = Field(pattern=_NAME)
    untrusted_text_layer: bool
    placeholders: tuple[PlaceholderKind, ...]
    uncertain: int = Field(ge=0)


class SummaryEvent(_Event):
    event: Literal["summary"]
    pages: tuple[_Page, ...]
    # The resolution kept images were lowered to, below the one they are made at.
    images_lowered_to: int | None = Field(default=None, ge=1, lt=KEPT_DPI)

    def summary(self) -> Summary:
        return Summary(
            pages=tuple(PageSummary(**dict(page)) for page in self.pages), images_lowered_to=self.images_lowered_to
        )


class RefusalEvent(_Event):
    event: Literal["refusal"]
    kind: Literal["UnsupportedFormat", "TooLarge"] | PlainRefusal  # the intake errors' type names
    found: Unconverted | None = None
    unit: SizeUnit | None = None
    size: int | None = Field(default=None, ge=0, le=_LARGEST_SIZE)
    limit: int | None = None

    @model_validator(mode="after")
    def _details_fit_the_kind(self) -> Self:
        """A size only for a file too large, over the service's own limit; what was found only
        for an unsupported file."""
        if self.kind == "TooLarge":
            if self.unit is None or self.size is None or self.limit != _LIMITS[self.unit] or self.size <= self.limit:
                raise ValueError("a file too large without a size over the service's limit")
        elif (self.unit, self.size, self.limit) != (None, None, None):
            raise ValueError("a size for a refusal that has none")
        if self.found is not None and self.kind != "UnsupportedFormat":
            raise ValueError("a type found for a refusal that has none")
        return self

    def intake_error(self) -> IntakeError:
        """The intake error the sandbox refused the file with."""
        match self.kind:
            case "UnsupportedFormat":
                return UnsupportedFormat(self.found)
            case "TooLarge":
                assert self.unit is not None and self.size is not None and self.limit is not None
                return TooLarge(self.unit, self.size, self.limit)
            case _:
                return _PLAIN_REFUSALS[self.kind]()


class FailureEvent(_Event):
    event: Literal["failure"]
    error: str = Field(pattern=_NAME)  # an error's type name


Event = OpenedEvent | ProgressEvent | SummaryEvent | RefusalEvent | FailureEvent
_EVENTS: TypeAdapter[Event] = TypeAdapter(Annotated[Event, Field(discriminator="event")])


def read_event(line: bytes) -> Event:
    try:
        return _EVENTS.validate_json(line)
    except ValidationError:
        raise Malformed("an event that does not follow its schema") from None


def read_parts(stdout: bytes) -> dict[OutputFormat, bytes]:
    """The outputs in the parts on stdout: each a line with its format and length, then that many bytes."""
    outputs: dict[OutputFormat, bytes] = {}
    rest = stdout
    while rest:
        header, newline, rest = rest.partition(b"\n")
        name, _, length = header.partition(b" ")
        found = next((known for known in get_args(OutputFormat) if known.encode("ascii") == name), None)
        if not newline or found is None or found in outputs or not length.isdigit() or int(length) > len(rest):
            raise Malformed("parts that do not follow their framing")
        outputs[found], rest = rest[: int(length)], rest[int(length) :]
    return outputs
