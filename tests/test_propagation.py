from __future__ import annotations

import subprocess
from pathlib import Path

from warpline.propagation import blast_radius
from warpline.store import WarplineStore


def test_blast_radius_returns_no_snapshot_honestly(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        key = store.ensure_entity_key(repo_id, locator="file:a.py", sei=None, commit_sha="c1")
        result = blast_radius(store, repo, [key], depth=2)
    assert result["completeness"] == "NO_SNAPSHOT"
    assert result["affected"] == []


def test_blast_radius_walks_downstream(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(
            repo_id, locator="python:function:a", sei=None, commit_sha="c1"
        )
        b = store.ensure_entity_key(
            repo_id, locator="python:function:b", sei=None, commit_sha="c1"
        )
        snap = store.create_edge_snapshot(repo_id, "c1", "loomweave", "test", "FULL")
        store.append_snapshot_edge(
            snap,
            source_entity_key_id=a,
            target_entity_key_id=b,
            edge_kind="calls",
            confidence="resolved",
        )
        result = blast_radius(store, repo, [a], depth=2)
    assert result["completeness"] == "FULL"
    assert result["affected"][0]["entity_key_id"] == b
    assert result["affected"][0]["depth"] == 1


def _chain_store(tmp_path: Path) -> tuple[Path, Path, tuple[int, int, int]]:
    """A 3-node call chain a -> b -> c in a FULL snapshot. Returns (repo, db, (a,b,c))."""
    repo = tmp_path / "repo"
    repo.mkdir()
    db = tmp_path / "warpline.db"
    with WarplineStore.open(db) as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(repo_id, locator="python:function:a", sei=None, commit_sha="c1")
        b = store.ensure_entity_key(repo_id, locator="python:function:b", sei=None, commit_sha="c1")
        c = store.ensure_entity_key(repo_id, locator="python:function:c", sei=None, commit_sha="c1")
        snap = store.create_edge_snapshot(repo_id, "c1", "loomweave", "test", "FULL")
        for src, dst in ((a, b), (b, c)):
            store.append_snapshot_edge(
                snap, source_entity_key_id=src, target_entity_key_id=dst,
                edge_kind="calls", confidence="resolved",
            )
    return repo, db, (a, b, c)


def test_blast_radius_flags_depth_cap_when_horizon_has_unexplored_edges(tmp_path: Path) -> None:
    # depth=1 reaches b but NOT c; b (at the depth horizon) still has an out-edge
    # to the unseen c -> the traversal was truncated.
    repo, db, (a, b, _c) = _chain_store(tmp_path)
    with WarplineStore.open(db) as store:
        result = blast_radius(store, repo, [a], depth=1)
    assert {row["entity_key_id"] for row in result["affected"]} == {b}  # b only
    assert result["depth_capped"] is True


def test_blast_radius_not_capped_when_full_chain_fits(tmp_path: Path) -> None:
    # depth=2 reaches both b and c; c (at the horizon) has no out-edge -> exhaustive.
    repo, db, (a, b, c) = _chain_store(tmp_path)
    with WarplineStore.open(db) as store:
        result = blast_radius(store, repo, [a], depth=2)
    assert {row["entity_key_id"] for row in result["affected"]} == {b, c}
    assert result["depth_capped"] is False


def test_blast_radius_depth_zero_caps_when_downstream_exists(tmp_path: Path) -> None:
    repo, db, (a, _b, _c) = _chain_store(tmp_path)
    with WarplineStore.open(db) as store:
        result = blast_radius(store, repo, [a], depth=0)
    assert result["affected"] == []
    assert result["depth_capped"] is True


def test_blast_radius_no_snapshot_is_not_depth_capped(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        key = store.ensure_entity_key(repo_id, locator="file:a.py", sei=None, commit_sha="c1")
        result = blast_radius(store, repo, [key], depth=2)
    assert result["completeness"] == "NO_SNAPSHOT"
    assert result["depth_capped"] is False


def test_blast_radius_reports_snapshot_staleness(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=repo, check=True)
    (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True)
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    (repo / "a.py").write_text("a = 2\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "two"], cwd=repo, check=True)

    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        key = store.ensure_entity_key(repo_id, locator="file:a.py", sei=None, commit_sha=first)
        store.create_edge_snapshot(repo_id, first, "loomweave", "test", "FULL")
        result = blast_radius(store, repo, [key], depth=2)
    assert result["staleness"]["snapshot_commit"] == first
    assert result["staleness"]["commits_behind"] == 1
