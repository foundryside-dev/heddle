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
    assert out["last_verified_at"] == "2026-06-25T10:00:00+00:00"
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
    assert out["last_verified_at"] is None
    assert out["decay"]["commits_behind"] is None


def test_unavailable_when_earlier_change_undetermined() -> None:
    # Fail-soft on the EARLIER branch: latest change is definitively uncovered,
    # but an earlier change's coverage is undetermined — never claim 'unverified'
    # (an earned clean-empty) when git could not decide.
    events = [{"commit_sha": "V1", "verified_at": "2026-06-25T10:00:00+00:00"}]

    def covers(verified: str, change: str) -> bool | None:
        if change == "C1":   # latest: definitively NOT covered
            return False
        return None          # earlier change: undetermined

    out = compose_verification_freshness(["C0", "C1"], events, covers, _between_const(0))
    assert out["state"] == "unavailable"
    assert out["reason"]["reason_class"] == "unreachable"
    assert out["last_verified_commit"] is None


def test_fresh_when_one_event_covers_latest_and_another_is_undetermined() -> None:
    # Precedence: a MIXED covers() result on the LATEST change (one event returns
    # None/undetermined, another returns True) must yield 'fresh' — a positive
    # cover wins; the None is irrelevant once a True exists.
    events = [
        {"commit_sha": "V1", "verified_at": "2026-06-25T09:00:00+00:00"},
        {"commit_sha": "V2", "verified_at": "2026-06-25T11:00:00+00:00"},
    ]

    def covers(verified: str, change: str) -> bool | None:
        return None if verified == "V1" else True  # V1 undetermined, V2 covers

    out = compose_verification_freshness(["C1"], events, covers, _between_const(0))
    assert out["state"] == "fresh"
    assert out["last_verified_commit"] == "V2"


def test_stale_decay_uses_tightest_cover_not_latest_recorded() -> None:
    # Two covering events for earlier changes, recorded OUT of git-ancestry order:
    # V_new is a more-advanced commit (tighter cover, 1 commit behind) recorded
    # FIRST; V_old is a less-advanced commit (6 behind) recorded LATER. Decay must
    # use the tightest cover (V_new -> 1), not the latest-recorded (V_old -> 6).
    events = [
        {"commit_sha": "V_new", "verified_at": "2026-06-25T10:00:00+00:00"},  # recorded first
        {"commit_sha": "V_old", "verified_at": "2026-06-25T12:00:00+00:00"},  # recorded later
    ]
    changes = ["C0", "C1", "C2"]  # latest = C2, uncovered by both
    def covers(verified: str, change: str) -> bool | None:
        return False if change == "C2" else True  # both cover earlier changes only
    def between(ancestor: str, descendant: str) -> int | None:
        return {"V_new": 1, "V_old": 6}.get(ancestor)  # distance from each cover to C2
    out = compose_verification_freshness(changes, events, covers, between)
    assert out["state"] == "stale"
    assert out["last_verified_commit"] == "V_new"   # tightest cover, NOT latest-recorded V_old
    assert out["decay"]["commits_behind"] == 1
