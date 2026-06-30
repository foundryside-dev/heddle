"""Rung 1c — self-healing SEI re-resolution sweep.

Covers the store merge core (``reresolve_entity_key_sei`` / ``null_sei_entity_keys``)
and the orchestration sweep (``reresolve.sweep_reresolve_sei``):

- a null-sei key heals to ``resolved`` when loomweave returns a SEI;
- the twin-collision merge (with and without a colliding change_event), where
  the resolved-keyed row is canonical (M5) and the orphan null key is dropped,
  the survivor keeps the resolved SEI and the merged first/last seen;
- the M5 differing-``hunk_summary`` case — the resolved row's data is preserved;
- a double run is a convergent no-op;
- loomweave absent → zero rows mutated, posture ``unavailable``, never
  resolved-to-null.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from warpline.reresolve import sweep_reresolve_sei
from warpline.store import WarplineStore


class _SeiClient:
    """Fake loomweave client resolving every locator to a fixed SEI."""

    def __init__(self, sei: str = "loomweave:eid:resolved") -> None:
        self.sei = sei
        self.calls = 0

    def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        assert name == "entity_resolve"
        self.calls += 1
        qualnames = arguments["qualnames"]
        assert isinstance(qualnames, list) and qualnames
        return {
            "results": [
                {
                    "qualname": qualnames[0],
                    "result_kind": "resolved",
                    "candidates": [{"id": "python:function:x", "sei": self.sei}],
                }
            ]
        }


class _NullClient:
    """Fake loomweave client that resolves nothing (no SEI in the index yet)."""

    def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        return {"results": []}


_LOCATOR = "python:function:src/pkg/mod.py::fn"
_LOCATOR_B = "python:function:src/pkg/mod.py::other"


def _open(tmp_path: Path) -> WarplineStore:
    return WarplineStore.open(tmp_path / "warpline.db")


def _null_key(store: WarplineStore, repo_id: str, locator: str, commit: str) -> int:
    return store.ensure_entity_key(repo_id, locator=locator, sei=None, commit_sha=commit)


def test_null_sei_entity_keys_lists_only_null_rows_id_ordered(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        _null_key(store, repo_id, _LOCATOR, "c1")
        store.ensure_entity_key(repo_id, locator=_LOCATOR_B, sei="loomweave:eid:x", commit_sha="c1")
        _null_key(store, repo_id, "python:function:src/pkg/mod.py::third", "c1")

        rows = store.null_sei_entity_keys(repo)
        locators = [r["locator"] for r in rows]
        assert locators == [_LOCATOR, "python:function:src/pkg/mod.py::third"]
        assert rows[0]["id"] < rows[1]["id"]


def test_sweep_resolves_null_key_in_place(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    client = _SeiClient()
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        key_id = _null_key(store, repo_id, _LOCATOR, "c1")

        report = sweep_reresolve_sei(store, repo, client)
        assert report == {
            "scanned": 1,
            "resolved": 1,
            "merged": 0,
            "still_null": 0,
            "loomweave": "present",
        }
        keys = {int(k["id"]): k for k in store.list_entity_keys(repo)}
        assert keys[key_id]["sei"] == "loomweave:eid:resolved"


def test_sweep_loomweave_absent_is_noop_and_unavailable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        key_id = _null_key(store, repo_id, _LOCATOR, "c1")

        report = sweep_reresolve_sei(store, repo, client=None)
        assert report == {
            "scanned": 1,
            "resolved": 0,
            "merged": 0,
            "still_null": 1,
            "loomweave": "unavailable",
        }
        # Never resolved-to-null: the row is untouched, sei still NULL.
        keys = {int(k["id"]): k for k in store.list_entity_keys(repo)}
        assert keys[key_id]["sei"] is None


def test_sweep_resolves_nothing_when_index_has_no_sei(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        _null_key(store, repo_id, _LOCATOR, "c1")

        report = sweep_reresolve_sei(store, repo, _NullClient())
        assert report["loomweave"] == "absent"
        assert report["resolved"] == 0
        assert report["still_null"] == 1


def test_twin_collision_merges_without_duplicate_event(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    resolved_sei = "loomweave:eid:resolved"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        # Resolved twin exists first (commit c2), then a null-keyed row for the
        # same locator (commit c1) — minted while loomweave was down.
        twin_id = store.ensure_entity_key(
            repo_id, locator=_LOCATOR, sei=resolved_sei, commit_sha="c2"
        )
        null_id = _null_key(store, repo_id, _LOCATOR, "c1")
        # A change_event on the null key that does NOT collide with the twin.
        store.append_change_event(
            repo_id=repo_id,
            entity_key_id=null_id,
            commit_sha="c1",
            path="src/pkg/mod.py",
            change_kind="modified",
            actor="agent",
            changed_at="2026-01-01T00:00:00Z",
        )

        report = sweep_reresolve_sei(store, repo, _SeiClient(resolved_sei))
        assert report["merged"] == 1
        assert report["resolved"] == 0

        keys = {int(k["id"]): k for k in store.list_entity_keys(repo)}
        # Orphan null key gone; twin survives with the resolved SEI.
        assert null_id not in keys
        assert keys[twin_id]["sei"] == resolved_sei
        # Carried first/last seen: min(first)=c1, max(last)=c2.
        assert keys[twin_id]["first_seen_commit"] == "c1"
        assert keys[twin_id]["last_seen_commit"] == "c2"
        # The non-colliding event was repointed onto the survivor.
        events = store.list_change_events(repo)
        assert len(events) == 1
        assert int(events[0]["entity_key_id"]) == twin_id


def test_twin_collision_drops_null_keyed_duplicate_preserving_resolved_data(
    tmp_path: Path,
) -> None:
    """M5/Q7: colliding change_events keep the resolved-keyed row's data."""

    repo = tmp_path / "repo"
    resolved_sei = "loomweave:eid:resolved"
    common = dict(
        commit_sha="c1",
        path="src/pkg/mod.py",
        change_kind="modified",
        actor="agent",
        changed_at="2026-01-01T00:00:00Z",
    )
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        twin_id = store.ensure_entity_key(
            repo_id, locator=_LOCATOR, sei=resolved_sei, commit_sha="c1"
        )
        null_id = _null_key(store, repo_id, _LOCATOR, "c1")
        # Two events that collide on the change_events UNIQUE constraint
        # (same commit/path/change_kind), differing only on hunk_summary.
        store.append_change_event(
            repo_id=repo_id, entity_key_id=twin_id, hunk_summary="RESOLVED-DATA", **common
        )
        store.append_change_event(
            repo_id=repo_id, entity_key_id=null_id, hunk_summary="NULL-DATA", **common
        )

        report = sweep_reresolve_sei(store, repo, _SeiClient(resolved_sei))
        assert report["merged"] == 1

        events = store.list_change_events(repo)
        assert len(events) == 1, "null-keyed duplicate must be deleted"
        assert int(events[0]["entity_key_id"]) == twin_id
        # The resolved-keyed row's data survives; the null row's was discarded.
        keys = {int(k["id"]): k for k in store.list_entity_keys(repo)}
        assert null_id not in keys
        # Re-read the surviving event's hunk_summary directly.
        row = store.conn.execute(
            "SELECT hunk_summary FROM change_events WHERE entity_key_id = ?",
            (twin_id,),
        ).fetchone()
        assert row["hunk_summary"] == "RESOLVED-DATA"


