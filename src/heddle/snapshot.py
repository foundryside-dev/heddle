from __future__ import annotations

from heddle.store import HeddleStore


def record_skipped_snapshot(
    store: HeddleStore,
    repo_id: str,
    commit_sha: str,
    reason: str,
) -> int:
    return store.create_edge_snapshot(
        repo_id=repo_id,
        commit_sha=commit_sha,
        source="loomweave",
        source_version=reason,
        completeness="SKIPPED",
    )
