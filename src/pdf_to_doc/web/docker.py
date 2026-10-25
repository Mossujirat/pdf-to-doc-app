"""The launcher's sandboxes in Docker, through the Docker Engine API on Docker's socket.

Each sandbox's container is created from the image the launcher itself runs, under every
restriction in ADR 0004 and the spec, and labelled and named with the launcher's environment.
The source file goes in on the container's stdin, through a connection that the Engine API
hijacks from an attach request; stdout and stderr come back on it, in Docker's frames.
"""

import asyncio
import json
import logging
import secrets
import socket
import sys
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Any, Literal, Self

import httpx

from pdf_to_doc.sandbox import KEEP_IMAGES_VARIABLE, keep_images_setting
from pdf_to_doc.web.protocol import Malformed
from pdf_to_doc.web.sandboxes import Usage
from pdf_to_doc.web.settings import Environment

Stream = Literal["stdout", "stderr"]
DOCKER_SOCKET = "/var/run/docker.sock"
# The version of the Engine API spoken. Docker 25.0 was the first to speak it, and 29 still does.
_API = "/v1.44"
_LABEL = "pdf-to-doc.sandbox"  # its value is the environment
_CPUS = 4
_MEMORY = 2 * 1024**3
# Threads count as processes. A conversion with an OCR page had 24 at most, at 4 OCR threads.
_PROCESSES = 128
# PaddleX keeps its working folders in /tmp; they stayed empty while a scanned page was read.
_SCRATCH = "rw,noexec,nosuid,nodev,size=64m"
_PIECE = 64 * 1024  # bytes read at a time
# Docker's frames name their stream by a number; 0, stdin, comes as stdout.
_STREAMS: dict[int, Stream] = {0: "stdout", 1: "stdout", 2: "stderr"}
_TIMEOUT = 60  # seconds, for each request but the stats

_log = logging.getLogger(__name__)


class AttachRefused(Exception):
    """Docker would not connect the launcher to a sandbox's stdin and stdout."""


def sandbox_name(environment: Environment) -> str:
    """A new sandbox's container name, which tells staging's sandboxes from production's."""
    return f"pdf-to-doc-sandbox-{environment}-{secrets.token_hex(8)}"


def sandbox_config(*, image: str, environment: Environment, runtime: str, keep_images: bool) -> dict[str, Any]:
    """What a sandbox's container is created with: the sandbox entry point from `image`, keeping
    images if `keep_images`, in the container runtime `runtime`, under every restriction in ADR
    0004 and the spec."""
    return {
        "Image": image,
        "Cmd": ["pdf-to-doc-sandbox"],
        "User": "converter",  # the image's own, which cannot change the installed code
        # Added to the image's own environment, which holds no secret.
        "Env": [f"PDF_TO_DOC_OCR_THREADS={_CPUS}", f"{KEEP_IMAGES_VARIABLE}={keep_images_setting(keep_images)}"],
        "AttachStdin": True,
        "AttachStdout": True,
        "AttachStderr": True,
        "OpenStdin": True,
        "StdinOnce": True,  # stdin closes once the source file has all been sent
        "Tty": False,
        "NetworkDisabled": True,
        "Labels": {_LABEL: environment},
        "HostConfig": {
            "Runtime": runtime,
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Tmpfs": {"/tmp": _SCRATCH},
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges"],
            "NanoCpus": _CPUS * 10**9,
            "Memory": _MEMORY,
            "MemorySwap": _MEMORY,  # the same as the memory: no swap
            "PidsLimit": _PROCESSES,
            "IpcMode": "none",
            # Docker would otherwise keep what the sandbox writes in a log file: the outputs are
            # the document's text.
            "LogConfig": {"Type": "none"},
        },
    }


class RestrictionDropped(Exception):
    """Docker created a sandbox's container without one of its restrictions, as it does on a
    server whose kernel cannot apply it, saying so only in a warning."""


class DockerEngine:
    """Sandboxes in Docker, for the launcher in `environment`, from `image`, in the container
    runtime `runtime`."""

    def __init__(self, *, image: str, environment: Environment, runtime: str) -> None:
        self._image = image
        self._environment = environment
        self._runtime = runtime

    @classmethod
    async def of_this_container(cls, *, environment: Environment, runtime: str) -> Self:
        """Sandboxes from the image that this container, the launcher's, runs. Docker names a
        container's host after its ID."""
        async with _client() as client:
            response = await client.get(f"/containers/{socket.gethostname()}/json")
            response.raise_for_status()
        image = response.json()["Image"]
        return cls(image=image, environment=environment, runtime=runtime)

    async def remove_leftovers(self) -> None:
        async with _client() as client:
            label = json.dumps({"label": [f"{_LABEL}={self._environment}"]})
            listed = await client.get("/containers/json", params={"all": "true", "filters": label})
            listed.raise_for_status()
            for container in listed.json():
                await _remove(client, container["Id"])
        if listed.json():
            _log.info("removed %d leftover sandboxes", len(listed.json()))

    @asynccontextmanager
    async def sandbox(self, source: bytes, *, keep_images: bool = False) -> AsyncIterator["_Container"]:
        async with _client() as client, AsyncExitStack() as cleanup:
            name = sandbox_name(self._environment)
            # Before it is asked for, so that a container created as the conversion is cancelled
            # goes too: Docker removes a container by its name as well as its ID.
            cleanup.push_async_callback(_remove, client, name)
            config = sandbox_config(
                image=self._image, environment=self._environment, runtime=self._runtime, keep_images=keep_images
            )
            created = await client.post("/containers/create", params={"name": name}, json=config)
            created.raise_for_status()
            if warnings := created.json().get("Warnings"):
                _log.warning("Docker dropped a sandbox restriction: %s", warnings)
                raise RestrictionDropped()
            reader, writer = await _attach(created.json()["Id"])
            cleanup.callback(writer.close)
            (await client.post(f"/containers/{name}/start")).raise_for_status()
            container = _Container(client, name, reader, writer, source)
            cleanup.callback(container.stop_watching)
            yield container


