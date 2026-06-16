"""Rung 1d — always-on lazy edge-snapshot capture (M6, Option A).

The post-commit hook only ingests, so a cold repo has no edge snapshot and
``blast_radius`` honestly returns NO_SNAPSHOT. The lazy capture restores the
correctness floor on the *read* path (``impact_radius`` / ``reverify_worklist``)
whenever loomweave is reachable — always-on internally, with NO ``auto_capture``
inputSchema field on the frozen tools.

Doctrine asserted here:
* ``blast_radius`` stays PURE (R7) — its signature is unchanged.
* lazy capture is fail-soft: no loomweave -> unchanged NO_SNAPSHOT, never raises.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import commit, init_repo

from warpline import commands
from warpline.propagation import blast_radius
from warpline.store import WarplineStore, default_store_path


class _FakeNeighborhoodClient:
    """Stands in for ``LoomweaveMcpClient``: a -> b call edge."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.calls: list[str] = []

    def neighborhood(self, entity: str) -> dict[str, object]:
        self.calls.append(entity)
        if entity == "python:function:a":
            return {
                "entity": {"id": "python:function:a"},
                "callees": [{"id": "python:function:b"}],
                "truncated": {"callers": False, "callees": False},
            }
        return {
            "entity": {"id": entity},
            "truncated": {"callers": False, "callees": False},
        }


def _seed_two_entities(repo: Path) -> tuple[int, int]:
    """Two warpline-local entity_keys (a, b) and NO snapshot. Returns (a_id, b_id)."""

    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(
            repo_id, locator="python:function:a", sei=None, commit_sha="c1"
        )
        b = store.ensure_entity_key(
            repo_id, locator="python:function:b", sei=None, commit_sha="c1"
        )
    return a, b


def _force_loomweave_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        commands.LoomweaveProbe,
        "probe",
        lambda self: {"status": "available", "version": "fake-1"},
    )
    monkeypatch.setattr(commands, "LoomweaveMcpClient", _FakeNeighborhoodClient)


def test_impact_radius_lazily_captures_when_loomweave_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")  # a real HEAD for capture's git rev-parse
    a, _b = _seed_two_entities(repo)
    _force_loomweave_available(monkeypatch)

    # Precondition: no snapshot, so a *pure* blast_radius is NO_SNAPSHOT.
    with WarplineStore.open(default_store_path(repo)) as store:
        cold = blast_radius(store, repo, [a], depth=2)
    assert cold["completeness"] == "NO_SNAPSHOT"
    assert cold["affected"] == []

    # impact_radius triggers the lazy capture, then traverses the populated graph.
    payload = commands.impact_radius(repo, [a], depth=2)
    assert payload["data"]["completeness"] == "FULL"
    affected_locators = {
        item["entity"]["locator"] for item in payload["data"]["affected"]
    }
    assert "python:function:b" in affected_locators

    # The snapshot now persists: a second read needs no capture (probe is skipped).
    with WarplineStore.open(default_store_path(repo)) as store:
        snap = store.latest_snapshot(repo)
    assert snap is not None
    assert snap["completeness"] == "FULL"


def test_reverify_worklist_lazily_captures_when_loomweave_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)
    _force_loomweave_available(monkeypatch)

    payload = commands.reverify_worklist(repo, [a], depth=2)
    assert payload["data"]["completeness"] == "FULL"
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.latest_snapshot(repo) is not None


def test_no_loomweave_falls_through_to_no_snapshot_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)
    # loomweave unreachable -> honest fall-through, no error, no gate.
    monkeypatch.setattr(
        commands.LoomweaveProbe,
        "probe",
        lambda self: {"status": "skipped", "reason": "command_unavailable"},
    )

    payload = commands.impact_radius(repo, [a], depth=2)
    assert payload["data"]["completeness"] == "NO_SNAPSHOT"
    assert payload["data"]["affected"] == []
    # No snapshot was written (loomweave never consulted for a capture).
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.latest_snapshot(repo) is None


def test_lazy_capture_is_fail_soft_when_probe_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)

    def _boom(self: object) -> dict[str, object]:
        raise RuntimeError("loomweave exploded")

    monkeypatch.setattr(commands.LoomweaveProbe, "probe", _boom)

    # The read must still succeed honestly — never propagate the capture failure.
    payload = commands.impact_radius(repo, [a], depth=2)
    assert payload["data"]["completeness"] == "NO_SNAPSHOT"


