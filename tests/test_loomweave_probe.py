from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from warpline.loomweave import LoomweaveMcpClient, LoomweaveProbe


class FakeLoomweaveStdout:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.closed = False

    def readline(self) -> str:
        if not self.lines:
            return ""
        return self.lines.pop(0)

    def fileno(self) -> int:
        raise OSError("fake stream has no file descriptor")

    def close(self) -> None:
        self.closed = True


class FakeLoomweaveStdin:
    def __init__(self, proc: FakeLoomweaveProcess) -> None:
        self.proc = proc
        self.closed = False

    def write(self, text: str | bytes) -> int:
        raw_text = text.decode("utf-8") if isinstance(text, bytes) else text
        for line in raw_text.splitlines():
            request = json.loads(line)
            entity_id = request["params"]["arguments"]["id"]
            payload = {
                "ok": True,
                "result": {
                    "entity": {"id": entity_id},
                    "callees": [],
                },
            }
            envelope = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload),
                        }
                    ]
                },
            }
            self.proc.requests.append(request)
            self.proc.stdout.lines.append(json.dumps(envelope) + "\n")
        return len(raw_text)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class FakeLoomweaveStderr:
    def read(self) -> str:
        return ""

    def close(self) -> None:
        return None


class FakeLoomweaveProcess:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs
        self.returncode: int | None = None
        self.requests: list[dict[str, object]] = []
        self.stdout = FakeLoomweaveStdout()
        self.stdin = FakeLoomweaveStdin(self)
        self.stderr = FakeLoomweaveStderr()
        FAKE_LOOMWEAVE_PROCESSES.append(self)

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9


class PipeStdoutProcess:
    def __init__(self, stdout: object) -> None:
        self.stdout = stdout
        self.stderr = None

    def poll(self) -> int | None:
        return None


FAKE_LOOMWEAVE_PROCESSES: list[FakeLoomweaveProcess] = []


def test_missing_loomweave_degrades_cleanly(tmp_path: Path) -> None:
    probe = LoomweaveProbe(repo=tmp_path, command="/no/such/loomweave")
    result = probe.probe()
    assert result["status"] == "skipped"
    assert result["reason"] == "command_unavailable"


def test_probe_reports_expected_read_tools(tmp_path: Path) -> None:
    probe = LoomweaveProbe(repo=tmp_path)
    assert {"entity_find", "entity_resolve", "entity_callers_list"} <= probe.expected_tools()


def test_mcp_client_unwraps_loomweave_ok_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FAKE_LOOMWEAVE_PROCESSES.clear()
    monkeypatch.setattr(subprocess, "Popen", FakeLoomweaveProcess)

    client = LoomweaveMcpClient(tmp_path)
    try:
        assert client.neighborhood("python:function:a") == {
            "entity": {"id": "python:function:a"},
            "callees": [],
        }
    finally:
        client.close()


def test_mcp_client_reuses_one_stdio_session_for_multiple_tool_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FAKE_LOOMWEAVE_PROCESSES.clear()

    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("LoomweaveMcpClient should not spawn per tool call")

    monkeypatch.setattr(subprocess, "run", fail_run)
    monkeypatch.setattr(subprocess, "Popen", FakeLoomweaveProcess)

    client = LoomweaveMcpClient(tmp_path)
    try:
        assert client.neighborhood("python:function:a")["entity"] == {
            "id": "python:function:a"
        }
        assert client.neighborhood("python:function:b")["entity"] == {
            "id": "python:function:b"
        }
    finally:
        client.close()

    assert len(FAKE_LOOMWEAVE_PROCESSES) == 1
    assert [
        request["params"]["arguments"]["id"]  # type: ignore[index]
        for request in FAKE_LOOMWEAVE_PROCESSES[0].requests
    ] == ["python:function:a", "python:function:b"]
    assert FAKE_LOOMWEAVE_PROCESSES[0].kwargs["stderr"] == subprocess.DEVNULL


