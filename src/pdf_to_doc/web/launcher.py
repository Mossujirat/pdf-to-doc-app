"""The launcher, and the web app's way to reach it (ADR 0004).

The launcher is the only part of the web service with access to Docker. It converts each source
file in a throwaway container of its own, and the web app reaches it through a socket that only
the two of them share.

Over that socket, each side sends frames: a line with the frame's kind and its payload's length
in bytes, then the payload, as the sandbox entry point frames its parts. For one conversion, the
web app opens a connection and sends a `run` frame holding the source file. The launcher sends
back an `event` frame for each event line, then the sandbox's `stdout`, then `ended`.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager, suppress
from functools import partial
from typing import Protocol, Self

from pydantic import BaseModel, ConfigDict

from pdf_to_doc.intake import MAX_BYTES, MAX_OUTPUTS
from pdf_to_doc.web.docker import DockerEngine, Stream
from pdf_to_doc.web.protocol import MAX_EVENT_LINE, Malformed, read_event
from pdf_to_doc.web.sandboxes import Ended, Usage
from pdf_to_doc.web.settings import LauncherSettings, Misconfigured, from_environment

MAX_SANDBOXES = 3  # running at once
# On a volume that only the web app and the launcher share; the image makes the folder.
SOCKET = "/run/pdf-to-doc/launcher.sock"
_log = logging.getLogger(__name__)
# Each frame's kind, and the longest payload it may have, as each side reads them.
_FROM_THE_WEB_APP = {"run": MAX_BYTES}
_FROM_THE_LAUNCHER = {"event": MAX_EVENT_LINE, "stdout": MAX_OUTPUTS, "ended": 1024}
_LONGEST_LENGTH = len(str(MAX_OUTPUTS))  # in digits
_PIECE = 64 * 1024  # bytes read at a time
# Seconds the web app waits for a cancelled conversion's sandbox to be removed.
_STOPPING_TAKES_AT_MOST = 60
# Seconds the web app waits for a launcher that does not listen yet, trying again every so often.
_STARTING_TAKES_AT_MOST = 30
_TRY_AGAIN_AFTER = 0.5


class BrokenFrames(Exception):
    """What came over the launcher's socket is not a frame that may come there, or stops partway."""


class Container(Protocol):
    """A sandbox's container, started with the source file on its stdin."""

    async def read(self) -> tuple[Stream, bytes] | None:
        """The next piece of what the sandbox writes, on stdout or stderr, as it comes; None
        once it has closed both."""
        ...

    async def wait(self) -> int:
        """Its exit code, once it has stopped."""
        ...

    async def kill(self) -> None:
        """Stop it now, if it still runs."""
        ...

    def usage(self) -> Usage | None:
        """What it has used so far, if Docker's stats have said."""
        ...


class Docker(Protocol):
    def sandbox(self, source: bytes) -> AbstractAsyncContextManager[Container]:
        """A sandbox converting `source`, removed on leaving, however the conversion ends."""
        ...

    async def remove_leftovers(self) -> None:
        """Remove every sandbox of the launcher's environment, such as a launcher that stopped
        can leave."""
        ...


Send = Callable[[bytes | Ended], Awaitable[None]]


class Launcher:
    """Converts each source file in a sandbox of its own, started with `docker`: at most
    `MAX_SANDBOXES` at once, as a backstop to the web app's queue, and the rest wait for a place."""

    def __init__(self, docker: Docker, *, time_limit: float) -> None:
        self._docker = docker
        self._time_limit = time_limit
        self._places = asyncio.Semaphore(MAX_SANDBOXES)

    async def run(self, source: bytes, send: Send) -> None:
        """Convert the source file: send each event line as it comes, then how it ended. A
        conversion past the time limit is stopped, and ends as timed out. What the sandbox writes
        is untrusted, so each line is checked first; raises `Malformed` for a line that does not
        follow its schema or is too long, or for outputs too large in all. However it ends, the
        sandbox is removed. The time limit starts once the conversion has a place."""
        async with self._places, self._docker.sandbox(source) as sandbox:
            try:
                async with asyncio.timeout(self._time_limit) as limit:
                    exit_code, stdout = await _relay(sandbox, send)
            except TimeoutError:
                if not limit.expired():
                    raise
                await sandbox.kill()
                await send(Ended(await sandbox.wait(), b"", timed_out=True, usage=sandbox.usage()))
            else:
                await send(Ended(exit_code, stdout, usage=sandbox.usage()))