def test_double_run_is_a_noop(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    client = _SeiClient()
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        _null_key(store, repo_id, _LOCATOR, "c1")

        first = sweep_reresolve_sei(store, repo, client)
        assert first["resolved"] == 1

        second = sweep_reresolve_sei(store, repo, client)
        assert second == {
            "scanned": 0,
            "resolved": 0,
            "merged": 0,
            "still_null": 0,
            "loomweave": "absent",
        }


def test_merge_core_action_noop_when_already_healed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        key_id = store.ensure_entity_key(
            repo_id, locator=_LOCATOR, sei="loomweave:eid:resolved", commit_sha="c1"
        )
        # Calling the merge core on an already-resolved key matches no null row.
        outcome = store.reresolve_entity_key_sei(
            repo_id=repo_id,
            null_key_id=key_id,
            locator=_LOCATOR,
            resolved_sei="loomweave:eid:resolved",
        )
        assert outcome == {"action": "noop"}


# --- #3: merge repoints co_change_pairs and snapshot_edges, not just events ---


def _pair(
    store: WarplineStore, repo_id: str, a: int, b: int
) -> tuple[int, int, int] | None:
    """The (a, b, co_change_count) row for a canonical pair, or None."""

    lo, hi = (a, b) if a < b else (b, a)
    row = store.conn.execute(
        "SELECT co_change_count FROM co_change_pairs "
        "WHERE repo_id = ? AND entity_key_id_a = ? AND entity_key_id_b = ?",
        (repo_id, lo, hi),
    ).fetchone()
    return None if row is None else (lo, hi, int(row["co_change_count"]))


def test_merge_repoints_co_change_pairs_and_snapshot_edges(tmp_path: Path) -> None:
    """#3: a null key in co_change_pairs / snapshot_edges is repointed to the twin.

    Covers the three co_change_pairs cases — a clean repoint, a collision that
    MERGES counts, and a self-pair that COLLAPSES — plus snapshot_edges repoint
    with a collision drop. After the merge no row may reference the deleted null
    id, counts are summed not lost, and no self-pair survives.
    """

    repo = tmp_path / "repo"
    resolved_sei = "loomweave:eid:resolved"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        # Resolved twin pre-exists for _LOCATOR; the null key is for the SAME
        # locator (so the UPDATE collides and the merge path runs). X and Y are
        # other entities the null key co-changed with.
        twin_id = store.ensure_entity_key(
            repo_id, locator=_LOCATOR, sei=resolved_sei, commit_sha="c2"
        )
        null_id = _null_key(store, repo_id, _LOCATOR, "c1")
        x_id = store.ensure_entity_key(
            repo_id, locator=_LOCATOR_B, sei="loomweave:eid:x", commit_sha="c1"
        )
        y_id = store.ensure_entity_key(
            repo_id,
            locator="python:function:src/pkg/mod.py::y",
            sei="loomweave:eid:y",
            commit_sha="c1",
        )

        def _insert_pair(a: int, b: int, count: int, last: str, sha: str) -> None:
            lo, hi = (a, b) if a < b else (b, a)
            store.conn.execute(
                "INSERT INTO co_change_pairs(repo_id, entity_key_id_a, entity_key_id_b, "
                "co_change_count, last_co_change, last_commit_sha) VALUES (?, ?, ?, ?, ?, ?)",
                (repo_id, lo, hi, count, last, sha),
            )

        # (null, X): no twin pair → clean repoint to (twin, X), count preserved.
        _insert_pair(null_id, x_id, 3, "2024-01-01", "n_x")
        # (null, Y) AND (twin, Y): collide after repoint → counts SUM (4+2=6),
        # later marker (2024-06-01 from twin) kept.
        _insert_pair(null_id, y_id, 4, "2024-01-01", "n_y")
        _insert_pair(twin_id, y_id, 2, "2024-06-01", "t_y")
        # (null, twin): self-pair after repoint → DROPPED.
        _insert_pair(null_id, twin_id, 5, "2024-02-01", "n_t")
        store.conn.commit()

        # snapshot_edges: a non-colliding edge (null→X) and a colliding pair
        # (null→Y) vs an existing (twin→Y).
        snap_id = store.create_edge_snapshot(repo_id, "c2", "loomweave", "v1", "FULL")
        store.append_snapshot_edge(
            snap_id, source_entity_key_id=null_id, target_entity_key_id=x_id,
            edge_kind="calls", confidence="high",
        )
        store.append_snapshot_edge(
            snap_id, source_entity_key_id=null_id, target_entity_key_id=y_id,
            edge_kind="calls", confidence="high",
        )
        store.append_snapshot_edge(
            snap_id, source_entity_key_id=twin_id, target_entity_key_id=y_id,
            edge_kind="calls", confidence="high",
        )

        outcome = store.reresolve_entity_key_sei(
            repo_id=repo_id,
            null_key_id=null_id,
            locator=_LOCATOR,
            resolved_sei=resolved_sei,
        )
        assert outcome == {"action": "merged"}

        # --- co_change_pairs ---
        # No row references the deleted null id.
        dangling = store.conn.execute(
            "SELECT COUNT(*) AS c FROM co_change_pairs "
            "WHERE entity_key_id_a = ? OR entity_key_id_b = ?",
            (null_id, null_id),
        ).fetchone()["c"]
        assert dangling == 0
        # Clean repoint: (twin, X) carries the original count.
        assert _pair(store, repo_id, twin_id, x_id) == (
            *sorted((twin_id, x_id)),
            3,
        )
        # Collision merge: (twin, Y) summed to 6, later marker kept.
        ty = store.conn.execute(
            "SELECT co_change_count, last_co_change, last_commit_sha "
            "FROM co_change_pairs WHERE entity_key_id_a = ? AND entity_key_id_b = ?",
            (min(twin_id, y_id), max(twin_id, y_id)),
        ).fetchone()
        assert int(ty["co_change_count"]) == 6
        assert ty["last_co_change"] == "2024-06-01"
        assert ty["last_commit_sha"] == "t_y"
        # Self-pair collapsed: no (twin, twin) row.
        assert _pair(store, repo_id, twin_id, twin_id) is None

        # --- snapshot_edges ---
        edges = {
            (int(e["source_entity_key_id"]), int(e["target_entity_key_id"]))
            for e in store.snapshot_edges(snap_id)
        }
        # Null id gone from edges; (twin→X) and a single (twin→Y) survive.
        assert all(null_id not in pair for pair in edges)
        assert (twin_id, x_id) in edges
        assert (twin_id, y_id) in edges
        # The colliding (null→Y) was dropped, not duplicated.
        assert sum(1 for s, t in edges if (s, t) == (twin_id, y_id)) == 1

        # The orphan null key itself is gone.
        keys = {int(k["id"]) for k in store.list_entity_keys(repo)}
        assert null_id not in keys

        # U1 forward-regression guard: after the full real merge surface (clean
        # repoint + count-merge collision + self-pair collapse + snapshot-edge
        # collision drop), every entity_key_id referenced by the FK-less derived
        # tables still resolves to an entity_keys row. This passes today (the
        # merge is already correct) and is a tripwire: it goes red if a FUTURE
        # edit drops a _repoint_* call, mis-orders the DELETE-before-repoint, or
        # adds a third entity_key_id-keyed table the merge leaves unrepointed.
        # Deliberately asserts NOTHING about a twin->twin snapshot self-edge:
        # that is a valid (non-orphan) row, so the invariant never fires on it,
        # and asserting its absence would silently enact the out-of-scope U11
        # change.
        store._assert_no_orphans()


def test_assert_no_orphans_catches_orphan_co_change_pair(tmp_path: Path) -> None:
    """U1 teeth (co_change_pairs branch): a bogus entity_key_id is caught.

    The entity_key_id_a/_b columns carry NO foreign key (even with
    foreign_keys=ON), so a row referencing a non-existent entity_keys id INSERTs
    cleanly. The invariant must detect it. Isolated to its own store with no
    snapshot_edges orphan so this branch is proven independently — the method
    raises on the first orphan found, so a shared DB would never exercise both.
    """

    repo = tmp_path / "repo"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        real_id = store.ensure_entity_key(
            repo_id, locator=_LOCATOR, sei="loomweave:eid:real", commit_sha="c1"
        )
        bogus_id = 999_999
        assert bogus_id != real_id
        # No FK on these columns: this INSERT succeeds and orphans the row.
        store.conn.execute(
            "INSERT INTO co_change_pairs(repo_id, entity_key_id_a, entity_key_id_b, "
            "co_change_count, last_co_change, last_commit_sha) VALUES (?, ?, ?, ?, ?, ?)",
            (repo_id, min(real_id, bogus_id), max(real_id, bogus_id), 1, None, None),
        )
        store.conn.commit()

        with pytest.raises(RuntimeError):
            store._assert_no_orphans()


def test_assert_no_orphans_catches_orphan_snapshot_edge(tmp_path: Path) -> None:
    """U1 teeth (snapshot_edges branch): a bogus source/target id is caught.

    snapshot_edges' only FK is snapshot_id; source_entity_key_id /
    target_entity_key_id have NO foreign key. A valid snapshot with a bogus
    target id therefore INSERTs cleanly (a bogus snapshot_id would instead trip
    the snapshot_id FK and never reach the invariant). Isolated to its own store
    with no co_change_pairs orphan so this branch is proven independently.
    """

    repo = tmp_path / "repo"
    with _open(tmp_path) as store:
        repo_id = store.ensure_repo(repo)
        real_id = store.ensure_entity_key(
            repo_id, locator=_LOCATOR, sei="loomweave:eid:real", commit_sha="c1"
        )
        bogus_id = 999_999
        assert bogus_id != real_id
        snap_id = store.create_edge_snapshot(repo_id, "c1", "loomweave", "v1", "FULL")
        # Valid snapshot_id (FK satisfied), bogus target id (no FK): orphans.
        store.append_snapshot_edge(
            snap_id,
            source_entity_key_id=real_id,
            target_entity_key_id=bogus_id,
            edge_kind="calls",
            confidence="high",
        )

        with pytest.raises(RuntimeError):
            store._assert_no_orphans()