class _Container:
    """A sandbox's container, as it runs: fed the source file, and read from Docker's frames."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        identifier: str,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        source: bytes,
    ) -> None:
        self._client = client
        self._identifier = identifier
        self._reader = reader
        self._stream: Stream = "stdout"  # the current frame's
        self._left = 0  # bytes of the current frame not yet read
        self._samples = 0  # of Docker's stats
        self._peak_memory: int | None = None
        self._cpu_time: float | None = None
        self._tasks = [asyncio.create_task(_feed(writer, source)), asyncio.create_task(self._watch())]

    async def read(self) -> tuple[Stream, bytes] | None:
        try:
            while self._left == 0:
                header = await self._reader.readexactly(8)
                stream = _STREAMS.get(header[0])
                if stream is None:
                    raise Malformed("a frame for no stream known")
                self._stream, self._left = stream, int.from_bytes(header[4:], "big")
            piece = await self._reader.readexactly(min(self._left, _PIECE))
        except asyncio.IncompleteReadError as error:
            if self._left == 0 and not error.partial:  # between frames: the sandbox has closed both
                return None
            raise Malformed("a frame cut short") from None
        self._left -= len(piece)
        return self._stream, piece

    async def wait(self) -> int:
        response = await self._client.post(f"/containers/{self._identifier}/wait")
        response.raise_for_status()
        return int(response.json()["StatusCode"])

    async def kill(self) -> None:
        response = await self._client.post(f"/containers/{self._identifier}/kill")
        if response.status_code not in (404, 409):  # 409: it no longer runs
            response.raise_for_status()

    def usage(self) -> Usage | None:
        if self._peak_memory is None or self._cpu_time is None:
            return None
        return Usage(self._peak_memory, self._cpu_time)

    def stop_watching(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._samples and self._peak_memory is None:
            _log.warning("sandbox statistics unavailable: no memory use in Docker's stats")

    async def _watch(self) -> None:
        """Keep the highest memory use and the CPU time from Docker's stats, which come about once
        a second while the sandbox runs."""
        path = f"/containers/{self._identifier}/stats"
        try:
            async with self._client.stream("GET", path, params={"stream": "true"}, timeout=None) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        self._sample(json.loads(line))
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            # The statistics are not worth a conversion.
            _log.warning("sandbox statistics unavailable: %s", type(error).__name__)

    def _sample(self, stats: dict[str, Any]) -> None:
        self._samples += 1
        memory = stats["memory_stats"]
        if "usage" in memory:  # not once the sandbox has stopped
            # As `docker stats` counts it on cgroup v2: without the file cache it could drop.
            used = memory["usage"] - memory.get("stats", {}).get("inactive_file", 0)
            self._peak_memory = max(self._peak_memory or 0, used)
        cpu_time = stats["cpu_stats"]["cpu_usage"]["total_usage"] / 10**9
        self._cpu_time = max(self._cpu_time or 0.0, cpu_time)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET), base_url=f"http://docker{_API}", timeout=_TIMEOUT
    )


async def _attach(identifier: str) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """A connection to the container's stdin, stdout and stderr, which the Engine API hijacks from
    an attach request. It must be made before the container starts, so that nothing is missed."""
    if sys.platform == "win32":
        raise NotImplementedError("Docker's socket is a Unix one, on the server")
    reader, writer = await asyncio.open_unix_connection(DOCKER_SOCKET)
    writer.write(
        f"POST {_API}/containers/{identifier}/attach?stream=1&stdin=1&stdout=1&stderr=1 HTTP/1.1\r\n"
        "Host: docker\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n".encode("ascii")
    )
    await writer.drain()
    head = await reader.readuntil(b"\r\n\r\n")
    if not head.startswith((b"HTTP/1.1 101 ", b"HTTP/1.1 200 ")):
        writer.close()
        raise AttachRefused()
    return reader, writer


async def _feed(writer: asyncio.StreamWriter, source: bytes) -> None:
    """Send the source file to the container's stdin, then close that half of the connection;
    stdout and stderr still come on the other."""
    with suppress(ConnectionError):  # a sandbox may stop before it has read it all
        writer.write(source)
        await writer.drain()
        writer.write_eof()


async def _remove(client: httpx.AsyncClient, identifier: str) -> None:
    """Remove the container, killing it first if it still runs."""
    response = await client.delete(f"/containers/{identifier}", params={"force": "true"})
    if response.status_code not in (404, 409):  # 409: Docker is removing it already
        response.raise_for_status()