async def _relay(sandbox: Container, send: Send) -> tuple[int, bytes]:
    """Send each event line the sandbox writes, once checked, and gather its outputs, until it has
    stopped. Returns its exit code and its outputs."""
    pending = bytearray()  # stderr since its last full line
    stdout = bytearray()
    while (piece := await sandbox.read()) is not None:
        stream, data = piece
        if stream == "stdout":
            stdout += data
            if len(stdout) > MAX_OUTPUTS:
                raise Malformed("outputs over their cap")
            continue
        pending += data
        while (end := pending.find(b"\n")) >= 0:
            line = bytes(pending[:end])
            del pending[: end + 1]
            await send(_checked(line))
        if len(pending) > MAX_EVENT_LINE:
            raise Malformed("an event line over its cap")
    if pending:
        raise Malformed("an event line cut short")
    return await sandbox.wait(), bytes(stdout)


def _checked(line: bytes) -> bytes:
    if len(line) > MAX_EVENT_LINE:
        raise Malformed("an event line over its cap")
    read_event(line)
    return line


def main() -> int:
    """`pdf-to-doc-launcher`: the launcher, as its container runs it, with its settings from the
    environment and Docker's socket mounted."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # it would log each request to Docker
    try:
        settings = from_environment(LauncherSettings)
    except Misconfigured as error:
        _log.error("%s", error)
        return 1
    asyncio.run(_launch(settings))
    return 0


async def _launch(settings: LauncherSettings) -> None:
    # Docker stops a container with SIGTERM. The conversions then stop, and their sandboxes go.
    stopping = asyncio.current_task()
    assert stopping is not None
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stopping.cancel)
    docker = await DockerEngine.of_this_container(environment=settings.environment, runtime=settings.sandbox_runtime)
    _log.info("started")
    try:
        await serve(docker, time_limit=settings.time_limit)
    except asyncio.CancelledError:
        _log.info("stopped")


async def serve(docker: Docker, *, time_limit: float, path: str = SOCKET) -> None:
    """Take the web app's conversions on the Unix socket at `path` until cancelled, converting
    in sandboxes started with `docker`. Leftover sandboxes are removed first, and again once the
    running conversions have been told to stop."""
    if sys.platform == "win32":
        raise NotImplementedError("the launcher listens on a Unix socket, on the server")
    await docker.remove_leftovers()
    with suppress(FileNotFoundError):
        os.unlink(path)  # left by a launcher that stopped
    server = await asyncio.start_unix_server(partial(serve_connection, Launcher(docker, time_limit=time_limit)), path)
    try:
        await asyncio.get_running_loop().create_future()  # until cancelled
    finally:
        server.close()
        server.close_clients()  # each conversion then stops, and its sandbox is removed
        await server.wait_closed()
        await docker.remove_leftovers()


async def serve_connection(launcher: Launcher, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """One conversion, for one connection from the web app. A conversion that fails ends without
    an `ended` frame. A `cancel` frame, or anything else the web app sends, or its closing the
    connection, stops the conversion; the connection is closed once its sandbox has been removed."""
    try:
        _, source = await _receive(reader, _FROM_THE_WEB_APP)
    except BrokenFrames:
        writer.close()
        return
    ending = asyncio.Event()  # the conversion has ended, and the web app is being told how

    async def send(item: bytes | Ended) -> None:
        if isinstance(item, Ended):
            ending.set()
        await _send_item(writer, item)

    converting = asyncio.create_task(launcher.run(source, send))
    stopping = asyncio.create_task(reader.read(1))  # a cancel, or the web app gone
    try:
        await asyncio.wait((converting, stopping), return_when=asyncio.FIRST_COMPLETED)
        # Once told how it ended, the web app closes the connection: that is no cancel, and
        # must not interrupt the sandbox's removal.
        if not ending.is_set():
            converting.cancel()
        await asyncio.wait((converting,))
    finally:
        stopping.cancel()
        converting.cancel()  # still running only when the launcher itself stops
        await asyncio.wait((converting, stopping))
        writer.close()
    if not converting.cancelled() and (error := converting.exception()) is not None:
        # Only the type: a message could quote what the sandbox sent.
        _log.warning("conversion failed: %s", type(error).__name__)
    if not stopping.cancelled():
        stopping.exception()  # retrieved, as nothing is to be done about it


class LauncherSandbox:
    """Conversions in the launcher's sandboxes, reached through its socket. A conversion stopped
    early is cancelled, and stopping it waits until its sandbox has been removed, so that the web
    app frees its place only then."""

    def __init__(self, connect: Callable[[], Awaitable[tuple[asyncio.StreamReader, asyncio.StreamWriter]]]) -> None:
        self._connect = connect

    @classmethod
    def at(cls, path: str = SOCKET) -> Self:
        """The launcher listening on the Unix socket at `path`."""
        if sys.platform == "win32":
            raise NotImplementedError("the launcher listens on a Unix socket, on the server")
        return cls(partial(asyncio.open_unix_connection, path))

    async def convert(self, source: bytes) -> AsyncGenerator[bytes | Ended]:
        reader, writer = await self._connected()
        ended = False
        try:
            await _send(writer, "run", source)
            stdout = b""
            while not ended:
                kind, payload = await _receive(reader, _FROM_THE_LAUNCHER)
                if kind == "event":
                    yield payload
                elif kind == "stdout":
                    stdout = payload
                else:
                    ended = True
                    yield _ended(payload, stdout)
        finally:
            if not ended:
                await _cancel(reader, writer)
            writer.close()

    async def _connected(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """A connection to the launcher, waiting for it while it starts, or starts again: it
        listens only some seconds after it starts."""
        async with asyncio.timeout(_STARTING_TAKES_AT_MOST):
            while True:
                try:
                    return await self._connect()
                except (FileNotFoundError, ConnectionRefusedError):
                    await asyncio.sleep(_TRY_AGAIN_AFTER)


async def _cancel(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Tell the launcher to stop the conversion, and wait until it closes the connection, which it
    does once the sandbox has been removed. A launcher that cannot be reached, or takes too long,
    is left to it: its own limit on sandboxes still holds."""
    with suppress(OSError, TimeoutError):
        await _send(writer, "cancel")
        async with asyncio.timeout(_STOPPING_TAKES_AT_MOST):
            while await reader.read(_PIECE):
                pass