def test_lazy_capture_skips_when_snapshot_already_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, b = _seed_two_entities(repo)
    # An existing FULL snapshot must short-circuit the probe entirely.
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        sid = store.create_edge_snapshot(repo_id, "c1", "loomweave", "v0", "FULL")
        store.append_snapshot_edge(
            sid,
            source_entity_key_id=a,
            target_entity_key_id=b,
            edge_kind="calls",
            confidence="resolved",
        )

    probe_calls: list[int] = []

    def _track(self: object) -> dict[str, object]:
        probe_calls.append(1)
        return {"status": "available", "version": "fake"}

    monkeypatch.setattr(commands.LoomweaveProbe, "probe", _track)

    commands.impact_radius(repo, [a], depth=2)
    assert probe_calls == []  # snapshot present -> capture machinery never engaged


def test_blast_radius_signature_stays_pure() -> None:
    """R7: no ``on_missing_snapshot`` / lazy-capture parameter leaked into the
    pure traversal."""

    params = set(inspect.signature(blast_radius).parameters)
    assert params == {"store", "repo", "changed_entity_key_ids", "depth"}


def test_unavailable_loomweave_probes_at_most_once_within_cooldown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When loomweave is unavailable, the probe (a ~1-5s subprocess spin-up) must
    be throttled: a second read within the cooldown window must NOT re-probe — yet
    the read still honestly falls through to NO_SNAPSHOT (advisory, never gates)."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)

    probe_calls: list[int] = []

    def _unavailable(self: object) -> dict[str, object]:
        probe_calls.append(1)
        return {"status": "skipped", "reason": "command_unavailable"}

    monkeypatch.setattr(commands.LoomweaveProbe, "probe", _unavailable)

    first = commands.impact_radius(repo, [a], depth=2)
    assert first["data"]["completeness"] == "NO_SNAPSHOT"
    assert len(probe_calls) == 1  # first read probes once.

    second = commands.impact_radius(repo, [a], depth=2)
    assert second["data"]["completeness"] == "NO_SNAPSHOT"
    # Throttle holds: the second read inside the cooldown must NOT re-probe.
    assert len(probe_calls) == 1
    # Still no snapshot written — the honest NO_SNAPSHOT fall-through is intact.
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.latest_snapshot(repo) is None


def test_throttle_expires_and_reprobes_after_cooldown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The throttle must not permanently disable capture: once the cooldown
    elapses the probe is retried, so loomweave coming back online is picked up."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)

    probe_calls: list[int] = []

    def _unavailable(self: object) -> dict[str, object]:
        probe_calls.append(1)
        return {"status": "skipped", "reason": "command_unavailable"}

    monkeypatch.setattr(commands.LoomweaveProbe, "probe", _unavailable)

    # Pin the clock so the first attempt is recorded at a known instant.
    base = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(commands, "_now", lambda: base)
    commands.impact_radius(repo, [a], depth=2)
    assert len(probe_calls) == 1

    # Still inside the cooldown -> no re-probe.
    monkeypatch.setattr(
        commands,
        "_now",
        lambda: base + timedelta(seconds=commands._LAZY_CAPTURE_COOLDOWN_SECONDS - 1),
    )
    commands.impact_radius(repo, [a], depth=2)
    assert len(probe_calls) == 1

    # Past the cooldown -> the probe is retried (recovery path stays open).
    monkeypatch.setattr(
        commands,
        "_now",
        lambda: base + timedelta(seconds=commands._LAZY_CAPTURE_COOLDOWN_SECONDS + 1),
    )
    commands.impact_radius(repo, [a], depth=2)
    assert len(probe_calls) == 2


def test_throttle_does_not_block_capture_when_loomweave_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A prior unavailable attempt records a throttle marker, but the FIRST read
    after loomweave recovers (past cooldown) must still capture a usable snapshot —
    the throttle gates the probe cost, not the success path."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)

    base = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(commands, "_now", lambda: base)
    monkeypatch.setattr(
        commands.LoomweaveProbe,
        "probe",
        lambda self: {"status": "skipped", "reason": "command_unavailable"},
    )
    commands.impact_radius(repo, [a], depth=2)
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.latest_snapshot(repo) is None

    # loomweave recovers; advance past the cooldown so the probe is allowed.
    monkeypatch.setattr(
        commands,
        "_now",
        lambda: base + timedelta(seconds=commands._LAZY_CAPTURE_COOLDOWN_SECONDS + 1),
    )
    _force_loomweave_available(monkeypatch)
    payload = commands.impact_radius(repo, [a], depth=2)
    assert payload["data"]["completeness"] == "FULL"
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.latest_snapshot(repo) is not None


def test_available_loomweave_still_captures_on_first_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard the success path: the throttle must not suppress a capture when
    loomweave is available on the very first read (no prior attempt marker)."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)
    _force_loomweave_available(monkeypatch)

    payload = commands.impact_radius(repo, [a], depth=2)
    assert payload["data"]["completeness"] == "FULL"
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.latest_snapshot(repo) is not None