def test_mcp_client_reads_buffered_response_after_non_json_line(tmp_path: Path) -> None:
    read_fd, write_fd = os.pipe()
    envelope = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"ok": True, "result": {"entity": {"id": "x"}}}),
                }
            ]
        },
    }
    os.write(write_fd, b"loomweave log line\n" + json.dumps(envelope).encode() + b"\n")
    reader = os.fdopen(read_fd, "r", encoding="utf-8")
    try:
        # _read_envelope now takes a deadline as a third argument; supply a generous
        # deadline so the test exercises the happy path, not the deadline path.
        client = LoomweaveMcpClient(tmp_path, timeout=0.01)
        far_future = 1e18
        assert client._read_envelope(PipeStdoutProcess(reader), 1, far_future) == envelope  # type: ignore[arg-type]
    finally:
        reader.close()
        os.close(write_fd)


# ---------------------------------------------------------------------------
# Test A — per-request deadline fires when a chatty stream never sends a
# matching response (deterministic, no real wall-clock time, no hang risk).
# ---------------------------------------------------------------------------
class _FakeStdoutNoFileno:
    """Fake stdout that raises OSError on fileno() — falls through to readline()."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def readline(self) -> str:
        if not self._lines:
            return ""
        return self._lines.pop(0)

    def fileno(self) -> int:
        raise OSError("fake stream has no file descriptor")

    def close(self) -> None:
        pass


def test_mcp_client_deadline_fires_on_chatty_non_matching_stream(tmp_path: Path) -> None:
    """A stream that emits only non-matching notifications must trip the deadline,
    not loop forever.  The fake monotonic advances by 1.0 per call so the 2.0-second
    deadline is exceeded after a small number of iterations.  The 5000-line EOF cap
    prevents the test from hanging on current (unfixed) code: instead of a hang it
    gets RuntimeError from EOF — NOT TimeoutError — so pytest.raises(TimeoutError)
    fails RED on the old code and passes GREEN after the fix.
    """

    tick = [0.0]

    def fake_monotonic() -> float:
        tick[0] += 1.0
        return tick[0]

    # 5000 non-matching notification lines followed by EOF (empty string).
    notify_line = json.dumps({"jsonrpc": "2.0", "method": "notifications/message"}) + "\n"
    lines: list[str] = [notify_line] * 5000 + [""]

    fake_stdout = _FakeStdoutNoFileno(lines)

    class _FakeProc:
        stdout = fake_stdout
        stderr = None

        def poll(self) -> int | None:
            return None

    client = LoomweaveMcpClient(tmp_path, timeout=2.0, monotonic=fake_monotonic)
    deadline = fake_monotonic() + client.timeout  # starts at tick==1 after first call
    with pytest.raises(TimeoutError):
        client._read_envelope(_FakeProc(), request_id=42, deadline=deadline)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test B — happy-path regression: a matching envelope must still be returned
# normally even when a deadline is in play.
# ---------------------------------------------------------------------------
def test_mcp_client_returns_matching_envelope_before_deadline(tmp_path: Path) -> None:
    """The deadline must not break the happy path."""

    tick = [0.0]

    def fake_monotonic() -> float:
        tick[0] += 0.1  # advances slowly — far from deadline
        return tick[0]

    request_id = 7
    envelope = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"ok": True, "result": {"answer": 42}}),
                }
            ]
        },
    }
    match_line = json.dumps(envelope) + "\n"
    lines: list[str] = [match_line]
    fake_stdout = _FakeStdoutNoFileno(lines)

    class _FakeProc:
        stdout = fake_stdout
        stderr = None

        def poll(self) -> int | None:
            return None

    client = LoomweaveMcpClient(tmp_path, timeout=60.0, monotonic=fake_monotonic)
    # deadline well in the future
    deadline = fake_monotonic() + client.timeout
    result = client._read_envelope(_FakeProc(), request_id=request_id, deadline=deadline)  # type: ignore[arg-type]
    assert result == envelope


# ---------------------------------------------------------------------------
# U8 — fd/selector-path hardening: multi-chunk reassembly, EOF-mid-frame,
# oversized-frame cap (max_frame_bytes), and the selector-path deadline.
# These exercise the SAME selectors+os.read+_stdout_buffer loop the real
# loomweave subprocess drives — not the no-fileno readline fallback.
# ---------------------------------------------------------------------------
def _make_pipe_proc() -> tuple[int, object]:
    """Return (write_fd, proc) where proc.stdout.fileno() is a live pipe read fd."""

    read_fd, write_fd = os.pipe()

    class _PipeReader:
        def fileno(self) -> int:
            return read_fd

        def readline(self) -> bytes:  # pragma: no cover - selector path is used
            return os.read(read_fd, 4096)

        def close(self) -> None:
            try:
                os.close(read_fd)
            except OSError:
                pass

    class _PipeProc:
        def __init__(self) -> None:
            self.stdout = _PipeReader()
            self.stdin: object | None = None
            self.stderr = None
            self._closed = False

        def poll(self) -> int | None:
            return 0 if self._closed else None

        def terminate(self) -> None:
            self._closed = True

        def wait(self, timeout: float | None = None) -> int:
            self._closed = True
            return 0

        def kill(self) -> None:
            self._closed = True

    return write_fd, _PipeProc()


def test_mcp_client_reassembles_frame_split_across_multiple_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A JSON-RPC envelope delivered in two os.write halves split mid-frame over a
    real pipe; the reader exposes a working fileno() so the selectors+os.read+
    _stdout_buffer accumulation path runs and reassembles the frame.

    To guarantee accumulation spans MULTIPLE os.read calls (not a single 4096-byte
    read), os.read is wrapped to return at most 8 bytes per call.
    """

    request_id = 11
    envelope = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"ok": True, "result": {"entity": {"id": "y"}}}),
                }
            ]
        },
    }
    frame = json.dumps(envelope).encode() + b"\n"

    real_os_read = os.read

    def small_read(fd: int, n: int) -> bytes:
        return real_os_read(fd, min(n, 8))

    monkeypatch.setattr("warpline.loomweave.os.read", small_read)

    write_fd, proc = _make_pipe_proc()
    # Split the frame mid-way across two writes; no newline in the first half.
    half = len(frame) // 2
    os.write(write_fd, frame[:half])
    os.write(write_fd, frame[half:])
    os.close(write_fd)

    client = LoomweaveMcpClient(tmp_path, timeout=60.0)
    try:
        # Finite, generous deadline: the selector branch passes `remaining` to
        # selectors.select(), which overflows time_t for an astronomically large
        # value, so a real (but far-off) monotonic deadline is used here.
        deadline = time.monotonic() + 30.0
        assert client._read_envelope(proc, request_id, deadline) == envelope  # type: ignore[arg-type]
    finally:
        proc.stdout.close()  # type: ignore[attr-defined]


