"""Read-only store-binding/status probe (``warpline_project_status_get``).

The Lacuna MCP-attachment regression harness asserts every federation member is
not merely *attached* but *bound to and able to serve* the staged repo. warpline
is repo-per-call (bound to nothing at launch), so "bound" here means: called with
``repo=R``, this build can READ warpline's snapshot store for R at a schema it
serves. The load-bearing signal is the schema version read FROM INSIDE the store
(with an absent/error sentinel) — never mere directory existence, which a stale
binary that cannot read the store would still see.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from warpline import commands
from warpline.mcp import dispatch
from warpline.store import (
    HIGHEST_KNOWN_VERSION,
    STORE_STATUS_VOCAB,
    WarplineStore,
    default_store_path,
    read_store_binding,
    store_repo_id,
)


def _empty_store(repo: Path) -> None:
    """A real, serveable store with NO change events and NO captured snapshot."""

    with WarplineStore.open(default_store_path(repo)) as store:
        store.ensure_repo(repo)


def _set_versions(repo: Path, *, meta: int | None = None, user_version: int | None = None) -> None:
    """Tamper the on-disk schema markers independently (models a foreign writer)."""

    conn = sqlite3.connect(default_store_path(repo))
    if meta is not None:
        conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (str(meta),))
    if user_version is not None:
        conn.execute(f"PRAGMA user_version = {user_version}")
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- helpers
def _populate_store(repo: Path) -> None:
    """Build a REAL warpline store the production way (open → write → close).

    Closing the context manager triggers SQLite's last-connection WAL checkpoint,
    so the discriminator test below reads a genuine WAL-mode store — not a
    hand-built rollback-journal DB that would mask a read-only-open WAL bug.
    """

    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        key_id = store.ensure_entity_key(repo_id, "app.py::f", None, "c0ffee")
        store.append_change_event(
            repo_id=repo_id,
            entity_key_id=key_id,
            commit_sha="c0ffee",
            path="app.py",
            change_kind="modified",
            actor="agent",
            changed_at="2026-06-01T00:00:00+00:00",
        )
        store.create_edge_snapshot(repo_id, "c0ffee", "loomweave", "0", "FULL")


def _call_status(repo: Path, name: str = "warpline_project_status_get") -> dict[str, object]:
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": {"repo": str(repo)}},
        }
    )
    result = response["result"]
    assert isinstance(result, dict)
    structured = result["structuredContent"]
    assert isinstance(structured, dict)
    return structured


# --------------------------------------------------------------------------- reader: absent
def test_read_store_binding_absent_reports_absent_and_creates_nothing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    binding = read_store_binding(repo)

    assert binding.present is False
    assert binding.readable is False
    assert binding.schema_version is None
    assert binding.snapshot_rev is None
    assert binding.change_event_count is None
    assert binding.binding_ok is False
    assert binding.status == "store_absent"
    # Read-only: an absent store stays absent — never initialized.
    assert not (repo / ".weft" / "warpline").exists()
    assert not default_store_path(repo).exists()


# --- reader: the WAL discriminator
def test_read_store_binding_present_readable_real_wal_store(tmp_path: Path) -> None:
    """The load-bearing test: a real, closed (checkpointed) WAL store reads OK."""

    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)

    binding = read_store_binding(repo)

    assert binding.present is True
    assert binding.readable is True
    assert binding.schema_version == HIGHEST_KNOWN_VERSION
    assert binding.binding_ok is True
    assert binding.change_event_count == 1
    assert binding.snapshot_rev == "c0ffee"
    assert binding.status == "ok"


# --- reader: schema ahead (stale binary)
def test_read_store_binding_schema_ahead_is_unreadable(tmp_path: Path) -> None:
    """A store written by a NEWER build (schema beyond this build) is the
    stale-binary case: readable=False, schema_version=null, binding_ok=False."""

    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)
    ahead = HIGHEST_KNOWN_VERSION + 99
    conn = sqlite3.connect(default_store_path(repo))
    conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (str(ahead),))
    conn.execute(f"PRAGMA user_version = {ahead}")
    conn.commit()
    conn.close()

    binding = read_store_binding(repo)

    assert binding.present is True
    assert binding.readable is False
    assert binding.schema_version is None
    assert binding.binding_ok is False
    assert binding.status == "schema_ahead"
    assert str(ahead) in binding.detail


# --------------------------------------------------------------------------- reader: corrupt
def test_read_store_binding_corrupt_store_is_unreadable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    store_path = default_store_path(repo)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_bytes(b"this is not a sqlite database")

    binding = read_store_binding(repo)

    assert binding.present is True
    assert binding.readable is False
    assert binding.schema_version is None
    assert binding.binding_ok is False
    assert binding.status == "store_unreadable"


# --- tools/list registration + honest metadata
def test_project_status_in_tools_list_with_read_only_metadata() -> None:
    response = dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    tools = response["result"]["tools"]
    by_name = {tool["name"]: tool for tool in tools}

    assert "warpline_project_status_get" in by_name
    assert "project_status" in by_name
    meta = by_name["warpline_project_status_get"]["metadata"]
    # The whole point: this tool is GENUINELY read-only — it writes/initializes
    # nothing, unlike the lazy-init read tools that declare writes_local_state.
    assert meta["read_only"] is True
    assert meta["writes_local_state"] is False
    assert meta["mutates_paths"] == []
    assert meta["local_only"] is True
    assert meta["peer_side_effects"] == []


# --------------------------------------------------------------------------- dispatch: bound
def test_project_status_binding_ok_over_mcp(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)

    payload = _call_status(repo)

    assert payload["schema"] == "warpline.project_status.v1"
    assert payload["ok"] is True
    data = payload["data"]
    assert isinstance(data, dict)
    assert data["resolved_root"] == str(repo.resolve())
    assert data["binding_ok"] is True
    store = data["store"]
    assert isinstance(store, dict)
    assert store["present"] is True
    assert store["readable"] is True
    assert store["schema_version"] == HIGHEST_KNOWN_VERSION
    # honesty meta rides on the envelope like every warpline payload
    assert payload["meta"]["local_only"] is True
    assert payload["meta"]["peer_side_effects"] == []


# --- dispatch: absent → not bound + next action
def test_project_status_absent_store_over_mcp(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    payload = _call_status(repo)

    assert payload["ok"] is True  # the CALL succeeded; the VERDICT is binding_ok
    data = payload["data"]
    assert isinstance(data, dict)
    assert data["binding_ok"] is False
    assert data["store"]["present"] is False
    assert data["store"]["schema_version"] is None
    # an absent store gets a ready-to-call capture hint
    assert "warpline_edge_snapshot_capture" in payload["next_actions"]


# --------------------------------------------------------------------------- dispatch: schema ahead
def test_project_status_schema_ahead_over_mcp(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)
    ahead = HIGHEST_KNOWN_VERSION + 99
    conn = sqlite3.connect(default_store_path(repo))
    conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (str(ahead),))
    conn.execute(f"PRAGMA user_version = {ahead}")
    conn.commit()
    conn.close()

    payload = _call_status(repo)
    data = payload["data"]
    assert isinstance(data, dict)
    assert data["binding_ok"] is False
    assert data["store"]["readable"] is False
    assert data["store"]["schema_version"] is None


# --- dispatch: read-only invariant
def test_project_status_over_mcp_initializes_nothing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    _call_status(repo)

    # The full dispatch path must not mkdir / open / migrate the store.
    assert not (repo / ".weft" / "warpline").exists()
    assert not default_store_path(repo).exists()


# --------------------------------------------------------------------------- endorsed == shim
def test_project_status_endorsed_and_shim_identical(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)

    endorsed = _call_status(repo, "warpline_project_status_get")
    shim = _call_status(repo, "project_status")

    assert endorsed["schema"] == shim["schema"] == "warpline.project_status.v1"
    assert endorsed["data"] == shim["data"]


# --------------------------------------------------------------------------- command-layer direct
def test_command_project_status_envelope_shape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    envelope = commands.project_status(repo)

    assert envelope["schema"] == "warpline.project_status.v1"
    assert envelope["ok"] is True
    assert set(envelope["data"]["store"]) == {
        "present",
        "readable",
        "schema_version",
        "snapshot_rev",
        "change_event_count",
    }


# --- D4: each arm of max(meta, user_version) must independently trip schema_ahead
def test_schema_ahead_when_only_user_version_is_bumped(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)
    # meta stays at HIGHEST; only PRAGMA user_version moves ahead.
    _set_versions(repo, user_version=HIGHEST_KNOWN_VERSION + 5)

    binding = read_store_binding(repo)

    assert binding.status == "schema_ahead"
    assert binding.readable is False
    assert binding.schema_version is None
    assert binding.binding_ok is False


def test_schema_ahead_when_only_meta_is_bumped(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)
    # user_version stays at HIGHEST; only the meta marker moves ahead.
    _set_versions(repo, meta=HIGHEST_KNOWN_VERSION + 5)

    binding = read_store_binding(repo)

    assert binding.status == "schema_ahead"
    assert binding.readable is False
    assert binding.schema_version is None
    assert binding.binding_ok is False


# --- D3: an empty-but-serveable store is bound (binding_ok independent of count/snapshot)
def test_empty_but_serveable_store_is_bound(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _empty_store(repo)

    binding = read_store_binding(repo)

    assert binding.present is True
    assert binding.readable is True
    assert binding.binding_ok is True
    assert binding.status == "ok"
    assert binding.schema_version == HIGHEST_KNOWN_VERSION
    # binding_ok does NOT require any change events or a captured snapshot
    assert binding.change_event_count == 0
    assert binding.snapshot_rev is None


# --- a store BELOW this build's HIGHEST schema is still serveable
def test_below_highest_schema_is_serveable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)
    # Model an older store this build still knows how to read (v2 < HIGHEST=4).
    _set_versions(repo, meta=2, user_version=2)

    binding = read_store_binding(repo)

    assert binding.readable is True
    assert binding.binding_ok is True
    assert binding.status == "ok"
    assert binding.schema_version == 2


# --- read-only invariant on a PRESENT store: the durable DB is never mutated
def test_present_store_durable_db_unchanged_after_probe(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)
    db = default_store_path(repo)
    before = hashlib.sha256(db.read_bytes()).hexdigest()

    # full dispatch path, twice (idempotent, no durable writes)
    _call_status(repo)
    _call_status(repo)

    after = hashlib.sha256(db.read_bytes()).hexdigest()
    assert after == before  # no rows written; the snapshot store is untouched


# --- store dir exists but the DB file does not → absent
def test_dir_without_db_is_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    default_store_path(repo).parent.mkdir(parents=True, exist_ok=True)  # .weft/warpline, no db

    binding = read_store_binding(repo)

    assert binding.present is False
    assert binding.status == "store_absent"
    assert binding.binding_ok is False


# --- the change-event count is scoped to THIS repo, not the whole DB
def test_change_event_count_is_repo_scoped(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)  # 1 event for this repo
    # Inject events under a DIFFERENT (phantom) repo_id into the same DB.
    conn = sqlite3.connect(default_store_path(repo))
    phantom = store_repo_id(tmp_path / "other-repo")
    assert phantom != store_repo_id(repo)
    conn.execute(
        "INSERT INTO entity_keys(repo_id, locator, sei, first_seen_commit, last_seen_commit) "
        "VALUES (?, 'x', NULL, 'p1', 'p1')",
        (phantom,),
    )
    key_id = conn.execute("SELECT id FROM entity_keys WHERE repo_id = ?", (phantom,)).fetchone()[0]
    conn.execute(
        "INSERT INTO change_events(repo_id, entity_key_id, commit_sha, path, change_kind, "
        "actor, changed_at) VALUES (?, ?, 'p1', 'x', 'modified', 'a', '2026-01-01T00:00:00+00:00')",
        (phantom, key_id),
    )
    conn.commit()
    conn.close()

    binding = read_store_binding(repo)

    assert binding.change_event_count == 1  # only the probed repo's event, not the phantom's


# --- store_status is always a member of the closed vocab
def test_store_status_is_always_in_closed_vocab(tmp_path: Path) -> None:
    # bound
    bound = tmp_path / "bound"
    bound.mkdir()
    _populate_store(bound)
    # absent
    absent = tmp_path / "absent"
    absent.mkdir()
    # corrupt
    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    cp = default_store_path(corrupt)
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_bytes(b"nope")
    # schema ahead
    ahead = tmp_path / "ahead"
    ahead.mkdir()
    _populate_store(ahead)
    _set_versions(ahead, meta=HIGHEST_KNOWN_VERSION + 9, user_version=HIGHEST_KNOWN_VERSION + 9)

    seen = {read_store_binding(r).status for r in (bound, absent, corrupt, ahead)}
    assert seen == {"ok", "store_absent", "store_unreadable", "schema_ahead"}
    assert seen <= STORE_STATUS_VOCAB


# --- dispatch surfaces the honest store_status + warning for not-bound stores
def test_dispatch_absent_surfaces_status_and_no_warning_noise(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = _call_status(repo)
    assert payload["data"]["store_status"] == "store_absent"


def test_dispatch_schema_ahead_surfaces_status_and_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _populate_store(repo)
    ahead = HIGHEST_KNOWN_VERSION + 99
    _set_versions(repo, meta=ahead, user_version=ahead)

    payload = _call_status(repo)

    assert payload["data"]["store_status"] == "schema_ahead"
    warnings = payload["warnings"]
    assert isinstance(warnings, list) and warnings
    assert str(ahead) in warnings[0]  # the on-disk version is named explicitly
