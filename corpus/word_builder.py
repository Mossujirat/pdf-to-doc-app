"""Builds small Word files from scratch, so tests need no Word install.

- `docx` writes a minimal DOCX: the three parts Word needs to open a one-paragraph document.
- `legacy_doc` writes a Word 97-2003 .doc container: a compound file holding a
  WordDocument stream that starts with the Word 97 file information block. The
  stream holds nothing else, so the file is real enough to identify but Word
  would not open it.

The same inputs always give the same bytes.
"""

import io
import struct
import zipfile
from xml.sax.saxutils import escape

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml"'
    ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_RELATIONSHIPS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1"'
    ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
    ' Target="word/document.xml"/>'
    "</Relationships>"
)


def docx(text: str) -> bytes:
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    parts = {"[Content_Types].xml": _CONTENT_TYPES, "_rels/.rels": _RELATIONSHIPS, "word/document.xml": document}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in parts.items():
            # A fixed timestamp keeps the bytes the same on every run.
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), content, zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


# Compound file layout (version 3, 512-byte sectors): the header, then sector 0
# holds the allocation table, sector 1 the directory, and sectors 2-9 the stream.
_SECTOR = 512
_FREE = 0xFFFFFFFF
_END_OF_CHAIN = 0xFFFFFFFE
_FAT_SECTOR = 0xFFFFFFFD
_NO_STREAM = 0xFFFFFFFF
# Name, name length, kind, colour, left and right siblings, child, class id,
# state bits, creation and modification times, first sector, size.
_DIRECTORY_ENTRY = struct.Struct("<64sHBBIII16sIQQIQ")
_UNUSED, _STREAM_OBJECT, _ROOT_STORAGE = 0, 2, 5
_RED, _BLACK = 0, 1  # the directory is a red-black tree
_STREAM_SIZE = 4096  # the smallest size kept in ordinary sectors rather than the mini stream
_WORD_97_FIB = struct.pack("<HH", 0xA5EC, 0x00C1)  # wIdent, nFib


def legacy_doc() -> bytes:
    stream_sectors = _STREAM_SIZE // _SECTOR
    header = struct.pack(
        "<8s16sHHHHH6sIIIIIIIII",
        bytes.fromhex("d0cf11e0a1b11ae1"),  # signature
        bytes(16),  # class id
        0x003E,  # minor version
        0x0003,  # major version
        0xFFFE,  # byte order: little-endian
        9,  # sector size 2**9
        6,  # mini sector size 2**6
        bytes(6),
        0,  # directory sectors (always 0 in version 3)
        1,  # allocation table sectors
        1,  # first directory sector
        0,  # transaction signature
        _STREAM_SIZE,  # mini stream cutoff
        _END_OF_CHAIN,  # first mini allocation table sector: none
        0,
        _END_OF_CHAIN,  # first extra allocation table sector: none
        0,
    ) + struct.pack("<109I", 0, *[_FREE] * 108)
    chain = [_FAT_SECTOR, _END_OF_CHAIN] + [2 + i + 1 for i in range(stream_sectors - 1)] + [_END_OF_CHAIN]
    allocation_table = struct.pack(f"<{_SECTOR // 4}I", *chain, *[_FREE] * (_SECTOR // 4 - len(chain)))
    directory = (
        _directory_entry("Root Entry", _ROOT_STORAGE, child=1, start=_END_OF_CHAIN)
        + _directory_entry("WordDocument", _STREAM_OBJECT, start=2, size=_STREAM_SIZE)
        + _directory_entry("", _UNUSED) * 2
    )
    word_document = _WORD_97_FIB.ljust(_STREAM_SIZE, b"\0")
    return header + allocation_table + directory + word_document


def _directory_entry(name: str, kind: int, *, child: int = _NO_STREAM, start: int = 0, size: int = 0) -> bytes:
    """An entry of the directory; an unused entry has no name."""
    encoded = (name + "\0").encode("utf-16-le") if name else b""
    colour = _BLACK if name else _RED
    return _DIRECTORY_ENTRY.pack(
        encoded, len(encoded), kind, colour, _NO_STREAM, _NO_STREAM, child, bytes(16), 0, 0, 0, start, size
    )
