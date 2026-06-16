"""CLI dispatch regressions.

Covers two review findings:

- #1: the ``loomweave-probe`` subcommand must reach its handler. A Rung 1c edit
  replaced the ``loomweave-probe`` dispatch guard with the ``reresolve-sei``
  branch (which ends in ``return 0``), stranding the probe body as dead code so
  the command silently fell through to ``print_help``.
- #10: the NON-FROZEN demo/internal verbs (``cop`` / ``co-change`` /
  ``rebuild-coupling``) must carry the same ``meta`` honesty block every frozen
  tool does — ``local_only: True`` and an explicit ``peer_side_effects: []`` —
  so a hand-built payload cannot silently drop the local-only guarantee.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import init_repo as _init_repo

from warpline import cli


def _assert_local_only(meta: dict) -> None:
    assert meta["local_only"] is True
    assert meta["peer_side_effects"] == []
    assert meta["producer"]["tool"] == "warpline"


def test_loomweave_probe_dispatches_to_handler(tmp_path: Path, monkeypatch, capsys) -> None:
    """#1: `warpline loomweave-probe` invokes the probe, not the help fallthrough."""

    repo = _init_repo(tmp_path)
    sentinel = {"status": "available", "version": "9.9.9-test", "marker": "probe-ran"}

    class _FakeProbe:
        def __init__(self, *, repo: Path, command: str) -> None:  # noqa: D401
            self._sentinel = sentinel

        def probe(self) -> dict:
            return self._sentinel

    monkeypatch.setattr(cli, "LoomweaveProbe", _FakeProbe)
    rc = cli.main(["loomweave-probe", "--repo", str(repo), "--json"])
    out = capsys.readouterr().out

    assert rc == 0
    # The handler ran: the probe payload is printed (the old bug printed help).
    assert json.loads(out) == sentinel
    assert "usage:" not in out


def test_co_change_payload_carries_local_only_meta(tmp_path: Path) -> None:
    """#10: the co-change error-path payload still carries the honesty meta."""

    repo = _init_repo(tmp_path)
    payload = cli._co_change_payload(
        repo, sei=None, locator=None, entity_key_id=None, min_count=2
    )
    assert "meta" in payload
    _assert_local_only(payload["meta"])


def test_rebuild_coupling_payload_carries_local_only_meta(
    tmp_path: Path, capsys
) -> None:
    """#10: the rebuild-coupling demo verb emits the honesty meta block."""

    repo = _init_repo(tmp_path)
    rc = cli.main(["rebuild-coupling", "--repo", str(repo), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "meta" in payload
    _assert_local_only(payload["meta"])


def test_cop_demo_payload_carries_local_only_meta(tmp_path: Path) -> None:
    """#10: the cop demo verb emits the honesty meta block (offline, no peers)."""

    repo = _init_repo(tmp_path)
    payload = cli._cop_payload(
        repo,
        frame="sei",
        rev_range=None,
        since=None,
        until=None,
        sei="loomweave:eid:does-not-exist",
        branch=None,
        sha=None,
        rev="HEAD",
    )
    assert "meta" in payload
    _assert_local_only(payload["meta"])
