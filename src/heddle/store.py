from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path
from types import TracebackType

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', '1');
CREATE TABLE IF NOT EXISTS repos (
  id TEXT PRIMARY KEY,
  root TEXT NOT NULL,
  remote_fingerprint TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS entity_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  locator TEXT NOT NULL,
  sei TEXT,
  first_seen_commit TEXT,
  last_seen_commit TEXT,
  FOREIGN KEY(repo_id) REFERENCES repos(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS entity_keys_unique
  ON entity_keys(repo_id, locator, COALESCE(sei, ''));
CREATE TABLE IF NOT EXISTS commit_refs (
  repo_id TEXT NOT NULL,
  sha TEXT NOT NULL,
  parents_json TEXT NOT NULL,
  author TEXT NOT NULL,
  authored_at TEXT NOT NULL,
  committed_at TEXT NOT NULL,
  PRIMARY KEY(repo_id, sha)
);
CREATE TABLE IF NOT EXISTS change_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  entity_key_id INTEGER NOT NULL,
  commit_sha TEXT NOT NULL,
  path TEXT NOT NULL,
  change_kind TEXT NOT NULL,
  actor TEXT NOT NULL,
  changed_at TEXT NOT NULL,
  hunk_summary TEXT NOT NULL DEFAULT '',
  UNIQUE(repo_id, entity_key_id, commit_sha, path, change_kind),
  FOREIGN KEY(entity_key_id) REFERENCES entity_keys(id)
);
CREATE TABLE IF NOT EXISTS edge_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  commit_sha TEXT NOT NULL,
  source TEXT NOT NULL,
  source_version TEXT NOT NULL,
  captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completeness TEXT NOT NULL,
  UNIQUE(repo_id, commit_sha, source)
);
CREATE TABLE IF NOT EXISTS snapshot_edges (
  snapshot_id INTEGER NOT NULL,
  source_entity_key_id INTEGER NOT NULL,
  target_entity_key_id INTEGER NOT NULL,
  edge_kind TEXT NOT NULL,
  confidence TEXT NOT NULL,
  PRIMARY KEY(snapshot_id, source_entity_key_id, target_entity_key_id, edge_kind),
  FOREIGN KEY(snapshot_id) REFERENCES edge_snapshots(id)
);
CREATE TABLE IF NOT EXISTS health_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  code TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def default_store_path(repo: Path, base_dir: Path | None = None) -> Path:
    root = repo.resolve()
    state_root = (
        Path(os.environ["XDG_STATE_HOME"])
        if "XDG_STATE_HOME" in os.environ
        else Path.home() / ".local/state"
    )
    state = base_dir or state_root / "heddle"
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return state / f"heddle-{digest}.db"


class HeddleStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @classmethod
    def open(cls, path: Path) -> HeddleStore:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        return cls(conn)

    def __enter__(self) -> HeddleStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.conn.close()

    def schema_version(self) -> int:
        row = self.conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        if row is None:
            raise RuntimeError("missing schema_version")
        return int(row["value"])
