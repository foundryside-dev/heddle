from __future__ import annotations

from pathlib import Path

from heddle.store import HeddleStore, default_store_path


def test_default_store_path_is_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = default_store_path(repo, base_dir=tmp_path / "state")
    assert path.parent == tmp_path / "state"
    assert repo not in path.parents


def test_store_initializes_schema(tmp_path: Path) -> None:
    db = tmp_path / "heddle.db"
    with HeddleStore.open(db) as store:
        assert store.schema_version() == 1
