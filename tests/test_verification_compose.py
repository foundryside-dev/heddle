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
