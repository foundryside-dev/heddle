from __future__ import annotations

import subprocess
from pathlib import Path

from warpline.store import WarplineStore, default_store_path


def test_default_store_path_uses_weft_member_runtime_tree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = default_store_path(repo)
    assert path == repo / ".weft" / "warpline" / "warpline.db"


def test_default_store_path_honors_explicit_store_dir(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = default_store_path(repo, base_dir=tmp_path / "state" / "warpline")
    assert path == tmp_path / "state" / "warpline" / "warpline.db"


def test_store_initializes_schema(tmp_path: Path) -> None:
    db = tmp_path / "warpline.db"
    with WarplineStore.open(db) as store:
        assert store.schema_version() == 3


def test_store_writes_nested_gitignore_that_ignores_runtime_db(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, text=True, capture_output=True)

    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.schema_version() == 3

    gitignore = repo / ".weft" / "warpline" / ".gitignore"
    assert gitignore.exists()
    assert "warpline.db" in gitignore.read_text(encoding="utf-8")
    ignored = subprocess.run(
        ["git", "check-ignore", ".weft/warpline/warpline.db"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    assert ignored.stdout.strip() == ".weft/warpline/warpline.db"


# --- #8: time_window bounds compare ISO-8601 offsets by UTC instant, not text -


def _write_event(
    store: WarplineStore, repo_id: str, repo: Path, locator: str, changed_at: str
) -> None:
    key_id = store.ensure_entity_key(repo_id, locator=locator, sei=None, commit_sha="c")
    store.append_change_event(
        repo_id=repo_id,
        entity_key_id=key_id,
        commit_sha=f"sha-{locator}",
        path=locator,
        change_kind="modified",
        actor="agent",
        changed_at=changed_at,
    )


def test_time_window_filter_normalizes_tz_offset(tmp_path: Path) -> None:
    """#8: since/until bounds compare the UTC INSTANT of an offset timestamp.

    "2024-01-01T09:00:00-05:00" is 14:00 UTC and "2024-01-01T10:00:00+00:00" is
    10:00 UTC. A raw-string ``>=``/``<=`` would order/filter them by the local
    wall-clock text (09 < 10), which is wrong. With ``datetime()`` normalization
    the bound sees the true instants.
    """

    repo = tmp_path / "repo"
    db = tmp_path / "warpline.db"
    with WarplineStore.open(db) as store:
        repo_id = store.ensure_repo(repo)
        # later instant, earlier-looking wall clock
        _write_event(store, repo_id, repo, "early_text_late_utc", "2024-01-01T09:00:00-05:00")
        # earlier instant, later-looking wall clock
        _write_event(store, repo_id, repo, "late_text_early_utc", "2024-01-01T10:00:00+00:00")

        # Bound at 12:00 UTC: only the 14:00-UTC event is >= it.
        rows = store.list_change_events(repo, since="2024-01-01T12:00:00+00:00")
        locators = {str(r["locator"]) for r in rows}
    assert locators == {"early_text_late_utc"}


def test_time_window_order_is_by_utc_instant(tmp_path: Path) -> None:
    """#8: ORDER BY normalizes the offset, so the earlier UTC instant comes first."""
    repo = tmp_path / "repo"
    db = tmp_path / "warpline.db"
    with WarplineStore.open(db) as store:
        repo_id = store.ensure_repo(repo)
        _write_event(store, repo_id, repo, "utc_14", "2024-01-01T09:00:00-05:00")  # 14:00Z
        _write_event(store, repo_id, repo, "utc_10", "2024-01-01T10:00:00+00:00")  # 10:00Z
        ordered = [str(r["locator"]) for r in store.list_change_events(repo)]
    # 10:00Z sorts before 14:00Z despite "10:00..." > "09:00..." lexically.
    assert ordered == ["utc_10", "utc_14"]
