from __future__ import annotations

import subprocess
from collections import deque
from pathlib import Path
from typing import Any

from warpline.store import WarplineStore


def _as_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"expected integer-compatible value, got {type(value).__name__}")


def _commits_behind(repo: Path, snapshot_commit: str) -> int | None:
    proc = subprocess.run(
        ["git", "rev-list", "--count", f"{snapshot_commit}..HEAD"],
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


def blast_radius(
    store: WarplineStore,
    repo: Path,
    changed_entity_key_ids: list[int],
    depth: int,
) -> dict[str, Any]:
    if depth < 0 or depth > 5:
        raise ValueError("depth must be between 0 and 5")
    snapshot = store.latest_snapshot(repo)
    changed = [{"entity_key_id": key_id} for key_id in changed_entity_key_ids]
    if snapshot is None or snapshot["completeness"] == "SKIPPED":
        return {
            "changed": changed,
            "affected": [],
            "staleness": {"snapshot_commit": None, "commits_behind": None},
            "completeness": "NO_SNAPSHOT",
            "depth_capped": False,
        }

    adjacency: dict[int, list[dict[str, Any]]] = {}
    for edge in store.snapshot_edges(_as_int(snapshot["id"])):
        source = _as_int(edge["source_entity_key_id"])
        adjacency.setdefault(source, []).append(edge)

    seen = set(changed_entity_key_ids)
    affected: list[dict[str, Any]] = []
    # depth_capped: did the bounded traversal leave reachable impact unexplored? A
    # node at the depth horizon (current_depth >= depth) that still has an out-edge
    # to an as-yet-unseen target means the affected set is truncated, NOT exhaustive.
    # This is the honest signal the impact-completeness assessment needs — without
    # it a narrowed depth-bounded scope reads as a complete one.
    depth_capped = False
    queue: deque[tuple[int, int, list[dict[str, Any]]]] = deque(
        (key_id, 0, []) for key_id in changed_entity_key_ids
    )
    while queue:
        current, current_depth, path = queue.popleft()
        if current_depth >= depth:
            if not depth_capped:
                for edge in adjacency.get(current, []):
                    if _as_int(edge["target_entity_key_id"]) not in seen:
                        depth_capped = True
                        break
            continue
        for edge in adjacency.get(current, []):
            target = _as_int(edge["target_entity_key_id"])
            if target in seen:
                continue
            seen.add(target)
            edge_view = {
                "from": current,
                "to": target,
                "kind": edge["edge_kind"],
                "confidence": edge["confidence"],
            }
            via_edges = [*path, edge_view]
            affected.append(
                {"entity_key_id": target, "depth": current_depth + 1, "via_edges": via_edges}
            )
            queue.append((target, current_depth + 1, via_edges))

    return {
        "changed": changed,
        "affected": affected,
        "staleness": {
            "snapshot_commit": snapshot["commit_sha"],
            "commits_behind": _commits_behind(repo, str(snapshot["commit_sha"])),
        },
        "completeness": snapshot["completeness"],
        "depth_capped": depth_capped,
    }
