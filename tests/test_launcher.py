"""The launcher: each conversion in a throwaway container of its own (ADR 0004), which the web app
reaches through the launcher's socket. The tests go through the web app's side of that socket,
with a stand-in for Docker whose sandboxes are processes on this machine."""

import asyncio
import json
import socket
import sys
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TypeVar

import markdown_reader
import pytest
from fake_docker import FakeDocker
from pdf_builder import Scan, pdf

from pdf_to_doc.web.launcher import Launcher, LauncherSandbox, serve, serve_connection
from pdf_to_doc.web.protocol import MAX_EVENT_LINE, read_parts
from pdf_to_doc.web.sandboxes import Ended, Usage

T = TypeVar("T")
SOURCE = pdf(["หน้าแรก"])
SCAN = pdf(Scan(["หน้าสแกน"], dpi=50))
MB = 1024 * 1024


def writing(stderr: str, *, then: str = "") -> str:
    """A sandbox's script: it writes `stderr`, an expression giving bytes, then runs `then`."""
    return f"import sys, time; sys.stderr.buffer.write({stderr}); sys.stderr.flush(); {then}"


@dataclass(frozen=True)
class Converted:
    """What came back from a conversion, as the web app reads it."""

    lines: list[bytes]  # its event lines, in the order they came
    ended: Ended | None  # how it ended; None when it failed without saying
    error: str | None  # the type of the error the web app's side raised, if it raised one


async def converted(sandbox: LauncherSandbox, source: bytes, *, keep_images: bool = False) -> Converted:
    lines: list[bytes] = []
    ended = None
    try:
        async for item in sandbox.convert(source, keep_images=keep_images):
            if isinstance(item, Ended):
                ended = item
            else:
                lines.append(item)
    except Exception as error:
        return Converted(lines, ended, type(error).__name__)
    return Converted(lines, ended, None)


Connect = Callable[[], Awaitable[tuple[asyncio.StreamReader, asyncio.StreamWriter]]]


