# Verification-Freshness (Rung 2, Track B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give warpline a `last_verified` axis sourced from its own gate result, so the reverify worklist surfaces an honest per-item `fresh / stale / unverified / unavailable` verification state plus a trust-decay signal — advisory, enrich-only, never gating.

**Architecture:** A new `verification_events` table (schema v4) records "gate K passed as-of commit C" (one row per run, mirroring `change_events`). A new mutating verb `verify-record` (CLI + MCP, the 2nd mutating tool) writes those rows. A pure `compose_verification_freshness` function (mirroring `_enrichment.py`) computes per-entity freshness by git reachability (`covers(verified_commit, change_commit)`). The reverify command attaches a `verification` block to each worklist item plus a `verification_summary` rollup to the `data` block, advisory-sorts stale-of-trust first, and **never filters**.

**Tech Stack:** Python 3 (stdlib `sqlite3`, `subprocess` for git), the existing warpline store/envelope/listing modules, argparse CLI, hand-rolled JSON-RPC MCP server. No new dependencies.

## Global Constraints

These bind **every** task. Copied from the spec and the frozen contract:

- **Enrich-only, never gates.** Verification annotates and may re-sort the worklist; it MUST NEVER remove/filter an item. (Hard anti-goal.)
- **`meta.local_only: true` and `meta.peer_side_effects: []`** on every envelope — preserved, never weakened.
- **The frozen closed enrichment vocab is exactly 6 keys** (`sei`, `edges`, `work`, `risk`, `governance`, `requirements`). Verification is **NOT** added to it. It rides as a reverify-worklist-item field and a `data`-block summary. `build_envelope` raises `ValueError` if you put any other key into `enrichment`/`enrichment_reasons` — so verification MUST NOT appear there.
- **The canonical 11 `reason_class` values are frozen** (`clean`, `disabled`, `unresolved_input`, `rejected`, `dead_path`, `unreachable`, `misrouted`, `error`, `scheme_mismatch`, `stale`, `partial`). Reuse them — add NO new class. (Mapping below.)
- **Every non-`fresh`/non-clean state carries a weft-reason triple** `{reason_class, cause, fix}` via `listing.reason()`. Absence is always EXPLAINED, never a bare scalar and never read as verified.
- **The frozen `entity` view is `{locator, sei}` only** (`refs.py:entity_view`). Do NOT add fields to it; thread `entity_key_id` separately.
- **Commit SHAs are stored resolved.** Never store a symbolic ref (`HEAD`) — always resolve to an object SHA first (the Plan A lesson).
- **Migrations use `conn.execute()` only**, never `executescript()` (which implicit-commits and breaks the runner's `BEGIN IMMEDIATE` atomicity). All columns/tables NULLable-friendly and additive.
- **Gates that must stay green:** `uv run ruff check .`, `uv run mypy src/warpline`, `uv run pytest tests -v`, `uv run warpline dogfood-eval`, `uv run warpline mcp-smoke`, and the member-diff guard. The mutating tool must appear in `tools/list` with correct metadata.
- **Version:** this is an additive **minor** (`1.3.0`) — new tool + new reverify-item field, frozen contracts untouched. The CHANGELOG gets an `[Unreleased]`/`1.3.0` entry; **the actual tag/release is owner-reserved and out of scope for this plan** (stop at merge-ready).

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `src/warpline/store.py` | v4 `verification_events` table: migration, presence-floor, accessors | Modify |
| `src/warpline/git.py` | `is_ancestor` / `commits_between` / `resolve_commit` reachability helpers | Modify |
| `src/warpline/verification.py` | Pure `compose_verification_freshness` + reason mapping | **Create** |
| `src/warpline/commands.py` | `verify_record` verb; reverify integration (verification_index, summary, advisory sort); `SCHEMA_VERIFICATION_RECORD` | Modify |
| `src/warpline/cli.py` | `verify-record` subcommand wiring | Modify |
| `src/warpline/mcp.py` | `warpline_verification_record` tool spec + handler + consumes map | Modify |
| `src/warpline/reverify.py` | Thread per-item `verification` block into rendered items | Modify |
| `tests/test_verification_store.py` | v4 migration + accessor tests | **Create** |
| `tests/test_git_reachability.py` | `is_ancestor`/`commits_between`/`resolve_commit` tests | **Create** |
| `tests/test_verification_compose.py` | Pure freshness unit tests (vectors-first) | **Create** |
| `tests/test_verify_record.py` | verb + MCP tool + error tests | **Create** |
| `tests/test_reverify_verification.py` | reverify integration tests (block, summary, never-filter, sort) | **Create** |
| `tests/contracts/test_golden_vectors.py` | `GV-VF-1` golden vector | Modify |
| `tests/fixtures/contracts/warpline/golden-vectors.json` | `GV-VF-1` fixture entry | Modify |
| `docs/reference/cli.md`, `docs/reference/mcp-tools.md` | document `verify-record` / `warpline_verification_record` | Modify |
| `CHANGELOG.md` | `[Unreleased]` / 1.3.0 entry | Modify |

---

## Reference: existing patterns (read before starting)

- **Migration machinery** — `store.py`: `Migration` NamedTuple (`store.py:123-133`), `MIGRATIONS` list (`store.py:204-207`), `HIGHEST_KNOWN_VERSION = max(... )` (`store.py:213`), `_run_migrations` runner (`store.py:324-442`, opens `BEGIN IMMEDIATE`, calls `migration.apply(conn)`, bumps `PRAGMA user_version` + `meta`), `_schema_presence_floor` (`store.py:286-321`), `_table_exists` (`store.py:268-273`), v3 migration `_migrate_v3_co_change_pairs` (`store.py:163-194`).
- **`change_events` template** — DDL `store.py:68-80`; insert `append_change_event` (`store.py:881-924`, `INSERT OR IGNORE` + `self.conn.commit()`); query `list_change_events` (`store.py:944-1003`, JOINs `entity_keys`, returns `list[dict]` with `entity_key_id`, `commit_sha`, `changed_at`). `_repo_id` = sha256 of resolved path (`store.py:490-491`); `ensure_repo(repo) -> str` (`store.py:493-501`).
- **Mutating verb template** — `capture_snapshot` (`commands.py:994-1149`); schema consts (`commands.py:44-50`); `build_envelope` (`envelope.py:61-99`) which always injects `enrichment_reasons.requirements` and validates the closed vocab; `local_only_meta` (`envelope.py:44-58`).
- **CLI wiring** — `capture-snapshot` subparser (`cli.py:334-339`) + dispatch (`cli.py:525-532`).
- **MCP wiring** — `_tool_spec` for `warpline_edge_snapshot_capture` (`mcp.py:217-242`); `_metadata` helper (`mcp.py:39-57`); `_HANDLERS` zip (`mcp.py:436-443`); `_h_capture` (`mcp.py:423-433`); `_HANDLER_CONSUMES` (`mcp.py:510-521`); `WarplineError → _error` conversion (`mcp.py:653-661`).
- **Errors** — `ERROR_CODES` frozen set (`errors.py:8-23`, includes `invalid_rev_range`, `invalid_entity_ref`); `WarplineError` base (`errors.py:26-67`); `BadRevisionError(code="invalid_rev_range")` (`errors.py:83-87`).
- **Pure enrichment** — `_enrichment.py` whole file (imports only `typing.Any` + `listing.reason`; no store/git/IO). `listing.reason(reason_class, *, cause, fix)` (`listing.py:34-44`); `REASON_CLASSES` (`listing.py:17-31`).
- **Reverify** — `render_reverify_worklist` (`reverify.py:19-79`, builds per-item dict, returns `(items, work_seen, candidates)`); `reverify_worklist` command (`commands.py:745-876`, pipeline: `compute_blast_radius` → `enrich_blast` → `render_reverify_worklist` → `apply_filters` → `apply_sort` → federation → `apply_overflow` → `apply_page` → `build_envelope`); `enrich_blast` (`_blast.py:123-157`, **drops `entity_key_id`** — the entity view is `{locator, sei}`).
- **Git reachability template** — `_commits_behind` (`propagation.py:19-32`, `git rev-list --count A..HEAD`); generic runners `_git`/`_git_optional` (`git.py:14-21`, `74-82`).
- **Golden vectors** — test `tests/contracts/test_golden_vectors.py` (e.g. `test_gv_hon_sei_*` ~line 410); fixture index `tests/fixtures/contracts/warpline/golden-vectors.json`. Helpers `_git_repo`, `_store`, `_seed_entity`, `_add_change` live in that test module — reuse them.

---

## Task 1: v4 `verification_events` schema + accessors (store)

**Files:**
- Modify: `src/warpline/store.py` (SCHEMA base block; `MIGRATIONS` list; `_schema_presence_floor`; new accessor methods)
- Test: `tests/test_verification_store.py` (create)

**Interfaces:**
- Consumes: existing `WarplineStore.open(path)`, `ensure_repo(repo) -> str`, `_repo_id(repo) -> str`, `default_store_path(repo)`.
- Produces:
  - `WarplineStore.record_verification_event(*, repo_id: str, commit_sha: str, kind: str, verified_at: str, actor: str | None, source: str = "warpline") -> bool` — `INSERT OR IGNORE` (idempotent on the UNIQUE key), commits; returns `True` if a new row was inserted, `False` if it already existed.
  - `WarplineStore.list_verification_events(repo: Path) -> list[dict[str, object]]` — all rows for the repo, ordered **oldest-first by the normalized `verified_at` instant** then `id` (NOT a raw lexical sort — see Step 5; a caller-supplied non-UTC offset must still sort chronologically). Each dict has keys `commit_sha`, `kind`, `verified_at`, `actor`, `source`.
  - `WarplineStore.list_change_events_for_key_ids(repo: Path, key_ids: list[int]) -> list[dict[str, object]]` — change events filtered to the given entity key ids (empty list → `[]`). Avoids the full-table scan when reverify only needs the worklist's entities.
  - Schema is at version **4**; presence-floor recognises `verification_events`. (This also requires updating the existing `tests/test_store_migrations.py` pin — Step 6b.)

- [ ] **Step 1: Write the failing migration + accessor tests**

Create `tests/test_verification_store.py`:

```python
from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

from warpline.store import HIGHEST_KNOWN_VERSION, WarplineStore, default_store_path


def _open(tmp_path: Path) -> WarplineStore:
    return WarplineStore.open(default_store_path(tmp_path))


def test_schema_reaches_version_4(tmp_path: Path) -> None:
    with _open(tmp_path) as store:
        version = store.conn.execute("PRAGMA user_version").fetchone()[0]
        assert int(version) == 4
        assert HIGHEST_KNOWN_VERSION == 4


def test_verification_events_table_exists(tmp_path: Path) -> None:
    with _open(tmp_path) as store:
        row = store.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='verification_events'"
        ).fetchone()
        assert row is not None


def test_reopen_is_idempotent(tmp_path: Path) -> None:
    path = default_store_path(tmp_path)
    with WarplineStore.open(path) as store:
        store.conn.execute("PRAGMA user_version").fetchone()
    # Re-open: no migration re-runs, no error, still v4.
    with WarplineStore.open(path) as store:
        assert int(store.conn.execute("PRAGMA user_version").fetchone()[0]) == 4


def test_presence_floor_recovers_dropped_table(tmp_path: Path) -> None:
    path = default_store_path(tmp_path)
    with WarplineStore.open(path) as store:
        pass
    # Simulate a v4 marker whose table is missing on disk: drop it and lie in meta.
    raw = sqlite3.connect(path)
    raw.execute("DROP TABLE verification_events")
    raw.commit()
    raw.close()
    # Re-open: presence-floor must detect the missing table and re-run v4.
    with WarplineStore.open(path) as store:
        row = store.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='verification_events'"
        ).fetchone()
        assert row is not None


def test_record_and_list_round_trip(tmp_path: Path) -> None:
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(tmp_path)
        store.record_verification_event(
            repo_id=repo_id,
            commit_sha="a" * 40,
            kind="test_pass",
            verified_at="2026-06-25T10:00:00+00:00",
            actor="ci-bot",
            source="warpline",
        )
        events = store.list_verification_events(tmp_path)
        assert len(events) == 1
        assert events[0]["commit_sha"] == "a" * 40
        assert events[0]["kind"] == "test_pass"
        assert events[0]["actor"] == "ci-bot"
        assert events[0]["source"] == "warpline"


def test_record_is_idempotent_on_unique_key(tmp_path: Path) -> None:
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(tmp_path)
        for _ in range(2):
            store.record_verification_event(
                repo_id=repo_id,
                commit_sha="b" * 40,
                kind="test_pass",
                verified_at="2026-06-25T10:00:00+00:00",
                actor="ci-bot",
                source="warpline",
            )
        assert len(store.list_verification_events(tmp_path)) == 1


def test_list_orders_by_verified_at(tmp_path: Path) -> None:
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(tmp_path)
        store.record_verification_event(
            repo_id=repo_id, commit_sha="c" * 40, kind="test_pass",
            verified_at="2026-06-25T12:00:00+00:00", actor=None, source="warpline",
        )
        store.record_verification_event(
            repo_id=repo_id, commit_sha="d" * 40, kind="test_pass",
            verified_at="2026-06-25T09:00:00+00:00", actor=None, source="warpline",
        )
        events = store.list_verification_events(tmp_path)
        assert [e["commit_sha"] for e in events] == ["d" * 40, "c" * 40]


def test_list_orders_chronologically_across_offsets(tmp_path: Path) -> None:
    # A chronologically-LATER value with a non-UTC offset must NOT sort before an
    # earlier UTC value. 14:00-04:00 == 18:00Z is later than 17:00+00:00.
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(tmp_path)
        store.record_verification_event(
            repo_id=repo_id, commit_sha="e" * 40, kind="test_pass",
            verified_at="2026-06-25T17:00:00+00:00", actor=None, source="warpline",
        )
        store.record_verification_event(
            repo_id=repo_id, commit_sha="f" * 40, kind="test_pass",
            verified_at="2026-06-25T14:00:00-04:00", actor=None, source="warpline",
        )
        events = store.list_verification_events(tmp_path)
        # UTC 17:00 (e) is earlier than UTC 18:00 (f) -> e first.
        assert [ev["commit_sha"] for ev in events] == ["e" * 40, "f" * 40]


def test_list_change_events_for_key_ids_filters(tmp_path: Path) -> None:
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(tmp_path)
        k1 = store.ensure_entity_key(repo_id, "python:function:m.py::f", None, "1" * 40)
        k2 = store.ensure_entity_key(repo_id, "python:function:m.py::g", None, "2" * 40)
        for kid, sha in ((k1, "1" * 40), (k2, "2" * 40)):
            store.append_change_event(
                repo_id=repo_id, entity_key_id=kid, commit_sha=sha, path="m.py",
                change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
            )
        only_k1 = store.list_change_events_for_key_ids(tmp_path, [k1])
        assert {r["entity_key_id"] for r in only_k1} == {k1}
        assert store.list_change_events_for_key_ids(tmp_path, []) == []


def test_list_change_events_for_key_ids_is_oldest_first(tmp_path: Path) -> None:
    # Ordering is load-bearing: compose_verification_freshness treats
    # entity_change_commits[-1] as the LATEST change. A wrong ORDER BY would make
    # the OLDEST change the "latest" and silently report stale-as-fresh.
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(tmp_path)
        k = store.ensure_entity_key(repo_id, "python:function:m.py::f", None, "1" * 40)
        store.append_change_event(
            repo_id=repo_id, entity_key_id=k, commit_sha="1" * 40, path="m.py",
            change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
        )
        store.append_change_event(
            repo_id=repo_id, entity_key_id=k, commit_sha="2" * 40, path="n.py",
            change_kind="modified", actor="dev", changed_at="2026-06-25T20:00:00+00:00",
        )
        rows = store.list_change_events_for_key_ids(tmp_path, [k])
        assert [r["commit_sha"] for r in rows] == ["1" * 40, "2" * 40]  # oldest-first
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_verification_store.py -v`
Expected: FAIL — `HIGHEST_KNOWN_VERSION == 3` (version assert fails) and `record_verification_event` / `list_verification_events` do not exist (`AttributeError`).

- [ ] **Step 3: Add the v4 migration function**

In `src/warpline/store.py`, immediately after `_migrate_v3_co_change_pairs` (ends ~`store.py:194`), add:

```python
def _migrate_v4_verification_events(conn: sqlite3.Connection) -> None:
    """v4 (Rung 2 Track B): verification-freshness events.

    ``verification_events`` records a per-commit gate-pass fact ("gate ``kind``
    passed as-of commit ``commit_sha``"), one row per run — mirroring
    ``change_events``. Freshness is computed at read time by git reachability
    (is a change commit an ancestor-or-equal of a verified commit), never by
    stamping every entity. Warpline OWNS this fact (its own gate result); it
    mirrors no sibling. ``commit_sha`` is always a resolved object SHA, never a
    symbolic ref. The UNIQUE key makes a re-record of the same (repo, commit,
    kind, source) idempotent.
    """

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          repo_id TEXT NOT NULL,
          commit_sha TEXT NOT NULL,
          kind TEXT NOT NULL,
          verified_at TEXT NOT NULL,
          actor TEXT,
          source TEXT NOT NULL DEFAULT 'warpline',
          UNIQUE(repo_id, commit_sha, kind, source)
        )
        """
    )
```

- [ ] **Step 4: Register the migration and bump the presence-floor**

In `src/warpline/store.py`, extend the `MIGRATIONS` list (`store.py:204-207`):

```python
MIGRATIONS: list[Migration] = [
    Migration(version=2, apply=_migrate_v2_anchor_columns),
    Migration(version=3, apply=_migrate_v3_co_change_pairs),
    Migration(version=4, apply=_migrate_v4_verification_events),
]
```

(`HIGHEST_KNOWN_VERSION` at `store.py:213` is computed from this list — it becomes 4 automatically.)

In `_schema_presence_floor` (`store.py:286-321`), after the v3 check block (`if claimed >= 3: ... floor = 3`) and before the final `return claimed`, add:

```python
    # v4 (Rung 2 Track B): the verification_events table.
    if claimed >= 4:
        if not _table_exists(conn, "verification_events"):
            return floor
        floor = 4
```

- [ ] **Step 5: Add the accessors**

In `src/warpline/store.py`, alongside the other `change_events` accessors (after `list_change_events`, ~`store.py:1003`), add two methods to the `WarplineStore` class:

```python
    def record_verification_event(
        self,
        *,
        repo_id: str,
        commit_sha: str,
        kind: str,
        verified_at: str,
        actor: str | None,
        source: str = "warpline",
    ) -> bool:
        """Record one gate-pass fact. Idempotent on (repo, commit, kind, source).

        Returns True if a NEW row was inserted, False if an identical event
        already existed (the ``INSERT OR IGNORE`` was a no-op). This gives the
        verb an O(1), race-free idempotency signal without a second table scan.
        ``commit_sha`` must be a resolved object SHA (the caller resolves the ref).
        """

        cursor = self.conn.execute(
            """
            INSERT OR IGNORE INTO verification_events(
              repo_id, commit_sha, kind, verified_at, actor, source
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (repo_id, commit_sha, kind, verified_at, actor, source),
        )
        inserted = cursor.rowcount > 0
        self.conn.commit()
        return inserted

    def list_verification_events(self, repo: Path) -> list[dict[str, object]]:
        """All verification events for ``repo``, ordered oldest-first by verified_at.

        ``verified_at`` is ISO-8601 written by the verb. We do NOT lexical-sort:
        a caller-supplied ``now`` could carry a non-UTC offset, and a
        chronologically-later ``...-04:00`` value sorts lexically BEFORE a UTC
        ``...+00:00`` one — which would corrupt ``compose_verification_freshness``'s
        most-recent-covering-event identification. So we normalize to the UTC
        instant with ``datetime()`` (mirroring ``list_change_events`` at
        ``store.py:~999``), and COALESCE back to the raw string so a value
        ``datetime()`` cannot parse still sorts deterministically by its lexical
        form rather than vanishing. ``id`` is the final tiebreak.
        """

        repo_id = self._repo_id(repo)
        rows = self.conn.execute(
            """
            SELECT commit_sha, kind, verified_at, actor, source
              FROM verification_events
             WHERE repo_id = ?
             ORDER BY COALESCE(datetime(verified_at), verified_at), id
            """,
            (repo_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_change_events_for_key_ids(
        self, repo: Path, key_ids: list[int]
    ) -> list[dict[str, object]]:
        """Change events filtered to ``key_ids`` (reverify's verification path).

        Pushes the entity filter into SQL (``WHERE ce.entity_key_id IN (...)``)
        so reverify does not full-table-scan every change event in the repo just
        to group commits by the handful of entities in the worklist. Empty
        ``key_ids`` short-circuits to ``[]``. Returns the same row shape as
        ``list_change_events`` (carries ``entity_key_id``, ``commit_sha``,
        ``changed_at``), ordered oldest-first by the normalized ``changed_at``
        instant then ``id`` so callers can take the latest change as the last row.
        """

        if not key_ids:
            return []
        repo_id = self._repo_id(repo)
        placeholders = ",".join("?" for _ in key_ids)
        rows = self.conn.execute(
            f"""
            SELECT ce.commit_sha, ce.changed_at, ce.entity_key_id
              FROM change_events ce
             WHERE ce.repo_id = ?
               AND ce.entity_key_id IN ({placeholders})
             ORDER BY COALESCE(datetime(ce.changed_at), ce.changed_at), ce.id
            """,
            (repo_id, *sorted(set(key_ids))),
        ).fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 6: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_verification_store.py -v`
Expected: PASS (11 tests).

- [ ] **Step 6b: Update the existing migration-version pin (REQUIRED — this hard-fails otherwise)**

`tests/test_store_migrations.py:48` currently reads `assert store_mod.HIGHEST_KNOWN_VERSION == 3`. Bumping the schema to v4 makes it fail. Update the assertion AND every stale-v3 prose/comment site the reviewer located (grep first to confirm current wording — `grep -n "HIGHEST_KNOWN_VERSION\|== 3\|v3\|co_change\|schema_version" tests/test_store_migrations.py`):

```python
# tests/test_store_migrations.py — change the version assertion (was == 3)
    assert store_mod.HIGHEST_KNOWN_VERSION == 4
```

Sites to update (verified by the plan-review reality pass):
- **line 48** — `assert ... == 3` → `== 4` (the hard pin).
- **lines 45-46** — comment "highest known version is 3" → name v4.
- **line 131** — prose "lands at v3" → "lands at v4".
- **lines 166-169** — docstring "meta.schema_version=3" → 4.
- **line 175** — "co_change_pairs (v3)" → mention `verification_events` (v4) as the new highest.

Do NOT touch the DYNAMIC refs (lines 44, 47, 82, 96, 187, 198 — they read `HIGHEST_KNOWN_VERSION`/`MIGRATIONS` programmatically) or the monkeypatch synthetic-migration block (lines 217-288 — it sets `HIGHEST_KNOWN_VERSION` explicitly and is inert to the real bump). After editing, run the whole file and treat ANY remaining comment/assertion mismatch as required to fix, not optional polish. If the file also enumerates an expected-tables set, add `verification_events`.

- [ ] **Step 7: Run the full store-affecting suite + types**

Run: `uv run pytest tests -k "store or migration or schema" -v && uv run mypy src/warpline`
Expected: PASS (including the updated `test_store_migrations.py` pin), no type errors. (Confirms the new migration didn't regress existing schema tests.)

- [ ] **Step 8: Commit**

```bash
git add src/warpline/store.py tests/test_verification_store.py tests/test_store_migrations.py
git commit -m "feat(store): v4 verification_events table + key-id-filtered change accessor"
```

---

## Task 2: git reachability helpers

**Files:**
- Modify: `src/warpline/git.py` (add three helpers)
- Test: `tests/test_git_reachability.py` (create)

**Interfaces:**
- Consumes: existing `_git_optional` pattern in `git.py`.
- Produces (all in `src/warpline/git.py`, module-level functions):
  - `resolve_commit(repo: Path, ref: str) -> str | None` — resolve a ref to a 40-hex object SHA via `git rev-parse --verify <ref>^{commit}`; `None` if unresolvable (never raises).
  - `is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool | None` — `git merge-base --is-ancestor`: `True` (rc 0), `False` (rc 1), `None` for any other rc (bad/missing commit, shallow clone — "could not compute").
  - `commits_between(repo: Path, ancestor: str, descendant: str) -> int | None` — `git rev-list --count ancestor..descendant`; `None` on failure.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_git_reachability.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path

from warpline.git import commits_between, is_ancestor, resolve_commit


def _run(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()


def _repo_with_three_commits(tmp_path: Path) -> tuple[Path, list[str]]:
    repo = tmp_path / "r"
    repo.mkdir()
    _run(repo, "init", "-q")
    _run(repo, "config", "user.email", "t@t")
    _run(repo, "config", "user.name", "t")
    shas: list[str] = []
    for i in range(3):
        (repo / "f.txt").write_text(f"v{i}\n")
        _run(repo, "add", ".")
        _run(repo, "commit", "-q", "-m", f"c{i}")
        shas.append(_run(repo, "rev-parse", "HEAD"))
    return repo, shas


def test_resolve_commit_resolves_head_to_object_sha(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    resolved = resolve_commit(repo, "HEAD")
    assert resolved == shas[2]
    assert len(resolved) == 40


def test_resolve_commit_returns_none_for_bad_ref(tmp_path: Path) -> None:
    repo, _ = _repo_with_three_commits(tmp_path)
    assert resolve_commit(repo, "no-such-ref") is None


def test_is_ancestor_true_for_earlier_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, shas[0], shas[2]) is True


def test_is_ancestor_true_for_equal_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, shas[1], shas[1]) is True


def test_is_ancestor_false_for_later_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, shas[2], shas[0]) is False


def test_is_ancestor_none_for_unknown_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, "f" * 40, shas[0]) is None