class _UsageFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    peak_memory: int
    cpu_time: float


class _EndedFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    exit_code: int
    timed_out: bool
    usage: _UsageFrame | None


def _ended(payload: bytes, stdout: bytes) -> Ended:
    frame = _EndedFrame.model_validate_json(payload)
    usage = None if frame.usage is None else Usage(frame.usage.peak_memory, frame.usage.cpu_time)
    return Ended(frame.exit_code, stdout, frame.timed_out, usage)


async def _send_item(writer: asyncio.StreamWriter, item: bytes | Ended) -> None:
    if not isinstance(item, Ended):
        await _send(writer, "event", item)
        return
    usage = None if item.usage is None else _UsageFrame(peak_memory=item.usage.peak_memory, cpu_time=item.usage.cpu_time)
    ended = _EndedFrame(exit_code=item.exit_code, timed_out=item.timed_out, usage=usage)
    await _send(writer, "stdout", item.stdout)
    await _send(writer, "ended", ended.model_dump_json().encode())


async def _send(writer: asyncio.StreamWriter, kind: str, payload: bytes = b"") -> None:
    writer.write(f"{kind} {len(payload)}\n".encode("ascii"))
    writer.write(payload)
    await writer.drain()


async def _receive(reader: asyncio.StreamReader, kinds: Mapping[str, int]) -> tuple[str, bytes]:
    """The next frame, of one of `kinds` and no longer than its limit there."""
    try:
        header = await reader.readuntil(b"\n")
        kind, _, length = header[:-1].decode("ascii").partition(" ")
        if kind not in kinds or not length.isdigit() or len(length) > _LONGEST_LENGTH or int(length) > kinds[kind]:
            raise BrokenFrames("a frame that may not come here")
        return kind, await reader.readexactly(int(length))
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, UnicodeDecodeError):
        raise BrokenFrames("frames that stop partway") from None