def connected_to_the_launcher(docker: FakeDocker, use: Callable[[Connect], Awaitable[T]], *, time_limit: float = 60) -> T:
    """Run `use` with a way to connect to the launcher's socket, the launcher starting its
    sandboxes with `docker`. The socket is a local TCP one here, which every platform has."""

    async def main() -> T:
        launcher = Launcher(docker, time_limit=time_limit)
        server = await asyncio.start_server(partial(serve_connection, launcher), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            return await use(partial(asyncio.open_connection, "127.0.0.1", port))

    return asyncio.run(main())


def through_the_launcher(
    docker: FakeDocker, use: Callable[[LauncherSandbox], Awaitable[T]], *, time_limit: float = 60
) -> T:
    """Run `use` with the web app's sandbox: the launcher, behind its socket."""
    return connected_to_the_launcher(docker, lambda connect: use(LauncherSandbox(connect)), time_limit=time_limit)


async def until(done: Callable[[], bool], what: str) -> None:
    try:
        async with asyncio.timeout(30):
            while not done():
                await asyncio.sleep(0.02)
    except TimeoutError:
        raise AssertionError(f"waited too long for {what}") from None


def test_a_source_file_comes_back_as_both_outputs_after_its_events() -> None:
    docker = FakeDocker()

    came = through_the_launcher(docker, lambda sandbox: converted(sandbox, SOURCE))

    events = [json.loads(line) for line in came.lines]
    assert events[0] == {"event": "opened", "source_type": "pdf", "pages": 1}
    assert events[-1]["event"] == "summary"
    assert came.ended is not None and came.ended.exit_code == 0, came
    outputs = read_parts(came.ended.stdout)
    assert markdown_reader.page_texts(outputs["markdown"].decode("utf-8")) == ["หน้าแรก"]
    assert "docx" in outputs
    assert docker.alive == 0  # removed once it ended


@pytest.mark.parametrize(
    ("keep_images", "stage"),
    [pytest.param(False, "ocr", id="read with OCR"), pytest.param(True, "images", id="kept images")],
)
def test_the_kept_images_setting_reaches_the_sandbox(
    keep_images: bool, stage: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without the OCR models, so that a scan sent to OCR stops there rather than being read.
    monkeypatch.setenv("PDF_TO_DOC_MODELS", str(tmp_path / "no-models-here"))

    came = through_the_launcher(FakeDocker(), lambda sandbox: converted(sandbox, SCAN, keep_images=keep_images))

    events = [json.loads(line) for line in came.lines]
    assert [event["stage"] for event in events if event["event"] == "progress"][1] == stage


def test_a_frame_with_a_setting_it_does_not_know_is_refused_before_any_sandbox_starts() -> None:
    docker = FakeDocker()

    async def send_a_run_of_another_kind(connect: Connect) -> bytes:
        reader, writer = await connect()
        writer.write(b"run-keeping-nothing %d\n" % len(SOURCE) + SOURCE)
        answer = await reader.read()  # until the launcher closes the connection
        writer.close()
        return answer

    answer = connected_to_the_launcher(docker, send_a_run_of_another_kind)

    assert answer == b""
    assert docker.started == 0


def test_a_launcher_not_listening_yet_is_waited_for() -> None:
    # As while the launcher starts, or starts again: it takes some seconds before it listens.
    docker = FakeDocker()

    async def convert_before_it_listens() -> Converted:
        with socket.socket() as free:  # a port for the launcher to listen on later
            free.bind(("127.0.0.1", 0))
            port = free.getsockname()[1]
        sandbox = LauncherSandbox(partial(asyncio.open_connection, "127.0.0.1", port))
        conversion = asyncio.create_task(converted(sandbox, SOURCE))
        await asyncio.sleep(3)  # longer than Windows itself tries to connect for
        launcher = Launcher(docker, time_limit=60)
        async with await asyncio.start_server(partial(serve_connection, launcher), "127.0.0.1", port):
            return await conversion

    came = asyncio.run(convert_before_it_listens())

    assert came.ended is not None and came.ended.exit_code == 0, came


def test_what_the_sandbox_used_comes_back_with_how_it_ended() -> None:
    used = Usage(peak_memory=1_300_000_000, cpu_time=42.5)

    came = through_the_launcher(FakeDocker(usage=used), lambda sandbox: converted(sandbox, SOURCE))

    assert came.ended is not None and came.ended.usage == used


@pytest.mark.parametrize(
    "script",
    [
        pytest.param(writing("b'not an event\\n'"), id="not JSON"),
        pytest.param(writing("b'{\"event\": \"opened\", \"source_type\": \"pdf\", \"pages\": -1}\\n'"), id="against its schema"),
        pytest.param(writing("b'{\"event\": \"opened\"'"), id="cut short"),
    ],
)
def test_a_malformed_event_line_fails_the_conversion(script: str) -> None:
    docker = FakeDocker(script)

    came = through_the_launcher(docker, lambda sandbox: converted(sandbox, SOURCE))

    assert came.ended is None
    assert came.lines == []
    assert docker.alive == 0


# Each cap holds while the sandbox runs: these sandboxes would run for a minute, and are stopped
# as soon as they pass it.


def test_an_event_line_over_its_cap_stops_the_conversion_at_once() -> None:
    docker = FakeDocker(writing(f"b'x' * {MAX_EVENT_LINE + 1}", then="time.sleep(60)"))

    came = through_the_launcher(docker, lambda sandbox: converted(sandbox, SOURCE))

    assert came.ended is None
    assert docker.killed == 1
    assert docker.alive == 0


def test_outputs_over_50_mb_stop_the_conversion_at_once() -> None:
    script = f"import sys, time; sys.stdout.buffer.write(b'x' * {50 * MB + 1}); sys.stdout.flush(); time.sleep(60)"
    docker = FakeDocker(script)

    came = through_the_launcher(docker, lambda sandbox: converted(sandbox, SOURCE))

    assert came.ended is None
    assert docker.killed == 1
    assert docker.alive == 0


OPENED = b'{"event": "opened", "source_type": "pdf", "pages": 1}'


def test_a_conversion_past_the_time_limit_is_stopped_and_said_to_have_timed_out() -> None:
    docker = FakeDocker(writing(f"{OPENED + b'\n'!r}", then="time.sleep(60)"))

    came = through_the_launcher(docker, lambda sandbox: converted(sandbox, SOURCE), time_limit=0.5)

    assert came.lines == [OPENED]
    assert came.ended is not None and came.ended.timed_out, came
    assert came.ended.stdout == b""
    assert docker.killed == 1
    assert docker.alive == 0


RUNS_A_MINUTE = writing(f"{OPENED + b'\n'!r}", then="time.sleep(60)")


def test_a_cancelled_conversion_has_its_sandbox_removed_before_the_cancel_returns() -> None:
    docker = FakeDocker(RUNS_A_MINUTE)

    async def cancel(sandbox: LauncherSandbox) -> int:
        conversion = sandbox.convert(SOURCE)
        assert await anext(conversion) == OPENED
        await conversion.aclose()  # as the web app's cancel does
        return docker.alive

    alive_once_cancelled = through_the_launcher(docker, cancel)

    assert alive_once_cancelled == 0
    assert docker.killed == 1


def test_a_web_app_gone_without_cancelling_has_its_conversion_stopped() -> None:
    docker = FakeDocker(RUNS_A_MINUTE)

    async def leave(connect: Connect) -> None:
        reader, writer = await connect()
        writer.write(b"run %d\n" % len(SOURCE) + SOURCE)
        assert await reader.readline() == b"event %d\n" % len(OPENED)  # it runs
        writer.close()  # as a web app that stops does
        await until(lambda: docker.alive == 0, "the sandbox to be removed")

    connected_to_the_launcher(docker, leave)

    assert docker.killed == 1


def test_at_most_three_sandboxes_run_at_once_and_a_fourth_waits_for_a_place() -> None:
    docker = FakeDocker(RUNS_A_MINUTE)

    async def four(sandbox: LauncherSandbox) -> None:
        conversions = [sandbox.convert(SOURCE) for _ in range(4)]
        first_events = [asyncio.ensure_future(anext(conversion)) for conversion in conversions]
        await until(lambda: sum(event.done() for event in first_events) >= 3, "three conversions to start")
        await asyncio.sleep(0.5)  # time enough for a fourth to start, if it could
        assert docker.started == 3, f"{docker.started} sandboxes started at once"
        running = [conversion for conversion, event in zip(conversions, first_events, strict=True) if event.done()]
        await running[0].aclose()  # a place is freed
        waiting = next(event for event in first_events if not event.done())
        assert await asyncio.wait_for(waiting, 30) == OPENED
        for conversion in conversions:
            await conversion.aclose()

    through_the_launcher(docker, four)

    assert docker.started == 4
    assert docker.most_alive == 3
    assert docker.alive == 0


@pytest.mark.skipif(sys.platform == "win32", reason="the launcher listens on a Unix socket, as on the server")
def test_the_launcher_serves_on_its_socket_and_removes_leftover_sandboxes_as_it_starts_and_stops(
    tmp_path: Path,
) -> None:
    docker = FakeDocker()
    socket = tmp_path / "launcher.sock"
    socket.write_bytes(b"")  # as a launcher that stopped leaves it, on the volume it shares with the web app

    async def start_convert_and_stop() -> tuple[int, Converted]:
        serving = asyncio.create_task(serve(docker, time_limit=60, path=str(socket)))
        await until(lambda: socket.is_socket(), "the launcher to listen")
        removed_as_it_started = docker.leftovers_removed
        came = await converted(LauncherSandbox.at(str(socket)), SOURCE)
        serving.cancel()
        with suppress(asyncio.CancelledError):
            await serving
        return removed_as_it_started, came

    removed_as_it_started, came = asyncio.run(start_convert_and_stop())

    assert removed_as_it_started == 1
    assert came.ended is not None and came.ended.exit_code == 0, came
    assert docker.leftovers_removed == 2