def test_mcp_client_reassembles_deeply_chunked_frame_without_recursion_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid envelope delivered in MORE os.read slices than the interpreter's
    recursion limit must still reassemble. This pins the recursion->loop conversion:
    on a tail-recursive _readline, accumulating one stack frame per os.read chunk blows
    sys.getrecursionlimit() (~1000) at ~4 MiB on a real stream — below the 16 MiB
    default cap — and propagates RecursionError (a RuntimeError subclass NOT caught by
    call_tool), leaking the subprocess. With an 8-byte-per-read slice, an >8 KiB frame
    is delivered in >1000 reads, so a recursive implementation raises RecursionError
    before the frame completes; a bounded loop reassembles it.

    Uses the DEFAULT max_frame_bytes (16 MiB) so this exercises the production default's
    accumulation mechanism, not a lowered test cap.
    """

    request_id = 13
    filler = "p" * 9000  # > 1000 * 8 bytes, so > recursion-limit os.read slices
    envelope = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"ok": True, "result": {"pad": filler}}),
                }
            ]
        },
    }
    frame = json.dumps(envelope).encode() + b"\n"
    assert len(frame) > 1000 * 8  # confirm >recursion-limit reads at 8 bytes/read
    assert len(frame) < 64 * 1024  # stay under the pipe buffer so os.write won't block

    real_os_read = os.read

    def small_read(fd: int, n: int) -> bytes:
        return real_os_read(fd, min(n, 8))

    monkeypatch.setattr("warpline.loomweave.os.read", small_read)

    write_fd, proc = _make_pipe_proc()
    os.write(write_fd, frame)
    os.close(write_fd)

    client = LoomweaveMcpClient(tmp_path, timeout=60.0)  # default 16 MiB cap
    try:
        deadline = time.monotonic() + 30.0
        assert client._read_envelope(proc, request_id, deadline) == envelope  # type: ignore[arg-type]
    finally:
        proc.stdout.close()  # type: ignore[attr-defined]


def test_mcp_client_eof_mid_frame_degrades_without_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial frame (no trailing newline) then EOF must degrade to RuntimeError —
    NOT a TypeError/IndexError crash and NOT a hang — and must close the process.
    """

    real_os_read = os.read

    def small_read(fd: int, n: int) -> bytes:
        return real_os_read(fd, min(n, 8))

    monkeypatch.setattr("warpline.loomweave.os.read", small_read)

    write_fd, proc = _make_pipe_proc()
    os.write(write_fd, b'{"jsonrpc": "2.0", "id": 1, "resu')  # partial, no newline
    os.close(write_fd)  # EOF

    client = LoomweaveMcpClient(tmp_path, timeout=60.0)
    client._process = proc  # type: ignore[assignment]
    deadline = time.monotonic() + 30.0
    with pytest.raises(RuntimeError):
        client._read_envelope(proc, request_id=1, deadline=deadline)  # type: ignore[arg-type]
    proc.stdout.close()  # type: ignore[attr-defined]


