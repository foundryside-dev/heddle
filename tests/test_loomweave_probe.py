from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from heddle.loomweave import LoomweaveMcpClient, LoomweaveProbe


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
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "ok": True,
                                "result": {
                                    "entity": {"id": "python:function:a"},
                                    "callees": [],
                                },
                            }
                        ),
                    }
                ]
            },
        }
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload))

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert LoomweaveMcpClient(tmp_path).neighborhood("python:function:a") == {
        "entity": {"id": "python:function:a"},
        "callees": [],
    }
