from __future__ import annotations

from pathlib import Path

from heddle.snapshot import capture_edge_snapshot, record_skipped_snapshot
from heddle.store import HeddleStore


class FakeNeighborhoodClient:
    def __init__(self) -> None:
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


class TruncatedNeighborhoodClient:
    def neighborhood(self, entity: str) -> dict[str, object]:
        return {
            "entity": {"id": entity},
            "callees": [{"id": "python:function:b"}],
            "truncated": {"callers": False, "callees": True},
        }


class LoomweaveIdNeighborhoodClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def neighborhood(self, entity: str) -> dict[str, object]:
        self.calls.append(entity)
        if entity != "python:function:pkg.mod.changed":
            return {
                "entity": {"id": entity},
                "truncated": {"callers": False, "callees": False},
            }
        return {
            "entity": {"id": "python:function:pkg.mod.changed"},
            "callees": [{"id": "python:function:pkg.other.affected"}],
            "truncated": {"callers": False, "callees": False},
        }


def test_skipped_snapshot_is_queryable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with HeddleStore.open(tmp_path / "heddle.db") as store:
        repo_id = store.ensure_repo(repo)
        record_skipped_snapshot(store, repo_id, "abc123", reason="no_index")
        snap = store.latest_snapshot(repo)

    assert snap is not None
    assert snap["completeness"] == "SKIPPED"
    assert snap["source"] == "loomweave"
    assert snap["source_version"] == "no_index"


def test_capture_edge_snapshot_records_loomweave_edges(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    client = FakeNeighborhoodClient()
    with HeddleStore.open(tmp_path / "heddle.db") as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(
            repo_id, locator="python:function:a", sei=None, commit_sha="c1"
        )
        result = capture_edge_snapshot(
            store,
            repo,
            commit_sha="c1",
            client=client,
            source_version="test-client",
        )
        snapshot = store.latest_snapshot(repo)
        assert snapshot is not None
        edges = store.snapshot_edges(int(snapshot["id"]))

    assert result["completeness"] == "FULL"
    assert result["edges"] == 1
    assert client.calls == ["python:function:a"]
    assert edges == [
        {
            "source_entity_key_id": a,
            "target_entity_key_id": a + 1,
            "edge_kind": "calls",
            "confidence": "resolved",
        }
    ]


def test_capture_edge_snapshot_maps_loomweave_ids_back_to_heddle_keys(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    client = LoomweaveIdNeighborhoodClient()
    with HeddleStore.open(tmp_path / "heddle.db") as store:
        repo_id = store.ensure_repo(repo)
        changed = store.ensure_entity_key(
            repo_id, locator="python:function:pkg/mod.py::changed", sei=None, commit_sha="c1"
        )
        affected = store.ensure_entity_key(
            repo_id, locator="python:function:pkg/other.py::affected", sei=None, commit_sha="c1"
        )
        result = capture_edge_snapshot(
            store,
            repo,
            commit_sha="c1",
            client=client,
            source_version="test-client",
        )
        snapshot = store.latest_snapshot(repo)
        assert snapshot is not None
        edges = store.snapshot_edges(int(snapshot["id"]))

    assert result["completeness"] == "FULL"
    assert client.calls == [
        "python:function:pkg.mod.changed",
        "python:function:pkg.other.affected",
    ]
    assert {
        "source_entity_key_id": changed,
        "target_entity_key_id": affected,
        "edge_kind": "calls",
        "confidence": "resolved",
    } in edges


def test_capture_edge_snapshot_clears_edges_on_recapture(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with HeddleStore.open(tmp_path / "heddle.db") as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(
            repo_id, locator="python:function:a", sei=None, commit_sha="c1"
        )
        b = store.ensure_entity_key(
            repo_id, locator="python:function:b", sei=None, commit_sha="c1"
        )
        snapshot_id = store.create_edge_snapshot(repo_id, "c1", "loomweave", "old", "FULL")
        store.append_snapshot_edge(
            snapshot_id,
            source_entity_key_id=a,
            target_entity_key_id=b,
            edge_kind="calls",
            confidence="resolved",
        )

        capture_edge_snapshot(
            store,
            repo,
            commit_sha="c1",
            client=None,
            source_version="no_index",
        )
        edges = store.snapshot_edges(snapshot_id)
        snapshot = store.latest_snapshot(repo)

    assert edges == []
    assert snapshot is not None
    assert snapshot["completeness"] == "SKIPPED"
    assert snapshot["source_version"] == "no_index"


def test_capture_edge_snapshot_degrades_truncated_neighborhood_to_delta(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with HeddleStore.open(tmp_path / "heddle.db") as store:
        repo_id = store.ensure_repo(repo)
        store.ensure_entity_key(repo_id, locator="python:function:a", sei=None, commit_sha="c1")
        result = capture_edge_snapshot(
            store,
            repo,
            commit_sha="c1",
            client=TruncatedNeighborhoodClient(),
            source_version="test-client",
        )
        snapshot = store.latest_snapshot(repo)
        assert snapshot is not None
        edges = store.snapshot_edges(int(snapshot["id"]))

    assert result["completeness"] == "DELTA"
    assert result["failed_entities"] == [
        {
            "locator": "python:function:a",
            "reason": "truncated neighborhood cannot be snapshotted as complete",
        }
    ]
    assert snapshot["completeness"] == "DELTA"
    assert edges == []