def test_mcp_client_oversized_frame_degrades_via_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A long newline-less byte run fed through the fd path must trip max_frame_bytes
    and degrade honestly: call_tool raises RuntimeError (the cap's TimeoutError funnels
    through call_tool's handler) AND self._process is None afterward (subprocess closed,
    not leaked).

    The cap (256) is set ABOVE one os.read slice (8 bytes) so the read loop must
    ACCUMULATE across many os.read calls before the cap fires — exercising the same
    bounded-loop accumulation path production uses at its 16 MiB default, not a
    single-chunk shortcut. On unfixed code (no cap), this loop accretes the buffer
    without ever raising the cap signal.
    """

    real_os_read = os.read

    def small_read(fd: int, n: int) -> bytes:
        return real_os_read(fd, min(n, 8))

    monkeypatch.setattr("warpline.loomweave.os.read", small_read)

    write_fd, proc = _make_pipe_proc()
    os.write(write_fd, b"x" * 4096)  # >256-byte newline-less run
    os.close(write_fd)

    client = LoomweaveMcpClient(tmp_path, timeout=60.0, max_frame_bytes=256)
    client._process = proc  # type: ignore[assignment]

    class _Stdin:
        def write(self, data: bytes) -> int:
            return len(data)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            return None

    proc.stdin = _Stdin()  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError):
        client.call_tool("entity_neighborhood_get", {"id": "x", "limit": 100})
    assert client._process is None


def test_mcp_client_deadline_fires_via_selector_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty (never-written) real pipe with a working fileno(), a tiny timeout, and a
    fast-advancing fake monotonic must trip TimeoutError via the selectors.select(remaining)
    branch — the branch the real subprocess fd path uses — within a bounded number of ticks.
    Complements Test A (which drives the no-fileno readline fallback).
    """

    tick = [0.0]

    def fake_monotonic() -> float:
        tick[0] += 1.0
        return tick[0]

    # Force selector.select to return immediately with no events regardless of the
    # remaining timeout, so the test cannot block on the empty pipe.
    monkeypatch.setattr(
        "warpline.loomweave.selectors.DefaultSelector",
        lambda: _NoEventSelector(),
    )

    write_fd, proc = _make_pipe_proc()
    # A large timeout keeps the per-request deadline well ahead of the handful of
    # monotonic ticks that precede the select() call, so the TimeoutError is raised by
    # the selector branch's "no events" path (the line a real hung sibling hits), NOT
    # by the top-of-_readline deadline guard. The match= pins that branch: a top-guard
    # raise would carry "exceeded the per-request deadline" instead and fail RED.
    client = LoomweaveMcpClient(tmp_path, timeout=100.0, monotonic=fake_monotonic)
    deadline = fake_monotonic() + client.timeout
    try:
        with pytest.raises(TimeoutError, match="timed out before returning a response"):
            client._read_envelope(proc, request_id=99, deadline=deadline)  # type: ignore[arg-type]
    finally:
        os.close(write_fd)
        proc.stdout.close()  # type: ignore[attr-defined]


class _NoEventSelector:
    """A selectors.DefaultSelector stand-in that registers fds but always reports
    zero ready events — emulating a pipe with no data, deterministically and without
    blocking on wall-clock time."""

    def register(self, fileobj: object, events: int) -> None:
        return None

    def select(self, timeout: float | None = None) -> list[object]:
        return []

    def close(self) -> None:
        return None
