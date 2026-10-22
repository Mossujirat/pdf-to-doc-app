"""A stand-in for Docker, for the launcher's tests: each sandbox is a process on this machine.

It runs the sandbox entry point, or a script that misbehaves as a sandbox could, with the
source file on its stdin. It counts the sandboxes it holds, so that a test can tell whether
each one was removed, and how many ran at once.
"""

import asyncio
import sys
from asyncio.subprocess import PIPE, Process
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from pdf_to_doc.web.docker import Stream
from pdf_to_doc.web.sandboxes import Usage

_PIECE = 64 * 1024


class FakeDocker:
    def __init__(self, script: str | None = None, usage: Usage | None = None) -> None:
        """`script` is the Python each sandbox runs instead of the entry point; `usage` is what
        Docker's stats would say each one used."""
        self._command = [sys.executable, "-c", script] if script else [sys.executable, "-m", "pdf_to_doc.sandbox"]
        self._usage = usage
        self.started = 0  # sandboxes started
        self.alive = 0  # sandboxes started and not yet removed
        self.most_alive = 0  # the most alive at once
        self.killed = 0  # sandboxes stopped before they ended by themselves
        self.leftovers_removed = 0  # how often the launcher had leftover sandboxes removed

    async def remove_leftovers(self) -> None:
        self.leftovers_removed += 1

    @asynccontextmanager
    async def sandbox(self, source: bytes) -> AsyncIterator["FakeContainer"]:
        process = await asyncio.create_subprocess_exec(*self._command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self.started += 1
        self.alive += 1
        self.most_alive = max(self.most_alive, self.alive)
        container = FakeContainer(self, process, source, self._usage)
        try:
            yield container
        finally:
            await container.remove()
            # As Docker's removal does, it takes a moment, and does not happen if interrupted.
            await asyncio.sleep(0.1)
            self.alive -= 1


class FakeContainer:
    """One sandbox: its process, fed the source file, with what it writes read as it comes."""

    def __init__(self, docker: FakeDocker, process: Process, source: bytes, usage: Usage | None) -> None:
        assert process.stdin is not None and process.stdout is not None and process.stderr is not None
        self._docker = docker
        self._process = process
        self._usage = usage
        self._pieces: asyncio.Queue[tuple[Stream, bytes] | None] = asyncio.Queue()
        self._open = 2  # stdout and stderr
        self._tasks = [
            asyncio.create_task(self._feed(process.stdin, source)),
            asyncio.create_task(self._pump("stdout", process.stdout)),
            asyncio.create_task(self._pump("stderr", process.stderr)),
        ]

    async def read(self) -> tuple[Stream, bytes] | None:
        while self._open:
            piece = await self._pieces.get()
            if piece is not None:
                return piece
            self._open -= 1
        return None

    async def wait(self) -> int:
        return await self._process.wait()

    async def kill(self) -> None:
        if self._process.returncode is None:
            self._docker.killed += 1
            with suppress(ProcessLookupError):
                self._process.kill()

    def usage(self) -> Usage | None:
        return self._usage

    async def remove(self) -> None:
        for task in self._tasks:
            task.cancel()
        await self.kill()
        await self._process.wait()

    async def _feed(self, stdin: asyncio.StreamWriter, source: bytes) -> None:
        with suppress(ConnectionError):  # a sandbox may end without reading it all
            stdin.write(source)
            await stdin.drain()
            stdin.close()

    async def _pump(self, stream: Stream, reader: asyncio.StreamReader) -> None:
        while piece := await reader.read(_PIECE):
            await self._pieces.put((stream, piece))
        await self._pieces.put(None)
