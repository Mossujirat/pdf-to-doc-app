"""Reading an upload: the file in a multipart form, with the form's other fields, held in memory
and never written to disk.

An upload is refused as soon as it passes the size limit: from its Content-Length when
it says one, otherwise while it is being read.
"""

from dataclasses import dataclass, field

from fastapi import Request
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header

from pdf_to_doc.intake import MAX_BYTES

# Room for the form's own framing around a file of the largest size taken.
_FRAMING = 64 * 1024
_FILE_FIELD = "file"


class UploadTooLarge(Exception):
    """The upload is over the size limit."""


class NotAnUpload(Exception):
    """The request holds no multipart form with a file in it."""


@dataclass(frozen=True)
class Upload:
    source: bytes
    file_name: str  # as the browser named it
    fields: dict[str, str]  # the form's other fields, such as the bot check's token


@dataclass
class _Part:
    headers: dict[bytes, bytes] = field(default_factory=dict)
    data: bytearray = field(default_factory=bytearray)
    # The header being read, which arrives in pieces.
    header_name: bytearray = field(default_factory=bytearray)
    header_value: bytearray = field(default_factory=bytearray)


async def read_upload(request: Request) -> Upload:
    content_type, options = parse_options_header(request.headers.get("content-type"))
    if content_type != b"multipart/form-data" or b"boundary" not in options:
        raise NotAnUpload()
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BYTES + _FRAMING:
        raise UploadTooLarge()
    source: bytes | None = None
    file_name = ""
    fields: dict[str, str] = {}
    for part in await _read_parts(request, options[b"boundary"]):
        disposition, details = parse_options_header(part.headers.get(b"content-disposition"))
        if disposition != b"form-data" or b"name" not in details:
            continue
        name = details[b"name"].decode("utf-8", errors="replace")
        if name != _FILE_FIELD or b"filename" not in details:
            fields[name] = part.data.decode("utf-8", errors="replace")
        elif source is None:  # the form has one file; any other is ignored
            if len(part.data) > MAX_BYTES:
                raise UploadTooLarge()
            source, file_name = bytes(part.data), details[b"filename"].decode("utf-8", errors="replace")
    if source is None:
        raise NotAnUpload()
    return Upload(source, file_name, fields)


async def _read_parts(request: Request, boundary: bytes) -> list[_Part]:
    parts: list[_Part] = []

    def on_part_begin() -> None:
        parts.append(_Part())

    def on_header_field(data: bytes, start: int, end: int) -> None:
        parts[-1].header_name += data[start:end]

    def on_header_value(data: bytes, start: int, end: int) -> None:
        parts[-1].header_value += data[start:end]

    def on_header_end() -> None:
        part = parts[-1]
        part.headers[bytes(part.header_name).lower()] = bytes(part.header_value)
        part.header_name, part.header_value = bytearray(), bytearray()

    def on_part_data(data: bytes, start: int, end: int) -> None:
        parts[-1].data += data[start:end]

    parser = MultipartParser(
        boundary,
        {
            "on_part_begin": on_part_begin,
            "on_header_field": on_header_field,
            "on_header_value": on_header_value,
            "on_header_end": on_header_end,
            "on_part_data": on_part_data,
        },
    )
    received = 0
    try:
        async for chunk in request.stream():
            received += len(chunk)
            if received > MAX_BYTES + _FRAMING:
                raise UploadTooLarge()
            parser.write(chunk)
        parser.finalize()
    except MultipartParseError:
        raise NotAnUpload() from None
    return parts
