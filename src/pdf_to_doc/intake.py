"""Source intake: which source files the converter takes.

A source file's type comes from its content, never from its name. Each kind of
refusal is its own error type, so the command line and the web service can
explain it in their own words. Error messages never quote the file's content.
"""

import io
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

import pymupdf

# PyMuPDF copies its PDF_ constants in at run time, where type checkers cannot see them.
from pymupdf.mupdf import PDF_PERM_COPY

SourceType = Literal["pdf", "docx"]
# A type recognised and not converted: legacy Word, or an Office file locked with a password.
Unconverted = Literal["doc", "locked office"]
SizeUnit = Literal["bytes", "pages", "unpacked bytes"]

MAX_BYTES = 50 * 1024 * 1024
MAX_PAGES = 150
# A DOCX is a zip archive: one that unpacks to more than this is a zip bomb.
MAX_UNPACKED_BYTES = 200 * 1024 * 1024

# Readers accept a PDF whose header is preceded by up to 1 KB of other bytes.
_PDF_HEADER = b"%PDF-"
_PDF_HEADER_WITHIN = 1024
_ZIP_SIGNATURE = bytes.fromhex("504b0304")  # the container of DOCX files
_WORD_DOCUMENT_PART = "word/document.xml"
_OLE_SIGNATURE = bytes.fromhex("d0cf11e0a1b11ae1")  # the compound file container of Office 97-2003
_WORD_97_STREAM = "WordDocument".encode("utf-16-le")  # its directory names the streams it holds
# Office keeps a password-locked DOCX, XLSX or PPTX in one; which it is, is locked inside.
_LOCKED_OFFICE_STREAM = "EncryptedPackage".encode("utf-16-le")


class IntakeError(Exception):
    """A source file the converter cannot or will not convert."""


class UnsupportedFormat(IntakeError):
    """The source is not a type the converter reads.

    `found` names a type that was recognised and is not converted: "doc" for a
    legacy Word 97-2003 file, or "locked office" for an Office file locked with a
    password, most likely a DOCX, which would need decrypting even to tell. It is
    None for anything else.
    """

    def __init__(self, found: Unconverted | None) -> None:
        super().__init__(f"unsupported source type: {found or 'unknown'}")
        self.found = found


class TooLarge(IntakeError):
    """The source is over a limit: `size` is its size in `unit`, and `limit` the most allowed.
    A DOCX's "unpacked bytes" are what its zip archive holds once unpacked."""

    def __init__(self, unit: SizeUnit, size: int, limit: int) -> None:
        super().__init__(f"{size} {unit}, over the limit of {limit}")
        self.unit = unit
        self.size = size
        self.limit = limit


class DamagedFile(IntakeError):
    """The source looks like a PDF or DOCX but cannot be read, as when a download was cut short."""


class PasswordRequired(IntakeError):
    """The PDF needs a password to open, and none was given."""


class WrongPassword(IntakeError):
    """The password given does not open the PDF."""


class CopyRestricted(IntakeError):
    """The PDF's permissions forbid copying its text, so it is not converted."""


def admit(source: bytes) -> SourceType:
    """Admit a source file of a type the converter takes, within the size limit, and return its type."""
    found = _detect(source)
    if len(source) > MAX_BYTES:
        raise TooLarge("bytes", len(source), MAX_BYTES)
    return found


def _detect(source: bytes) -> SourceType:
    if source.startswith(_ZIP_SIGNATURE):
        try:
            with zipfile.ZipFile(io.BytesIO(source)) as archive:
                entries = archive.infolist()
        except zipfile.BadZipFile as error:
            raise DamagedFile() from error
        if _WORD_DOCUMENT_PART not in (entry.filename for entry in entries):
            raise UnsupportedFormat(None)
        # Reading a part never gives more than the size the archive lists for it.
        unpacked = sum(entry.file_size for entry in entries)
        if unpacked > MAX_UNPACKED_BYTES:
            raise TooLarge("unpacked bytes", unpacked, MAX_UNPACKED_BYTES)
        return "docx"
    if source.startswith(_OLE_SIGNATURE) and _LOCKED_OFFICE_STREAM in source:
        raise UnsupportedFormat("locked office")
    if source.startswith(_OLE_SIGNATURE) and _WORD_97_STREAM in source:
        raise UnsupportedFormat("doc")
    if _PDF_HEADER in source[:_PDF_HEADER_WITHIN]:
        return "pdf"
    raise UnsupportedFormat(None)


@contextmanager
def open_pdf(source: bytes, password: str | None) -> Iterator[pymupdf.Document]:
    """The PDF, opened with the password if it needs one, once it allows copying text and passes the page limit."""
    try:
        opened = pymupdf.open(stream=source, filetype="pdf")
    except pymupdf.FileDataError as error:
        raise DamagedFile() from error
    with opened as pdf:
        if pdf.needs_pass:
            if password is None:
                raise PasswordRequired()
            if not pdf.authenticate(password):
                raise WrongPassword()
        # PyMuPDF reads the text whatever the permissions say, so they are enforced here.
        if not _allows_copying(pdf):
            raise CopyRestricted()
        if pdf.page_count > MAX_PAGES:
            raise TooLarge("pages", pdf.page_count, MAX_PAGES)
        yield pdf


def _allows_copying(pdf: pymupdf.Document) -> bool:
    """Whether the PDF's own permissions allow copying its text.

    They are read from the file's encryption dictionary, because after the owner
    password opens a PDF, PyMuPDF reports every permission as granted.
    """
    kind, value = pdf.xref_get_key(-1, "Encrypt/P")
    return kind != "int" or bool(int(value) & PDF_PERM_COPY)