def test_commits_between_counts_distance(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert commits_between(repo, shas[0], shas[2]) == 2


def test_commits_between_zero_for_same(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert commits_between(repo, shas[1], shas[1]) == 0


def test_commits_between_none_for_unknown(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert commits_between(repo, "f" * 40, shas[0]) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_git_reachability.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_commit'` (and the others).

- [ ] **Step 3: Implement the helpers**

In `src/warpline/git.py`, add at module level (after the existing `_git_optional`, ~`git.py:82`):

```python
def resolve_commit(repo: Path, ref: str) -> str | None:
    """Resolve ``ref`` to a 40-hex commit object SHA, or None if unresolvable.

    Uses ``rev-parse --verify <ref>^{commit}`` so a tag/branch/``HEAD`` resolves
    to the underlying commit and a non-commit object is rejected. Never raises:
    a bad ref returns None for the caller to turn into a structured error.
    """

    out = _git_optional(repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    if out is None:
        return None
    out = out.strip()
    return out if len(out) == 40 else None


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool | None:
    """Is ``ancestor`` an ancestor-or-equal of ``descendant``?

    Wraps ``git merge-base --is-ancestor``: exit 0 -> True, exit 1 -> False, any
    other exit (unknown/missing commit, shallow clone) -> None ("could not
    compute" — fail-soft, never a crash, never a silent False).
    """

    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def commits_between(repo: Path, ancestor: str, descendant: str) -> int | None:
    """Count commits in ``ancestor..descendant`` (excludes ancestor), or None.

    ``git rev-list --count ancestor..descendant``. None on any git failure
    (unknown commit, etc.). Zero when the two are the same commit.
    """

    proc = subprocess.run(
        ["git", "rev-list", "--count", f"{ancestor}..{descendant}"],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return None
```

(`subprocess` and `Path` are already imported in `git.py`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_git_reachability.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Types check**

Run: `uv run mypy src/warpline/git.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/warpline/git.py tests/test_git_reachability.py
git commit -m "feat(git): is_ancestor / commits_between / resolve_commit reachability helpers"
```

---

## Task 3: pure freshness compute (`verification.py`)

**Files:**
- Create: `src/warpline/verification.py`
- Test: `tests/test_verification_compose.py` (create)

**Interfaces:**
- Consumes: `listing.reason` (`listing.py:34-44`). NO store, NO git, NO I/O — purity is enforced by the import list (mirrors `_enrichment.py`).
- Produces: `compose_verification_freshness(...) -> dict` with this exact contract:

```python
def compose_verification_freshness(
    entity_change_commits: list[str],          # this entity's change commit SHAs, OLDEST-first
    verification_events: list[dict],           # repo verification events, OLDEST-first; each has "commit_sha", "verified_at"
    covers: Callable[[str, str], bool | None], # covers(verified_commit, change_commit): True/False/None(unavailable)
    commits_between: Callable[[str, str], int | None],  # commits_between(ancestor, descendant) for decay
) -> dict:
    # returns:
    # {
    #   "state": "fresh" | "stale" | "unverified" | "unavailable",
    #   "last_verified_at": str | None,
    #   "last_verified_commit": str | None,
    #   "decay": {"commits_behind": int | None},
    #   "reason": <weft-reason triple dict from listing.reason()>,
    # }
```

Semantics (the truth table the tests lock):

| Condition | state |
|-----------|-------|
| `entity_change_commits` empty | `unverified` (nothing to verify) |
| Some event covers the LATEST change commit (`covers(V, latest) is True`) | `fresh` |
| No event covers latest, but `covers(...)` returned `None` for an undetermined check that could otherwise be fresh | `unavailable` |
| No event covers latest, but some event covers an EARLIER change | `stale` |
| Events exist but none cover any change (all `False`) / no events at all | `unverified` |

Reason mapping (reuse canonical 11):
- `fresh` → `reason("clean")`
- `stale` → `reason("stale", cause=..., fix=...)`
- `unverified` → `reason("disabled", cause=..., fix=...)` (no gate pass recorded/covering)
- `unavailable` → `reason("unreachable", cause=..., fix=...)` (git reachability could not be computed)

`last_verified_commit`/`last_verified_at` = the most-recent (by `verified_at`) event that covers some change of this entity (`None` if none). `decay.commits_behind`: `0` for `fresh`; `commits_between(last_covering_commit, latest_change)` for `stale`; `None` for `unverified`/`unavailable`.

- [ ] **Step 1: Write the failing unit tests (vectors-first)**

Create `tests/test_verification_compose.py`:

```python
from __future__ import annotations

from warpline.verification import compose_verification_freshness


def _covers_set(covered_pairs: set[tuple[str, str]]):
    """covers(V, C) True iff (V, C) in the set; default False."""

    def covers(verified: str, change: str) -> bool | None:
        return (verified, change) in covered_pairs

    return covers


def _between_const(value):
    def between(ancestor: str, descendant: str) -> int | None:
        return value

    return between


def test_empty_changes_is_unverified() -> None:
    out = compose_verification_freshness([], [], _covers_set(set()), _between_const(0))
    assert out["state"] == "unverified"
    assert out["reason"]["reason_class"] == "disabled"
    assert out["reason"]["cause"] and out["reason"]["fix"]
    assert out["decay"]["commits_behind"] is None


def test_fresh_when_latest_change_covered() -> None:
    events = [{"commit_sha": "V1", "verified_at": "2026-06-25T10:00:00+00:00"}]
    out = compose_verification_freshness(
        ["C0", "C1"], events, _covers_set({("V1", "C1"), ("V1", "C0")}), _between_const(5)
    )
    assert out["state"] == "fresh"
    assert out["last_verified_commit"] == "V1"
    assert out["last_verified_at"] == "2026-06-25T10:00:00+00:00"
    assert out["decay"]["commits_behind"] == 0
    assert out["reason"]["reason_class"] == "clean"


def test_stale_when_only_earlier_change_covered() -> None:
    events = [{"commit_sha": "V1", "verified_at": "2026-06-25T10:00:00+00:00"}]
    # V1 covers C0 (earlier) but NOT C1 (latest).
    out = compose_verification_freshness(
        ["C0", "C1"], events, _covers_set({("V1", "C0")}), _between_const(2)
    )
    assert out["state"] == "stale"
    assert out["last_verified_commit"] == "V1"
    assert out["decay"]["commits_behind"] == 2
    assert out["reason"]["reason_class"] == "stale"
    assert out["reason"]["cause"] and out["reason"]["fix"]


def test_unverified_when_no_event_covers_any_change() -> None:
    events = [{"commit_sha": "V1", "verified_at": "2026-06-25T10:00:00+00:00"}]
    out = compose_verification_freshness(
        ["C0", "C1"], events, _covers_set(set()), _between_const(0)
    )
    assert out["state"] == "unverified"
    assert out["last_verified_commit"] is None
    assert out["decay"]["commits_behind"] is None
    assert out["reason"]["reason_class"] == "disabled"


def test_unverified_when_no_events_at_all() -> None:
    out = compose_verification_freshness(
        ["C0"], [], _covers_set(set()), _between_const(0)
    )
    assert out["state"] == "unverified"
    assert out["reason"]["reason_class"] == "disabled"


def test_unavailable_when_reachability_undetermined() -> None:
    events = [{"commit_sha": "V1", "verified_at": "2026-06-25T10:00:00+00:00"}]

    def covers(verified: str, change: str) -> bool | None:
        return None  # git could not compute (shallow clone / missing commit)

    out = compose_verification_freshness(["C0", "C1"], events, covers, _between_const(0))
    assert out["state"] == "unavailable"
    assert out["last_verified_commit"] is None
    assert out["decay"]["commits_behind"] is None
    assert out["reason"]["reason_class"] == "unreachable"
    assert out["reason"]["cause"] and out["reason"]["fix"]


def test_most_recent_covering_event_wins_last_verified() -> None:
    events = [
        {"commit_sha": "V1", "verified_at": "2026-06-25T09:00:00+00:00"},
        {"commit_sha": "V2", "verified_at": "2026-06-25T11:00:00+00:00"},
    ]
    # Both cover latest; the later-verified_at one is reported.
    out = compose_verification_freshness(
        ["C1"], events, _covers_set({("V1", "C1"), ("V2", "C1")}), _between_const(0)
    )
    assert out["state"] == "fresh"
    assert out["last_verified_commit"] == "V2"
    assert out["last_verified_at"] == "2026-06-25T11:00:00+00:00"


def test_unavailable_when_latest_undetermined_even_if_earlier_covered() -> None:
    # Fail-soft precedence: if git cannot decide the LATEST change's coverage,
    # the state is 'unavailable' even when an EARLIER change is covered — never
    # 'stale' (which would falsely imply we KNOW it drifted) and never 'fresh'.
    events = [{"commit_sha": "V1", "verified_at": "2026-06-25T10:00:00+00:00"}]

    def covers(verified: str, change: str) -> bool | None:
        if change == "C1":
            return None   # latest change: git cannot decide
        return True       # earlier change C0: covered

    out = compose_verification_freshness(["C0", "C1"], events, covers, _between_const(0))
    assert out["state"] == "unavailable"
    assert out["reason"]["reason_class"] == "unreachable"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_verification_compose.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'warpline.verification'`.

- [ ] **Step 3: Implement `verification.py`**

Create `src/warpline/verification.py`:

```python
"""Pure verification-freshness compute (internal API).

Mirrors ``_enrichment.py``: enrich-only, no store, no git, no I/O — git
reachability is injected as the ``covers`` / ``commits_between`` callables. The
import list (``typing`` + ``warpline.listing.reason``) is the structural proof
that this module cannot gate, mirror a sibling, or perform I/O.

Freshness asks: has the entity's LATEST change been proven good by a recorded
gate run? A gate run at commit ``V`` "covers" a change at commit ``C`` iff ``C``
is an ancestor-or-equal of ``V`` (the gate ran at or after the change landed).
Absence is always EXPLAINED via a weft-reason triple; it never reads as verified.
"""

from __future__ import annotations

from typing import Any, Callable

from warpline.listing import reason


def _latest_covering_event(
    change_commits: list[str],
    events: list[dict[str, Any]],
    covers: Callable[[str, str], bool | None],
) -> tuple[dict[str, Any] | None, bool]:
    """Return (most-recent event covering ANY change, saw_undetermined).

    ``events`` is oldest-first, so the last covering event by iteration is the
    most-recent by ``verified_at``. ``saw_undetermined`` is True if any
    ``covers`` call returned None (git could not decide) — the caller uses it to
    fail-soft to ``unavailable`` rather than claim a clean ``unverified``.
    """

    latest: dict[str, Any] | None = None
    saw_undetermined = False
    for event in events:
        verified_commit = str(event.get("commit_sha"))
        for change_commit in change_commits:
            result = covers(verified_commit, change_commit)
            if result is None:
                saw_undetermined = True
            elif result is True:
                latest = event  # later events overwrite -> most-recent wins
                break
    return latest, saw_undetermined


def compose_verification_freshness(
    entity_change_commits: list[str],
    verification_events: list[dict[str, Any]],
    covers: Callable[[str, str], bool | None],
    commits_between: Callable[[str, str], int | None],
) -> dict[str, Any]:
    """Compose the per-entity verification-freshness block. See module docstring."""

    if not entity_change_commits:
        return _unverified("the entity has no recorded change commits to verify")

    latest_change = entity_change_commits[-1]  # oldest-first input -> latest is last

    # Is the LATEST change covered by any event? (fresh wins outright.)
    latest_saw_undetermined = False
    fresh_event: dict[str, Any] | None = None
    for event in verification_events:
        result = covers(str(event.get("commit_sha")), latest_change)
        if result is None:
            latest_saw_undetermined = True
        elif result is True:
            fresh_event = event  # most-recent covering event wins (oldest-first)

    if fresh_event is not None:
        return {
            "state": "fresh",
            "last_verified_at": fresh_event.get("verified_at"),
            "last_verified_commit": fresh_event.get("commit_sha"),
            "decay": {"commits_behind": 0},
            "reason": reason("clean"),
        }

    # Not fresh. If git could not decide the latest-change coverage, fail soft.
    if latest_saw_undetermined:
        return _unavailable()

    # Latest definitively uncovered (all covers() returned False, no None — else
    # we'd have returned unavailable above). Does any event cover an EARLIER
    # change? Check only [:-1] — the latest is already known uncovered, so
    # re-checking it would waste a covers() call.
    covering_event, earlier_undetermined = _latest_covering_event(
        entity_change_commits[:-1], verification_events, covers
    )
    if covering_event is not None:
        last_commit = str(covering_event.get("commit_sha"))
        return {
            "state": "stale",
            "last_verified_at": covering_event.get("verified_at"),
            "last_verified_commit": covering_event.get("commit_sha"),
            "decay": {"commits_behind": commits_between(last_commit, latest_change)},
            "reason": reason(
                "stale",
                cause=(
                    "the entity changed since it was last proven good: its latest change "
                    "commit is not covered by any recorded verification event"
                ),
                fix=(
                    "re-run your gate (tests/CI) at HEAD and record it with "
                    "`warpline verify-record --commit HEAD --kind test_pass`"
                ),
            ),
        }

    if earlier_undetermined:
        return _unavailable()
    return _unverified(
        "no recorded verification event covers any of the entity's change commits"
    )


def _unverified(cause: str) -> dict[str, Any]:
    return {
        "state": "unverified",
        "last_verified_at": None,
        "last_verified_commit": None,
        "decay": {"commits_behind": None},
        "reason": reason(
            "disabled",
            cause=cause,
            fix=(
                "record a gate pass after your tests/CI run with "
                "`warpline verify-record --commit <sha> --kind test_pass`; until then "
                "verification is honestly unverified, not an earned-clean"
            ),
        ),
    }


def _unavailable() -> dict[str, Any]:
    return {
        "state": "unavailable",
        "last_verified_at": None,
        "last_verified_commit": None,
        "decay": {"commits_behind": None},
        "reason": reason(
            "unreachable",
            cause=(
                "git reachability between the entity's change commits and the recorded "
                "verification commits could not be computed (e.g. shallow clone or a "
                "missing commit object)"
            ),
            fix=(
                "fetch full history (unshallow the clone) so commit ancestry is "
                "resolvable, then re-query; until then freshness is honestly unavailable"
            ),
        ),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_verification_compose.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Types + lint**

Run: `uv run mypy src/warpline/verification.py && uv run ruff check src/warpline/verification.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/warpline/verification.py tests/test_verification_compose.py
git commit -m "feat(verification): pure compose_verification_freshness (fresh/stale/unverified/unavailable)"
```

---

## Task 4: `verify-record` verb (CLI + MCP)

**Files:**
- Modify: `src/warpline/commands.py` (add `SCHEMA_VERIFICATION_RECORD` + `verify_record`)
- Modify: `src/warpline/cli.py` (subparser + dispatch)
- Modify: `src/warpline/mcp.py` (tool spec + handler + consumes)
- Modify: `docs/reference/cli.md`, `docs/reference/mcp-tools.md`
- Test: `tests/test_verify_record.py` (create)

**Interfaces:**
- Consumes: `WarplineStore` accessors from Task 1; `git.resolve_commit` from Task 2; `build_envelope`/`enrichment_state` (`envelope.py`); `errors.WarplineError`; `_utc_now_iso` (see Step 3 — reuse an existing UTC-now helper if one exists; grep first).
- Produces:
  - `commands.SCHEMA_VERIFICATION_RECORD = "warpline.verification_record.v1"`.
  - `commands.verify_record(repo: Path, *, commit: str, kind: str, actor: str | None = None, now: str | None = None) -> dict[str, Any]` — resolves `commit` to an object SHA, validates `kind` non-empty, records the event, returns the standard envelope. `now` is an injectable ISO-8601 timestamp for tests (defaults to current UTC).
  - CLI `warpline verify-record --commit <ref> --kind <kind> [--actor <id>] [--json]`.
  - MCP tool `warpline_verification_record` (shim `verify_record`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_verify_record.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from warpline import commands
from warpline.errors import WarplineError
from warpline.store import WarplineStore, default_store_path


def _git_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "r"
    repo.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    (repo / "f.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "c0"], cwd=repo, check=True, capture_output=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()
    return repo, sha


def test_mcp_module_imports() -> None:
    # mcp.py runs assert_inputschema_consumed() + a strict zip at IMPORT time; a
    # missing consume-declaration or handler crashes here. Keep this first so an
    # import crash is distinguishable from a metadata-assertion failure below.
    from warpline import mcp

    assert mcp.TOOL_SPECS


def test_verify_record_stores_resolved_sha(tmp_path: Path) -> None:
    repo, sha = _git_repo(tmp_path)
    env = commands.verify_record(
        repo, commit="HEAD", kind="test_pass", actor="ci", now="2026-06-25T10:00:00+00:00"
    )
    assert env["ok"] is True
    assert env["schema"] == "warpline.verification_record.v1"
    # The SYMBOLIC ref HEAD must be stored as the resolved 40-hex object SHA.
    assert env["data"]["commit_sha"] == sha
    assert env["data"]["kind"] == "test_pass"
    assert env["data"]["actor"] == "ci"
    assert env["data"]["source"] == "warpline"
    with WarplineStore.open(default_store_path(repo)) as store:
        events = store.list_verification_events(repo)
    assert len(events) == 1
    assert events[0]["commit_sha"] == sha


def test_verify_record_envelope_is_local_only(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    env = commands.verify_record(repo, commit="HEAD", kind="test_pass")
    assert env["meta"]["local_only"] is True
    assert env["meta"]["peer_side_effects"] == []


def test_verify_record_is_idempotent(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    commands.verify_record(repo, commit="HEAD", kind="test_pass", now="2026-06-25T10:00:00+00:00")
    env2 = commands.verify_record(repo, commit="HEAD", kind="test_pass", now="2026-06-25T10:00:00+00:00")
    assert env2["data"]["idempotency"] == "already_recorded"
    with WarplineStore.open(default_store_path(repo)) as store:
        assert len(store.list_verification_events(repo)) == 1


def test_verify_record_idempotent_across_different_timestamps(tmp_path: Path) -> None:
    # verified_at is NOT part of UNIQUE(repo_id, commit_sha, kind, source), so a
    # re-record at a DIFFERENT time must still collapse to a single row.
    repo, _ = _git_repo(tmp_path)
    commands.verify_record(repo, commit="HEAD", kind="test_pass", now="2026-06-25T10:00:00+00:00")
    commands.verify_record(repo, commit="HEAD", kind="test_pass", now="2026-06-25T23:00:00+00:00")
    with WarplineStore.open(default_store_path(repo)) as store:
        assert len(store.list_verification_events(repo)) == 1


def test_verify_record_in_detached_head(tmp_path: Path) -> None:
    # CI commonly runs on a detached HEAD. verify_record(commit="HEAD") must still
    # resolve HEAD to the detached commit's object SHA and store that.
    repo, sha = _git_repo(tmp_path)
    subprocess.run(["git", "checkout", "-q", sha], cwd=repo, check=True, capture_output=True)
    env = commands.verify_record(repo, commit="HEAD", kind="ci_pass", now="2026-06-25T10:00:00+00:00")
    assert env["data"]["commit_sha"] == sha


def test_cli_verify_record_bad_commit_does_not_exit_zero(tmp_path: Path) -> None:
    # Mirror tests/test_cli_dispatch.py's invocation style (read it first). A bad
    # --commit must not return success. If cli.main has a top-level WarplineError
    # handler producing an ok:false envelope + nonzero return, assert that;
    # otherwise assert the non-zero/raised outcome the existing verbs produce.
    from warpline import cli

    repo, _ = _git_repo(tmp_path)
    try:
        rc = cli.main(
            ["verify-record", "--repo", str(repo), "--commit", "no-such-ref",
             "--kind", "test_pass", "--json"]
        )
    except Exception:
        return  # surfaced as an exception (traceback) -> not a success path
    assert rc != 0


def test_verify_record_bad_ref_raises_structured_error(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    with pytest.raises(WarplineError) as exc:
        commands.verify_record(repo, commit="no-such-ref", kind="test_pass")
    data = exc.value.to_error_data()
    assert data["error_code"] == "invalid_rev_range"
    assert data["rejected_field"] == "commit"
    # No row written.
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.list_verification_events(repo) == []


def test_verify_record_empty_kind_raises_structured_error(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    with pytest.raises(WarplineError) as exc:
        commands.verify_record(repo, commit="HEAD", kind="   ")
    data = exc.value.to_error_data()
    assert data["rejected_field"] == "kind"


def test_mcp_lists_verification_record_tool_with_mutating_metadata() -> None:
    from warpline import mcp

    names = {spec["endorsed"] for spec in mcp.TOOL_SPECS}
    assert "warpline_verification_record" in names
    spec = next(s for s in mcp.TOOL_SPECS if s["endorsed"] == "warpline_verification_record")
    meta = spec["metadata"]
    assert meta["read_only"] is False
    assert meta["writes_local_state"] is True
    assert meta["mutates_paths"] == [".weft/warpline/"]
    assert meta["local_only"] is True
    assert meta["peer_side_effects"] == []
    # Both endorsed + shim dispatch to a handler.
    assert "warpline_verification_record" in mcp._HANDLERS
    assert "verify_record" in mcp._HANDLERS
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_verify_record.py -v`
Expected: FAIL — `commands.verify_record` does not exist; `warpline_verification_record` not in `TOOL_SPECS`.

- [ ] **Step 3: Add the schema constant + command**

In `src/warpline/commands.py`, add the schema constant beside the others (`commands.py:44-50`):

```python
SCHEMA_VERIFICATION_RECORD = "warpline.verification_record.v1"
```

Reuse the existing timestamp helper: `_now()` already exists at `commands.py:556` (returns a `datetime`; the module imports `from datetime import UTC, datetime`). Use `_now().isoformat()` — do NOT add a second now-helper.

Add the command (place it near `capture_snapshot`, after `commands.py:1149`). Confirm `build_envelope`, `enrichment_state`, `default_store_path`, and `_now` are available in `commands.py`; add the missing imports (`from warpline.git import resolve_commit`, and `from warpline.errors import BadRevisionError, MissingRequiredFieldError` — check what is already imported and only add what is missing):

```python
def verify_record(
    repo: Path,
    *,
    commit: str,
    kind: str,
    actor: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Record a verification (gate-pass) event for ``commit``.

    The 2nd mutating verb (besides capture-snapshot). Writes ONE row to the
    local ``verification_events`` table (``.weft/warpline/`` only); never a
    sibling repo. ``commit`` is resolved to an object SHA before storage — a
    symbolic ref is never persisted. ``kind`` is a free-form non-empty provenance
    label (e.g. ``test_pass`` / ``ci_pass`` / ``gate_pass``). Idempotent on
    (repo, commit, kind, source=warpline).
    """

    kind_clean = kind.strip()
    if not kind_clean:
        raise MissingRequiredFieldError(
            "kind must be a non-empty verification label, e.g. test_pass",
            rejected_field="kind",
        )
    resolved = resolve_commit(repo, commit)
    if resolved is None:
        raise BadRevisionError(
            f"could not resolve commit ref {commit!r} to an object SHA",
            rejected_field="commit",
        )
    verified_at = now or _now().isoformat()
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        inserted = store.record_verification_event(
            repo_id=repo_id,
            commit_sha=resolved,
            kind=kind_clean,
            verified_at=verified_at,
            actor=actor,
            source="warpline",
        )
    data = {
        "commit_sha": resolved,
        "kind": kind_clean,
        "verified_at": verified_at,
        "actor": actor,
        "source": "warpline",
        "idempotency": "recorded" if inserted else "already_recorded",
    }
    query = {
        "repo": str(repo),
        "tool": "warpline_verification_record",
        "arguments": {"commit": commit, "kind": kind, "actor": actor},
        "filters": {},
        "sort": {},
        "page": {"limit": None, "cursor": None},
    }
    return build_envelope(
        SCHEMA_VERIFICATION_RECORD,
        query=query,
        data=data,
        enrichment=enrichment_state(),
        warnings=[],
    )
```

> Error-class rationale (verified against `errors.py`): `MissingRequiredFieldError` (`errors.py:70-73`, `code="missing_required_field"`, `retryability="retry_with_changes"`) is the semantically correct error for a blank `kind` — do NOT use `InvalidChangedRefsError` (its `code="invalid_changed_refs"` would misleadingly point a caller at the `changed_refs` input). `BadRevisionError` (`errors.py:83-87`, `code="invalid_rev_range"`) is correct for an unresolvable commit ref; its default `rejected_field` is `"rev_range"`, and passing `rejected_field="commit"` overrides it (the `WarplineError.__init__` honors the kwarg — `errors.py:26-67`).

- [ ] **Step 4: Wire the CLI**

In `src/warpline/cli.py`, add the subparser beside `capture-snapshot` (`cli.py:334-339`):

```python
    verify_record_parser = sub.add_parser("verify-record")
    verify_record_parser.add_argument("--repo", type=Path, default=Path("."))
    verify_record_parser.add_argument("--commit", required=True)
    verify_record_parser.add_argument("--kind", required=True)
    verify_record_parser.add_argument("--actor")
    verify_record_parser.add_argument("--json", action="store_true")
```

And the dispatch beside `capture-snapshot`'s (`cli.py:525-532`):

```python
    if args.command == "verify-record":
        payload = commands.verify_record(
            args.repo,
            commit=args.commit,
            kind=args.kind,
            actor=args.actor,
        )
        print(
            json.dumps(payload, sort_keys=True)
            if args.json
            else json.dumps(payload, indent=2)
        )
        return 0
```

> If `cli.py` wraps command calls to convert `WarplineError` into a printed error envelope + nonzero exit (check how `capture-snapshot`/`changed` handle errors — grep `WarplineError` in `cli.py`), follow that same pattern so a bad `--commit` exits cleanly rather than tracebacks.

- [ ] **Step 5: Wire the MCP tool**

In `src/warpline/mcp.py`, add the handler beside `_h_capture` (`mcp.py:423-433`):

```python
def _h_verify_record(args: dict[str, Any]) -> dict[str, Any]:
    return commands.verify_record(
        _repo_arg(args),
        commit=str(args.get("commit", "")),
        kind=str(args.get("kind", "")),
        actor=_opt_str(args, "actor"),
    )
```

> Check `_opt_str` exists in `mcp.py` (the capture handler uses helpers for optional args). If not, inline: `actor=(str(args["actor"]) if args.get("actor") is not None else None)`.

Add the tool spec to `TOOL_SPECS` after the `warpline_edge_snapshot_capture` spec (`mcp.py:217-242`):

```python
    _tool_spec(
        endorsed="warpline_verification_record",
        shim="verify_record",
        schema=commands.SCHEMA_VERIFICATION_RECORD,
        description=(
            "Record a verification (gate-pass) for a commit, e.g. test_pass. Mutates ONLY "
            ".weft/warpline state; never a sibling repo. Advisory; warpline never gates."
        ),
        input_properties={
            "commit": {"type": "string"},
            "kind": {"type": "string"},
            "actor": {"type": ["string", "null"]},
        },
        required=["repo", "commit", "kind"],
        metadata=_metadata(
            read_only=False,
            writes_local_state=True,
            idempotent=True,
            mutates_paths=[".weft/warpline/"],
            federation_dependencies=[],
        ),
    ),
```

Add `_h_verify_record` to the `_HANDLERS` zip handler list (`mcp.py:436-443`) — append it AFTER `_h_capture` so the indexed order matches `TOOL_SPECS`:

```python
for _spec, _handler in zip(
    TOOL_SPECS,
    [_h_change_list, _h_timeline, _h_churn, _h_impact, _h_reverify, _h_capture, _h_verify_record],
    strict=True,
):
```

**REQUIRED (not conditional) — the consume declarations.** `mcp.py` runs `assert_inputschema_consumed()` at **import time** (the assert is at `mcp.py:574`); it crashes the whole MCP module — making *every* warpline tool uncallable and failing `mcp-smoke`/`dogfood` — if the new tool is missing from BOTH maps. Add both:

To `_HANDLER_CONSUMES` (`mcp.py:510-521`) — all four advertised fields are consumed by `_h_verify_record`:

```python
    "warpline_verification_record": frozenset({"repo", "commit", "kind", "actor"}),
```

To `_KNOWN_FASTFOLLOW_DEAD` (the companion map near `mcp.py:531`) — no advertised-but-unconsumed fields, so an empty set:

```python
    "warpline_verification_record": frozenset(),
```

Grep to confirm both map names and the assert: `grep -n "_HANDLER_CONSUMES\|_KNOWN_FASTFOLLOW_DEAD\|assert_inputschema_consumed" src/warpline/mcp.py`. Both endorsed-name keys are required; the shim (`verify_record`) is handled by the existing consume logic — match how `warpline_edge_snapshot_capture` is keyed (endorsed name only) and mirror it exactly.

- [ ] **Step 5b: Fix the contract-fixture mutating-tool assertion + regenerate the static inventory (REQUIRED)**

A second mutating tool breaks two existing contract checks. Grep first: `grep -rn "is_capture\|mutates\|mcp-tool-inventory" tests/contracts/ tests/fixtures/contracts/`.

1. `tests/contracts/test_warpline_contract_fixtures.py:54-55` reads:
   ```python
   is_capture = tool["name"] in {"capture_snapshot", "warpline_edge_snapshot_capture"}
   assert tool["mutates"] is is_capture
   ```
   This asserts the capture tool is the ONLY mutating tool. Generalize it (rename `is_capture` → `is_mutating`) to include the new tool:
   ```python
   is_mutating = tool["name"] in {
       "capture_snapshot", "warpline_edge_snapshot_capture",
       "verify_record", "warpline_verification_record",
   }
   assert tool["mutates"] is is_mutating
   ```
2. `tests/fixtures/contracts/warpline/mcp-tool-inventory.json` is a STATIC snapshot of `tools/list`. It must be regenerated so the two new tool names appear with `mutates: true` and the correct metadata. Find how it is generated (grep for a regenerate script or a `--update`/`--regen` flag, or a test that writes it): `grep -rn "mcp-tool-inventory\|inventory" tests/ scripts/ src/warpline/`. If a regenerate command exists, run it; otherwise hand-add the two tool entries mirroring the `warpline_edge_snapshot_capture` entry's shape (name, inputSchema, full metadata block) for both `warpline_verification_record` and its `verify_record` shim. Then run `uv run pytest tests/contracts/test_warpline_contract_fixtures.py -v` and confirm green.

> Note: there is a pre-existing open follow-up `warpline-fc09bdeddd` about contract-fixture drift (a missing `enrichment_reasons` key in fixtures). That is SEPARATE from this step (different fixture concern) — do not conflate; just make THIS tool's inventory entries correct.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_verify_record.py tests/contracts/test_warpline_contract_fixtures.py -v`
Expected: PASS (8 verb tests + the contract fixtures).

- [ ] **Step 7: MCP smoke + types**

Run: `uv run warpline mcp-smoke --repo . --json && uv run mypy src/warpline`
Expected: `mcp-smoke` reports `ok: true`; mypy clean.

- [ ] **Step 8: Document the verb**

In `docs/reference/cli.md`, add a `verify-record` entry mirroring the `capture-snapshot` entry's format (flags `--commit` (required), `--kind` (required), `--actor`, `--json`; one-line description: "Record a local gate-pass verification event for a commit (advisory; warpline never gates)."). In `docs/reference/mcp-tools.md`, add `warpline_verification_record` (shim `verify_record`) to the tool table/list with its inputs and the mutating/`local_only` metadata, mirroring the `warpline_edge_snapshot_capture` row.

- [ ] **Step 9: Commit**

```bash
git add src/warpline/commands.py src/warpline/cli.py src/warpline/mcp.py \
  src/warpline/errors.py docs/reference/cli.md docs/reference/mcp-tools.md \
  tests/test_verify_record.py tests/contracts/test_warpline_contract_fixtures.py \
  tests/fixtures/contracts/warpline/mcp-tool-inventory.json
git commit -m "feat: verify-record verb (CLI + MCP, 2nd mutating tool)"
```
(Include `errors.py` only if you added/adjusted an error subclass; include the contract-fixture + inventory files from Step 5b.)

---

## Task 5: reverify integration (per-item block, summary, advisory sort)

**Files:**
- Modify: `src/warpline/reverify.py` (thread a per-item `verification` block)
- Modify: `src/warpline/commands.py` (`reverify_worklist`: build verification index, attach, summary, advisory sort)
- Test: `tests/test_reverify_verification.py` (create)

**Interfaces:**
- Consumes: `verification.compose_verification_freshness` (Task 3); `git.is_ancestor`/`git.commits_between` (Task 2); `store.list_verification_events`/`store.list_change_events` (Task 1 + existing); the existing `reverify_worklist` pipeline (`commands.py:745-876`).
- Produces:
  - Each worklist item gains `item["verification"]` (the dict from `compose_verification_freshness`).
  - `data["verification_summary"] = {"fresh": int, "stale": int, "unverified": int, "unavailable": int, "local_source_configured": bool}`.
  - Advisory sort: stale-of-trust surfaces first WITHIN the existing depth ordering; **no item removed**.

**Design (data flow — read carefully):**
`enrich_blast` returns `changed`/`affected` whose `entity` view is `{locator, sei}` only (`entity_key_id` is dropped — `refs.py:entity_view` keeps the frozen view). But the upstream `result` from `compute_blast_radius` still carries `entity_key_id` per row, and `enrich_blast` preserves order. So: in `commands.py`, build aligned `entity_key_id` lists from `result["changed"]`/`result["affected"]`, compute a `verification` block per key id, and pass a `verification_for: Callable[[int | None], dict]` plus the aligned id lists into `render_reverify_worklist`, which attaches `item["verification"]` per row. This keeps the frozen entity view untouched and avoids fragile positional zips after sorting.

- [ ] **Step 1: Write the failing integration tests**

Create `tests/test_reverify_verification.py`. (Reuse the seeding style from `tests/contracts/test_golden_vectors.py`; this test drives the public `commands.reverify_worklist`.)

```python
from __future__ import annotations

import subprocess
from pathlib import Path

from warpline import commands
from warpline.store import WarplineStore, default_store_path


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    return repo


def _commit(repo: Path, name: str, body: str) -> str:
    (repo / name).write_text(body)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", f"touch {name}")
    return _git(repo, "rev-parse", "HEAD")


def _seed_entity_change(store: WarplineStore, repo: Path, locator: str, commit_sha: str) -> int:
    repo_id = store.ensure_repo(repo)
    key_id = store.ensure_entity_key(repo_id, locator, None, commit_sha)
    store.append_change_event(
        repo_id=repo_id,
        entity_key_id=key_id,
        commit_sha=commit_sha,
        path="m.py",
        change_kind="modified",
        actor="dev",
        changed_at="2026-06-25T08:00:00+00:00",
    )
    return key_id


def test_each_item_carries_a_verification_block(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    env = commands.reverify_worklist(repo, [key_id])
    items = env["data"]["items"]
    assert items, "expected a non-empty worklist"
    for item in items:
        assert "verification" in item
        assert item["verification"]["state"] in {"fresh", "stale", "unverified", "unavailable"}
        assert "reason_class" in item["verification"]["reason"]


def test_unverified_when_no_verification_recorded(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    env = commands.reverify_worklist(repo, [key_id])
    summary = env["data"]["verification_summary"]
    assert summary["local_source_configured"] is False
    assert summary["unverified"] >= 1
    item = env["data"]["items"][0]
    assert item["verification"]["state"] == "unverified"
    assert item["verification"]["reason"]["reason_class"] == "disabled"


def test_fresh_when_change_is_verified(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    commands.verify_record(repo, commit=c0, kind="test_pass", now="2026-06-25T10:00:00+00:00")
    env = commands.reverify_worklist(repo, [key_id])
    summary = env["data"]["verification_summary"]
    assert summary["local_source_configured"] is True
    assert summary["fresh"] >= 1
    item = next(i for i in env["data"]["items"] if i["reason"] == "changed")
    assert item["verification"]["state"] == "fresh"
    assert item["verification"]["last_verified_commit"] == c0


def test_stale_when_change_lands_after_verification(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    # Verify at c0, THEN the entity changes again at c1 (uncovered).
    commands.verify_record(repo, commit=c0, kind="test_pass", now="2026-06-25T10:00:00+00:00")
    c1 = _commit(repo, "m.py", "v1\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        key_id = store.ensure_entity_key(repo_id, "python:function:m.py::f", None, c0)
        for sha in (c0, c1):
            store.append_change_event(
                repo_id=repo_id, entity_key_id=key_id, commit_sha=sha, path="m.py",
                change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
            )
    env = commands.reverify_worklist(repo, [key_id])
    item = next(i for i in env["data"]["items"] if i["reason"] == "changed")
    assert item["verification"]["state"] == "stale"
    assert env["data"]["verification_summary"]["stale"] >= 1


def test_verification_never_filters_items(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    baseline = commands.reverify_worklist(repo, [key_id])
    n_before = len(baseline["data"]["items"])
    # Recording verification must never REMOVE an item — only annotate/sort.
    commands.verify_record(repo, commit=c0, kind="test_pass")
    after = commands.reverify_worklist(repo, [key_id])
    assert len(after["data"]["items"]) == n_before


def test_envelope_stays_local_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    env = commands.reverify_worklist(repo, [key_id])
    assert env["meta"]["local_only"] is True
    assert env["meta"]["peer_side_effects"] == []
    # verification must NOT have leaked into the frozen enrichment vocab.
    assert "verification" not in env["enrichment"]
    assert "verification" not in env["enrichment_reasons"]


def test_verification_summary_is_post_filter_zero_case(tmp_path: Path) -> None:
    # Our entity has sei=None; filtering has_sei -> empty set -> all-zero summary.
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    env = commands.reverify_worklist(repo, [key_id], filters={"has_sei": True})
    assert env["data"]["items"] == []
    summary = env["data"]["verification_summary"]
    assert summary["fresh"] == 0
    assert summary["stale"] == 0
    assert summary["unverified"] == 0
    assert summary["unavailable"] == 0


def test_verification_summary_counts_only_filtered_subset(tmp_path: Path) -> None:
    # Two entities; one HAS an sei, one does not. Filtering has_sei=True keeps
    # exactly ONE. The summary must count 1, not 2 — proving it is computed on the
    # POST-filter set (a pre-filter computation would report 2).
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        with_sei = store.ensure_entity_key(repo_id, "python:function:m.py::f", "lw:eid:has", c0)
        without_sei = store.ensure_entity_key(repo_id, "python:function:m.py::g", None, c0)
        for kid in (with_sei, without_sei):
            store.append_change_event(
                repo_id=repo_id, entity_key_id=kid, commit_sha=c0, path="m.py",
                change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
            )
    env = commands.reverify_worklist(repo, [with_sei, without_sei], filters={"has_sei": True})
    assert len(env["data"]["items"]) == 1
    summary = env["data"]["verification_summary"]
    total = summary["fresh"] + summary["stale"] + summary["unverified"] + summary["unavailable"]
    assert total == 1  # NOT 2 — proves post-filter computation


def test_unavailable_when_reachability_fails(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    # A verification event must exist so covers() is actually consulted.
    commands.verify_record(repo, commit=c0, kind="test_pass", now="2026-06-25T10:00:00+00:00")
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    # Patch the name in commands' namespace (it imported is_ancestor by name).
    monkeypatch.setattr(commands, "is_ancestor", lambda *a, **k: None)
    env = commands.reverify_worklist(repo, [key_id])
    item = next(i for i in env["data"]["items"] if i["reason"] == "changed")
    assert item["verification"]["state"] == "unavailable"
    assert item["verification"]["reason"]["reason_class"] == "unreachable"
    assert env["data"]["verification_summary"]["unavailable"] >= 1


def test_stale_sorts_before_fresh_by_default(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    c0 = _commit(repo, "a.py", "v0\n")
    commands.verify_record(repo, commit=c0, kind="test_pass", now="2026-06-25T10:00:00+00:00")
    c1 = _commit(repo, "b.py", "v1\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(repo_id, "python:function:a.py::fa", None, c0)
        store.append_change_event(
            repo_id=repo_id, entity_key_id=a, commit_sha=c0, path="a.py",
            change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
        )
        b = store.ensure_entity_key(repo_id, "python:function:b.py::fb", None, c0)
        for sha in (c0, c1):
            store.append_change_event(
                repo_id=repo_id, entity_key_id=b, commit_sha=sha, path="b.py",
                change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
            )
    # Seed FRESH first so the natural (pre-presort) order is fresh-then-stale;
    # the presort must flip it. (Catches presort removal: without it the order
    # stays fresh-first and this assertion fails.)
    env = commands.reverify_worklist(repo, [a, b])
    states = [i["verification"]["state"] for i in env["data"]["items"]]
    assert "stale" in states and "fresh" in states
    assert states.index("stale") < states.index("fresh")  # advisory: stale first


def test_fresh_when_verified_at_a_later_commit(tmp_path: Path) -> None:
    # Asymmetric real-git case that catches a covers/is_ancestor argument SWAP:
    # change at c0, verify at c1 (c1 is a DESCENDANT of c0). c0 is an ancestor of
    # c1, so the change IS covered -> fresh. A swapped is_ancestor(verified, change)
    # would compute is_ancestor(c1, c0) -> False and wrongly report not-fresh.
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    c1 = _commit(repo, "n.py", "v0\n")  # later commit, descendant of c0
    with WarplineStore.open(default_store_path(repo)) as store:
        key_id = _seed_entity_change(store, repo, "python:function:m.py::f", c0)
    commands.verify_record(repo, commit=c1, kind="test_pass", now="2026-06-25T10:00:00+00:00")
    env = commands.reverify_worklist(repo, [key_id])
    item = next(i for i in env["data"]["items"] if i["reason"] == "changed")
    assert item["verification"]["state"] == "fresh"
    assert item["verification"]["last_verified_commit"] == c1


def test_unavailable_when_change_commit_no_longer_exists(tmp_path: Path) -> None:
    # Squash/rebase honesty: a change_event whose commit SHA was rewritten away
    # (no longer a real object). With a recorded verification, git reachability
    # cannot be computed -> 'unavailable'/'unreachable', NOT a silent 'unverified'
    # (which would falsely imply "just needs verifying" instead of "trust unknown").
    repo = _repo(tmp_path)
    c0 = _commit(repo, "m.py", "v0\n")
    commands.verify_record(repo, commit=c0, kind="test_pass", now="2026-06-25T10:00:00+00:00")
    ghost = "0" * 40  # a SHA that never existed (rewritten by squash/rebase)
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        key_id = store.ensure_entity_key(repo_id, "python:function:m.py::f", None, ghost)
        store.append_change_event(
            repo_id=repo_id, entity_key_id=key_id, commit_sha=ghost, path="m.py",
            change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
        )
    env = commands.reverify_worklist(repo, [key_id])
    item = next(i for i in env["data"]["items"] if i["reason"] == "changed")
    assert item["verification"]["state"] == "unavailable"
    assert item["verification"]["reason"]["reason_class"] == "unreachable"
```

> Before implementing, the engineer MUST verify the seeding helpers used here match real store signatures: `ensure_entity_key(repo_id, locator, sei, commit_sha) -> int` (`store.py:521`), `append_change_event(*, repo_id, entity_key_id, commit_sha, path, change_kind, actor, changed_at, ...)` (`store.py:881`). Adjust the test seeding if a signature differs.

**ALSO write `test_stale_first_is_secondary_to_an_explicit_sort`** (prose, because it needs an edge snapshot to produce a depth≥1 item — do not hand-guess the edge direction). It proves stale-first is a SECONDARY tiebreak, not a primary override. Construct it by **mirroring an existing test that produces downstream/affected items** (grep: `grep -rln "capture_snapshot_atomic\|\"depth\": 1\|depth=1\|downstream" tests/`) — copy that test's exact edge-snapshot setup. Make the changed entity X **fresh** (verify at its change commit) and its downstream entity Y at depth 1 **stale** (Y changes again after the last covering verification). Then with the default sort assert: (a) `[it["depth"] for it in env["data"]["items"]] == sorted(...)` — depth stays the PRIMARY ordering; (b) the depth-0 fresh item precedes the depth-1 stale item — stale-first did NOT override the primary key; (c) where two items share a depth, the stale one precedes the fresh one. If a swapped placement (presort after `apply_sort`) were used, (a)/(b) would fail. This is the test that makes the placement fix non-vacuous.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_reverify_verification.py -v`
Expected: FAIL — items have no `verification` key; `data` has no `verification_summary`. (Note: `test_unavailable_when_reachability_fails` red-states as `AttributeError: module 'warpline.commands' has no attribute 'is_ancestor'` until Step 4 adds the `from warpline.git import is_ancestor, commits_between` import — that import form is REQUIRED for `monkeypatch.setattr(commands, "is_ancestor", ...)` to bind. Guard any `next(... for ... if ...)` in these tests with a preceding `assert any(...)` so a truncated worklist fails with a clear message, not `StopIteration`.)

- [ ] **Step 3: Thread the per-item block through `render_reverify_worklist`**

In `src/warpline/reverify.py`, change `render_reverify_worklist` to accept aligned key-id lists and a `verification_for` callable, and attach the block. Replace the signature and the row-building / item-building sections (`reverify.py:19-79`):

```python
def render_reverify_worklist(
    *,
    changed: list[dict[str, Any]],
    affected: list[dict[str, Any]],
    completeness: str,
    staleness: dict[str, Any],
    work_client: WorkClient | None = None,
    changed_key_ids: list[int | None] | None = None,
    affected_key_ids: list[int | None] | None = None,
    verification_for: Callable[[int | None], dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]]]:
    """Render the frozen reverify worklist items.

    Returns ``(items, work_seen, filigree_candidates)``. The changed entities are
    always present (reason ``changed``) so a solo/NO_SNAPSHOT worklist is still
    non-empty; downstream entities are added when a snapshot exists.

    ``verification_for`` (advisory, Rung 2 Track B) maps an ``entity_key_id`` to
    its verification-freshness block; ``changed_key_ids`` / ``affected_key_ids``
    are aligned 1:1 with ``changed`` / ``affected`` so the block can be attached
    without threading the internal key id into the FROZEN ``{locator, sei}``
    entity view. When ``verification_for`` is None the block defaults to an
    honest ``unverified`` (no source configured).
    """

    ckids = changed_key_ids or [None] * len(changed)
    akids = affected_key_ids or [None] * len(affected)
    rows: list[tuple[dict[str, Any], str, int, list[Any], int | None]] = []
    for entry, kid in zip(changed, ckids):
        rows.append((entry.get("entity", {}), "changed", 0, [], kid))
    for entry, kid in zip(affected, akids):
        rows.append(
            (
                entry.get("entity", {}),
                "downstream",
                entry.get("depth", 1),
                entry.get("via_edges", []),
                kid,
            )
        )

    items: list[dict[str, Any]] = []
    work_seen = False
    candidates: list[dict[str, Any]] = []
    for entity, reason, depth, why, kid in rows:
        enrichment = _empty_enrichment()
        priority = "unknown"
        sei = entity.get("sei")
        if work_client is not None and isinstance(sei, str) and sei:
            work_items = work_enrichment_for_sei(work_client, sei)
            if work_items:
                work_seen = True
                enrichment["work"] = work_items
                priority = priority_from_work(work_items)
                for work_item in work_items:
                    candidates.append(
                        {
                            "proposed_action": "review_linked_issue",
                            "issue_id": work_item.get("issue_id"),
                            "entity": entity,
                        }
                    )
        verification = (
            verification_for(kid) if verification_for is not None else _default_verification()
        )
        items.append(
            {
                "entity": entity,
                "priority": priority,
                "reason": reason,
                "depth": depth,
                "why": why,
                "suggested_verification": _SUGGESTED_VERIFICATION,
                "enrichment": enrichment,
                "verification": verification,
            }
        )
    return items, work_seen, candidates
```

Add the imports + the default helper at the top of `reverify.py`:

```python
from typing import Any, Callable

from warpline.listing import reason
```

```python
def _default_verification() -> dict[str, Any]:
    """Honest default when no verification source is wired (advisory)."""

    return {
        "state": "unverified",
        "last_verified_at": None,
        "last_verified_commit": None,
        "decay": {"commits_behind": None},
        "reason": reason(
            "disabled",
            cause="no local verification source is configured for this worklist",
            fix=(
                "record a gate pass with `warpline verify-record --commit <sha> "
                "--kind test_pass`"
            ),
        ),
    }
```

Also add a one-line comment to `enrich_blast` (`_blast.py:142-157`) recording the order-preservation invariant the alignment relies on: `# Order-preserving: changed[i]/affected[i] map 1:1 to result["changed"][i]/["affected"][i]; reverify's verification key-id alignment depends on this.`

- [ ] **Step 4: Build the verification index + summary + advisory sort in `reverify_worklist`**

In `src/warpline/commands.py`, inside `reverify_worklist` (`commands.py:745-876`): after `changed, affected = enrich_blast(store, repo, result)` (line ~777) and before `render_reverify_worklist`, add the index construction. Then pass it into render, attach the summary, and add the advisory presort.

Add the import at the top of `commands.py`: `from warpline.verification import compose_verification_freshness` and `from warpline.git import is_ancestor, commits_between`.

Insert before the `render_reverify_worklist(...)` call:

```python
        # Rung 2 Track B — verification freshness (advisory, never gates).
        # Align entity_key_id to changed/affected ORDER. enrich_blast preserves
        # the order of result["changed"]/result["affected"] (verified _blast.py:142-157),
        # whose rows carry entity_key_id; the FROZEN {locator, sei} entity view never
        # does. The positional alignment changed[i] <-> changed_key_ids[i] is the
        # invariant render_reverify_worklist relies on to attach the block.
        changed_key_ids: list[int | None] = [
            r.get("entity_key_id") if isinstance(r.get("entity_key_id"), int) else None
            for r in result.get("changed", [])
        ]
        affected_key_ids: list[int | None] = [
            r.get("entity_key_id") if isinstance(r.get("entity_key_id"), int) else None
            for r in result.get("affected", [])
        ]
        # Load ONLY the worklist's change commits (no full-table scan — push the
        # entity filter into SQL) and group by key id; load verification events once.
        worklist_key_ids = [k for k in (*changed_key_ids, *affected_key_ids) if k is not None]
        verification_events = store.list_verification_events(repo)
        local_source_configured = len(verification_events) > 0
        changes_by_key: dict[int, list[str]] = {}
        for ce in store.list_change_events_for_key_ids(repo, worklist_key_ids):
            kid = ce.get("entity_key_id")
            if isinstance(kid, int):
                sha = str(ce.get("commit_sha"))
                bucket = changes_by_key.setdefault(kid, [])
                # One entity can have several change_event rows for the SAME commit
                # (the UNIQUE key is (repo, entity_key_id, commit_sha, path, change_kind),
                # not commit_sha alone). Collapse adjacent duplicates (rows are
                # oldest-first) so the covers() fan-out isn't wasted and
                # entity_change_commits[-1] stays the true latest distinct commit.
                if not bucket or bucket[-1] != sha:
                    bucket.append(sha)

        def _covers(verified_commit: str, change_commit: str) -> bool | None:
            # NOTE the argument inversion: a change is COVERED by a verification
            # iff the change commit is an ancestor-or-equal of the verified commit
            # (the gate ran at/after the change). So covers(verified, change) maps
            # to is_ancestor(ancestor=change_commit, descendant=verified_commit).
            return is_ancestor(repo, change_commit, verified_commit)

        def _between(ancestor: str, descendant: str) -> int | None:
            return commits_between(repo, ancestor, descendant)

        _verif_cache: dict[int, dict[str, Any]] = {}

        def verification_for(kid: int | None) -> dict[str, Any]:
            # kid is None for an affected row that carried no entity_key_id;
            # compose([], ...) honestly yields "unverified" (nothing to verify).
            if kid is None:
                return compose_verification_freshness([], verification_events, _covers, _between)
            if kid not in _verif_cache:
                _verif_cache[kid] = compose_verification_freshness(
                    changes_by_key.get(kid, []),
                    verification_events,
                    _covers,
                    _between,
                )
            return _verif_cache[kid]
```

Change the `render_reverify_worklist(...)` call (currently `commands.py:780-786`) to pass the new kwargs:

```python
        items, work_seen, filigree_candidates = render_reverify_worklist(
            changed=changed,
            affected=affected,
            completeness=completeness,
            staleness=staleness,
            work_client=work_client,
            changed_key_ids=changed_key_ids,
            affected_key_ids=affected_key_ids,
            verification_for=verification_for,
        )
```

The render call attaches `item["verification"]` to every item but does NOT reorder them. The advisory stale-first presort goes **between the existing `apply_filters` (`commands.py:787`) and `apply_sort` (`commands.py:788`) calls** — NOT right after render. Pipeline order must be: `render` (780) → `apply_filters` (787) → **`[stale-first presort]`** → `apply_sort` (788) → **`[verification_summary]`** → `apply_group_by` → `apply_overflow` (820) → `apply_page` (823).

Why exactly there (verified: `apply_sort` is Python's stable `sorted()` at `listing.py:332`, with a `sort_by=None` passthrough at `listing.py:306`): the LAST stable sort applied is the PRIMARY key. So the presort must run immediately *before* `apply_sort` — then `apply_sort` is primary and stale-first survives only as the secondary tiebreak within equal primary-key groups (and, when `sort_by` is None, the passthrough leaves the presort order intact). Placing it before `apply_filters` would (a) waste work sorting items filters then drop and (b) be a no-op once `apply_sort` re-sorts. Insert between the two existing statements:

```python
        items = apply_filters(items, tool="warpline_reverify_worklist_get", filters=filters)
        # Advisory: stale-of-trust first. Stable presort run JUST BEFORE apply_sort
        # so apply_sort stays the PRIMARY key (last stable sort wins) and stale-first
        # is the secondary tiebreak within ties. Never reorders across the primary
        # key; never removes an item. Relies on apply_sort being a stable sorted()
        # (listing.py:332) with a sort_by=None passthrough (listing.py:306).
        _state_rank = {"stale": 0, "unavailable": 1, "unverified": 2, "fresh": 3}
        items.sort(key=lambda it: _state_rank.get(it["verification"]["state"], 3))
        items = apply_sort(items, tool="warpline_reverify_worklist_get", sort_by=sort_by, sort_order=sort_order)
```

(The `apply_filters`/`apply_sort` lines above are the EXISTING `commands.py:787-788` statements shown for context — insert only the three presort lines between them; match the real call signatures already in the file.)

Then compute `verification_summary` from the **post-filter, post-sort, pre-page** item set (so a caller who filtered to one `path_prefix` gets counts for *their* scope, not the whole blast radius). Insert it **after `apply_sort` (788) and before `apply_overflow` (820)**, holding it in a variable for the `data` dict (built later, after paging):

```python
        # verification_summary reflects the post-filter, pre-page set (mirrors how
        # completeness/staleness describe the requested set, not the current page).
        verification_summary = {
            "fresh": sum(1 for it in items if it["verification"]["state"] == "fresh"),
            "stale": sum(1 for it in items if it["verification"]["state"] == "stale"),
            "unverified": sum(1 for it in items if it["verification"]["state"] == "unverified"),
            "unavailable": sum(1 for it in items if it["verification"]["state"] == "unavailable"),
            "local_source_configured": local_source_configured,
        }
```

Then add `verification_summary` to the `data = { ... }` dict (~`commands.py:824-834`), right after `"staleness": staleness,`:

```python
        data = {
            "completeness": completeness,
            "staleness": staleness,
            "verification_summary": verification_summary,
            "resolved": resolved,
            # ... rest unchanged ...
        }
```

> Why post-filter/pre-page (not pre-filter): `apply_filters` for this tool supports `path_prefix`/`priority`/`reason`/`has_sei`, all of which DROP items. Computing the summary before filters would report whole-repo counts even when the caller scoped to one path — a silent miscount. Computing it pre-page (before `apply_overflow`/`apply_page`) keeps it describing the full requested set rather than one page, consistent with `completeness`/`staleness`. The never-filter invariant is about *verification never removing an item*; caller filters are a separate, legitimate scoping the summary must honor.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_reverify_verification.py -v`
Expected: PASS (13 tests, incl. the mirrored mixed-depth secondary-sort test).

- [ ] **Step 6: Run the full reverify + envelope suite**

Run: `uv run pytest tests -k "reverify or envelope or render or worklist" -v && uv run mypy src/warpline`
Expected: PASS, mypy clean. (Catches any existing reverify test that asserts an exact item-dict shape and now needs the `verification` key — if a frozen-shape test breaks, that is a CONTRACT decision: the reverify worklist ITEM schema is additive here, so update that test to allow the new key; do NOT touch the frozen ENVELOPE `enrichment` vocab.)

- [ ] **Step 7: Commit**

```bash
git add src/warpline/reverify.py src/warpline/commands.py tests/test_reverify_verification.py
git commit -m "feat(reverify): advisory per-item verification block + summary + stale-first sort"
```

---

## Task 6: Golden vector `GV-VF-1` + honesty lock

**Files:**
- Modify: `tests/contracts/test_golden_vectors.py` (add the GV-VF-1 test)
- Modify: `tests/fixtures/contracts/warpline/golden-vectors.json` (add the index entry)

**Interfaces:**
- Consumes: `commands.reverify_worklist`, `commands.verify_record`, and the existing golden-vector test helpers (`_git_repo`, `_store`, `_seed_entity`, `_add_change`) in `test_golden_vectors.py`.
- Produces: `GV-VF-1` locking `fresh`/`stale`/`unverified` semantics, the unverified-when-no-source honesty, and the **never-filter** invariant — all asserted on the `data` block (NOT on `enrichment`, which would violate the closed vocab).

- [ ] **Step 1: Inspect the existing helpers**

Run: `grep -n "def _git_repo\|def _store\|def _seed_entity\|def _add_change" tests/contracts/test_golden_vectors.py`
Read those helpers so the new vector uses the real signatures (do not assume; e.g. `_seed_entity(store, repo_id, locator, sei)` and `_add_change(store, repo_id, key_id, path=...)` per the GV-HON-SEI example).

- [ ] **Step 2: Write the GV-VF-1 test (it will fail until the assertions match real output, but the underlying feature from Tasks 1–5 already exists)**

Add to `tests/contracts/test_golden_vectors.py`:

```python
def test_gv_vf_1_reverify_verification_freshness_is_explained(tmp_path: Path) -> None:
    """GV-VF-1: the reverify worklist carries an HONEST verification block.

    Locks: (a) unverified-when-no-source — every item reads ``unverified`` with a
    ``disabled`` reason when no gate pass is recorded; (b) ``fresh`` once the
    change is verified; (c) the never-filter invariant — recording verification
    annotates/sorts but never removes an item; (d) verification rides the data
    block, never the FROZEN enrichment vocab.
    """

    repo = _git_repo(tmp_path)
    # One real commit so verify-record can resolve HEAD to an object SHA.
    head = _commit_file(repo, "m.py", "v0\n")  # see helper note below
    with _store(repo) as store:
        repo_id = store.ensure_repo(repo)
        key_id = store.ensure_entity_key(repo_id, "python:function:m.py::f", None, head)
        store.append_change_event(
            repo_id=repo_id, entity_key_id=key_id, commit_sha=head, path="m.py",
            change_kind="modified", actor="dev", changed_at="2026-06-25T08:00:00+00:00",
        )

    # (a) No verification recorded yet -> unverified + explained.
    env = commands.reverify_worklist(repo, [key_id])
    summary = env["data"]["verification_summary"]
    assert summary["local_source_configured"] is False
    assert summary["unverified"] >= 1
    assert env["data"]["items"], "expected a non-empty worklist"
    n_items = len(env["data"]["items"])
    item = env["data"]["items"][0]
    assert item["verification"]["state"] == "unverified"
    assert item["verification"]["reason"]["reason_class"] == "disabled"
    assert item["verification"]["reason"]["cause"] and item["verification"]["reason"]["fix"]
    # (d) verification is NOT in the frozen enrichment vocab.
    assert "verification" not in env["enrichment"]
    assert "verification" not in env["enrichment_reasons"]

    # (b) record a gate pass at HEAD -> fresh.
    commands.verify_record(repo, commit=head, kind="test_pass", now="2026-06-25T10:00:00+00:00")
    env2 = commands.reverify_worklist(repo, [key_id])
    assert env2["data"]["verification_summary"]["local_source_configured"] is True
    assert env2["data"]["verification_summary"]["fresh"] >= 1
    assert env2["data"]["items"], "expected a non-empty worklist after verification"
    assert any(i["reason"] == "changed" for i in env2["data"]["items"])
    fresh_item = next(i for i in env2["data"]["items"] if i["reason"] == "changed")
    assert fresh_item["verification"]["state"] == "fresh"
    assert fresh_item["verification"]["last_verified_commit"] == head

    # (c) never-filter is an IDENTITY invariant, not just cardinality: the exact
    # SET of entities is unchanged by recording verification (count-equality alone
    # would pass a buggy impl that drops one item and re-adds a different one).
    assert len(env2["data"]["items"]) == n_items
    before_locators = {i["entity"]["locator"] for i in env["data"]["items"]}
    after_locators = {i["entity"]["locator"] for i in env2["data"]["items"]}
    assert after_locators == before_locators
    # Honesty meta preserved.
    assert env2["meta"]["local_only"] is True
    assert env2["meta"]["peer_side_effects"] == []
```

**REQUIRED helper (the module does NOT have one):** `test_golden_vectors.py` has `_git_repo`/`_store`/`_seed_entity`/`_add_change` but NO `_commit_file`, and `_seed_entity`/`_add_change` use FAKE SHAs (e.g. `"c1"`) that `verify_record`'s `git rev-parse` cannot resolve. So this Step MUST add a real commit helper near the top of the module and seed via `ensure_entity_key`/`append_change_event` with the REAL HEAD SHA (as the test above does) — NOT `_seed_entity`:

```python
def _commit_file(repo: Path, name: str, body: str) -> str:
    (repo / name).write_text(body)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", f"touch {name}"], cwd=repo, check=True, capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()
```

(Confirm `subprocess` and `Path` are imported in the module; `_git_repo` already creates the git repo, so call `_commit_file` on the repo it returns.)

- [ ] **Step 3: Add the fixture index entry**

In `tests/fixtures/contracts/warpline/golden-vectors.json`, add to the `vectors` array (match the existing entry shape — `id`, `seam`, `tool`, `assert`):

```json
{
  "id": "GV-VF-1",
  "seam": "warpline",
  "tool": "warpline_reverify_worklist_get / warpline_verification_record",
  "assert": "reverify carries an honest verification block on the DATA item (never the frozen enrichment vocab): no source -> every item unverified + disabled triple + local_source_configured false; record a gate pass at the change commit -> fresh + last_verified_commit set + local_source_configured true; recording verification never removes an item (never-filter); meta.local_only true / peer_side_effects []"
}
```

> If the fixture has a count field (e.g. a top-level `"count"` or a test asserting `len(vectors) == N`), bump it. Grep: `grep -rn "len(.*vectors\|count" tests/contracts/test_golden_vectors.py`.

- [ ] **Step 4: Run the golden vectors**

Run: `uv run pytest tests/contracts/test_golden_vectors.py -v`
Expected: PASS, including `GV-VF-1` and the existing vectors (and any "fixture index matches tests" meta-check).

- [ ] **Step 5: Commit**

```bash
git add tests/contracts/test_golden_vectors.py tests/fixtures/contracts/warpline/golden-vectors.json
git commit -m "test(contracts): GV-VF-1 locks verification-freshness honesty + never-filter"
```

---

## Task 7: Gate sweep + CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`
- Verify only: all gates green; no member diffs; mcp-smoke advertises the new tool.

**Interfaces:**
- Consumes: everything from Tasks 1–6.
- Produces: a green release-candidate-equivalent gate run and a CHANGELOG entry. (No tag/release — owner-reserved.)

- [ ] **Step 1: Full test suite**

Run: `uv run pytest tests -v`
Expected: all PASS (the pre-existing baseline was 338 passed / 1 skipped; this adds ~45 new tests + GV-VF-1). 0 failures. If any PRE-EXISTING reverify/contract test fails, it will be because the additive per-item `verification` key or the new `verification_summary` data key changed a shape it asserts. Confirm the failure is an additive-key mismatch (NOT a frozen-envelope/enrichment-vocab break) and update that test to tolerate the additive key — e.g. `tests/test_reverify.py:25-30` asserts only the `enrichment` sub-dict (survives), so a break elsewhere means a test asserting whole-item-dict equality; relax it to the keys it cares about. Never weaken the closed `enrichment` vocab to make a test pass.

- [ ] **Step 2: Lint + types**

Run: `uv run ruff check . && uv run mypy src/warpline`
Expected: clean.

- [ ] **Step 3: MCP smoke (new tool advertised)**

Run: `uv run warpline mcp-smoke --repo . --json`
Expected: `ok: true`. Then confirm the new tool is listed:
Run: `uv run warpline mcp-smoke --repo . --json | python -c "import sys, json; d=json.load(sys.stdin); print('warpline_verification_record present:', any(c for c in d.get('checks', []) ))"`
(Or simpler — `uv run python -c "from warpline import mcp; print('warpline_verification_record' in {s['endorsed'] for s in mcp.TOOL_SPECS})"` → `True`.)

- [ ] **Step 4: Dogfood eval**

Run: `uv run warpline dogfood-eval --output /tmp/wl-dogfood.json --json`
Expected: `ready: True` (the existing dogfood cases must still pass — the additive `verification` block must not break parity or item counts; if a dogfood assertion counts item keys exactly, update the harness to tolerate the additive key, treating it like any other advisory enrichment).

- [ ] **Step 5: Member-diff guard**

Run: `bash scripts/maybe_check_member_diffs.sh`
Expected: 0 warpline-caused diffs in sibling repos (this change touches only warpline's own tree — no sibling files).

- [ ] **Step 6: Update CHANGELOG**

In `CHANGELOG.md`, add an `[Unreleased]` (or `1.3.0`) section above `[1.2.0]`:

```markdown
## [Unreleased]

### Added
- **Verification freshness (Rung 2, Track B).** The reverify worklist now carries
  an advisory per-item `verification` block (`fresh` / `stale` / `unverified` /
  `unavailable`) with a trust-decay signal, plus a `verification_summary` rollup —
  answering "what changed since it was last proven good." Sourced from warpline's
  own gate result via a new mutating verb `verify-record` (CLI) /
  `warpline_verification_record` (MCP), the 2nd local-only mutating tool. Advisory
  and enrich-only: it annotates and re-sorts (stale-of-trust first) but NEVER
  filters an item, and NEVER gates. Sibling-sourced verification (wardline/
  filigree/legis) remains honest-absent RESERVED. New schema v4
  (`verification_events`); golden vector `GV-VF-1`. The frozen `warpline.<contract>.v1`
  envelope and the closed 6-key enrichment vocab are untouched (verification rides
  the reverify-item schema, not the enrichment vocab).
```

- [ ] **Step 7: Confirm a clean tree + final commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): verification freshness (Rung 2 Track B)"
git status --short   # expect: clean
```

- [ ] **Step 8: Run the release-candidate gate end-to-end (read-only confidence check)**

Run: `bash scripts/check_release_candidate.sh`
Expected: exits 0 (clean tree, member-diffs, spike, dogfood, productization, ruff, mypy, pytest all green). This is the merge-readiness proof. (Do NOT tag or release — that is owner-directed.)

---

## Self-Review (completed by plan author)

**Spec coverage:**
- v4 migration + accessors → Task 1 ✅
- `verify-record` verb (CLI+MCP, ref-resolution, errors, tool metadata) → Task 4 ✅
- pure `compose_verification_freshness` (fresh/stale/unverified/unavailable + reason triples) → Task 3 (+ git helpers Task 2) ✅
- reverify integration (per-item block + summary + advisory sort, never filter) → Task 5 ✅
- `GV-VF-1` + honesty lock → Task 6 ✅
- gate sweep → Task 7 ✅
- Non-goals respected: sibling sources stay RESERVED/honest-absent (not implemented); `verification` NOT promoted to the frozen envelope vocab (rides data/item field); no gating/filtering (never-filter test in Tasks 5 & 6). ✅

**Type consistency:** `compose_verification_freshness(entity_change_commits, verification_events, covers, commits_between)` is referenced identically in Task 3 (def), Task 5 (`reverify.py` default + `commands.py` call). `verification_for: Callable[[int | None], dict]` consistent between `reverify.py` and `commands.py`. The block keys (`state`/`last_verified_at`/`last_verified_commit`/`decay.commits_behind`/`reason`) are identical across Tasks 3, 5, 6. `record_verification_event` / `list_verification_events` signatures identical across Tasks 1, 4, 5.

**Plan-review v1 (4-dimension panel + synthesis, 2026-06-25) — all blocker/high/medium findings resolved into the plan:**
- BLOCKER — `test_store_migrations.py:48` pins `HIGHEST_KNOWN_VERSION == 3` → Task 1 Step 6b updates it to `== 4` (required).
- BLOCKER — 2nd mutating tool breaks `test_warpline_contract_fixtures.py:54-55` (`mutates is is_capture`) + the static `mcp-tool-inventory.json` → Task 4 Step 5b generalizes the assertion + regenerates the inventory (required).
- BLOCKER — import-time `assert_inputschema_consumed()` (`mcp.py:574`) crashes all tools if the new tool is missing from `_HANDLER_CONSUMES`/`_KNOWN_FASTFOLLOW_DEAD` → Task 4 Step 5 makes BOTH entries required, not conditional.
- BLOCKER — `GV-VF-1` referenced a non-existent `_commit_file` helper + fake SHAs → Task 6 Step 2 makes the real-commit helper required and seeds with the real HEAD SHA + adds items guards.
- HIGH — `verification_summary` placement was self-contradictory → Task 5 Step 4 fixes it to post-filter/post-sort/pre-page, with a dedicated filter test.
- MEDIUM — wrong error code for blank `kind` → `MissingRequiredFieldError` (Task 4 Step 3). O(N) full-table scan → `list_change_events_for_key_ids` (Tasks 1 + 5). Advisory-sort/sort_by interaction → documented as secondary tiebreak + stale-before-fresh test (Task 5). `verified_at` lexical-sort bug → `datetime()`-normalized ORDER BY + offset test (Task 1). Missing `unavailable` integration + idempotency-across-timestamps coverage → added (Tasks 4 + 5).
- LOW — reuse `_now()` (Task 4); CLI error-path test (Task 4); reconcile spec accessor names (spec updated); document `enrich_blast` order invariant (Task 5 Step 3).

**Plan-review v2 (re-review, 2026-06-25) — 0 blockers; all 4 HIGH + 5 MEDIUM resolved:**
- HIGH — advisory-presort placement → pinned BETWEEN `apply_filters` (787) and `apply_sort` (788) so `apply_sort` stays primary (Task 5 Step 4).
- HIGH — stale-before-fresh test could pass vacuously → added `test_stale_first_is_secondary_to_an_explicit_sort` (mixed-depth, depth-primary; mirrors existing downstream setup) (Task 5).
- HIGH — post-filter summary test only covered the zero case → added `test_verification_summary_counts_only_filtered_subset` (2 entities, asserts count == 1) (Task 5).
- HIGH — `list_change_events_for_key_ids` oldest-first ordering unasserted → added `test_list_change_events_for_key_ids_is_oldest_first` (Task 1).
- MEDIUM — Step 6b under-specified → now names every stale-v3 site (lines 45-46, 48, 131, 166-175) (Task 1). Duplicate per-entity SHAs → adjacent-dedup in `changes_by_key` (Task 5). `covers`/`is_ancestor` arg-order → documented at `_covers` + `test_fresh_when_verified_at_a_later_commit` (asymmetric, catches a swap). Partial-unavailable gap → `test_unavailable_when_latest_undetermined_even_if_earlier_covered` (Task 3). Squash/rebase + detached-HEAD → `test_unavailable_when_change_commit_no_longer_exists` (Task 5) + `test_verify_record_in_detached_head` (Task 4).
- LOW — idempotency now via `record_verification_event -> bool` (O(1), race-free) (Task 1/4); GV-VF-1 never-filter strengthened to set-identity (Task 6); `test_mcp_module_imports` smoke test first (Task 4); monkeypatch import-order + `next()`-guard notes (Task 5 Step 2); stale-path `[:-1]` micro-opt (Task 3).

Confirmed by the v2 panel against source: the v1 blocker fixes are all correct (`test_store_migrations.py:48` really pins `==3`; `MissingRequiredFieldError` at `errors.py:70-73`; `_HANDLER_CONSUMES`/`_KNOWN_FASTFOLLOW_DEAD` both exist; `has_sei` filter valid at `listing.py:271-272`; `apply_sort` stable at `listing.py:332` with `sort_by=None` passthrough at `listing.py:306`). No frozen-contract violations; verification never enters the 6-key vocab.

**Residual confirm-points (LOW, the implementer verifies against source — not blocking):**
1. The exact `filters=` dict shape for the post-filter tests (Task 5; `has_sei` key verified, shape to confirm from an existing reverify filter test).
2. The `mcp-tool-inventory.json` regeneration mechanism (script vs hand-edit) — Task 4 Step 5b.
3. The downstream/affected-item edge-snapshot setup to mirror for `test_stale_first_is_secondary_to_an_explicit_sort` — Task 5 (grep existing tests for `capture_snapshot_atomic`).
