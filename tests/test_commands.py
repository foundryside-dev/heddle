from __future__ import annotations

import json
from pathlib import Path

import pytest

from heddle import cli
from heddle.store import HeddleStore, default_store_path


def test_cli_changed_outputs_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert cli.main(["changed", "--repo", str(repo), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "changed"
    assert "changed" in payload
    assert "changed_entity_key_ids" in payload


def test_cli_timeline_outputs_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert cli.main(["timeline", "--repo", str(repo), "--entity", "file:a.py", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "timeline"
    assert payload["entity"] == "file:a.py"


def test_cli_capture_snapshot_degrades_without_loomweave(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with HeddleStore.open(default_store_path(repo)) as store:
        store.ensure_repo(repo)

    assert (
        cli.main(
            [
                "capture-snapshot",
                "--repo",
                str(repo),
                "--commit",
                "c1",
                "--loomweave-command",
                "/no/such/loomweave",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "capture_snapshot"
    assert payload["completeness"] == "SKIPPED"
    assert payload["source_version"] == "command_unavailable"
