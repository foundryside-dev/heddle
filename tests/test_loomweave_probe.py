from __future__ import annotations

import json
import os
import subprocess
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
