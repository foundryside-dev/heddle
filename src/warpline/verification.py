"""Pure verification-freshness compute (internal API).

Mirrors ``_enrichment.py``: enrich-only, no store, no git, no I/O — git
reachability is injected as the ``covers`` / ``commits_between`` callables. The
import list (``collections.abc`` + ``typing`` + ``warpline.listing.reason``) is
the structural proof that this module cannot gate, mirror a sibling, or perform
I/O.

Freshness asks: has the entity's LATEST change been proven good by a recorded
gate run? A gate run at commit ``V`` "covers" a change at commit ``C`` iff ``C``
is an ancestor-or-equal of ``V`` (the gate ran at or after the change landed).
Absence is always EXPLAINED via a weft-reason triple; it never reads as verified.

For the STALE path, decay uses the TIGHTEST git cover — the covering event whose
commit is fewest commits behind the latest change (the most-advanced proof
available) — not the most-recently-recorded covering event. This ensures
``decay.commits_behind`` reflects the best verification already on record,
regardless of the order in which events were written.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from warpline.listing import reason


def _tightest_covering_event(
    change_commits: list[str],
    events: list[dict[str, Any]],
    covers: Callable[[str, str], bool | None],
    commits_between: Callable[[str, str], int | None],
    latest_change: str,
) -> tuple[dict[str, Any] | None, int | None, bool]:
    """Return (tightest covering event, its commits_behind, saw_undetermined).

    A "covering" event covers at least one of ``change_commits``. Among them, pick
    the TIGHTEST cover — the one whose commit is fewest commits behind
    ``latest_change`` (minimal ``commits_between(event_commit, latest_change)``) —
    so decay reflects the most-advanced proof, not merely the most-recently
    recorded. ``events`` is oldest-first; ties on distance break toward the most
    recent ``verified_at`` (later iteration). If covering events exist but none has
    a computable distance, fall back to the most-recent covering event with a None
    decay. ``saw_undetermined`` is True if any ``covers`` call returned None.
    """
    best_event: dict[str, Any] | None = None
    best_dist: int | None = None
    fallback_event: dict[str, Any] | None = None
    saw_undetermined = False
    for event in events:
        verified_commit = str(event.get("commit_sha"))
        covers_any = False
        for change_commit in change_commits:
            result = covers(verified_commit, change_commit)
            if result is None:
                saw_undetermined = True
            elif result is True:
                covers_any = True
                break
        if not covers_any:
            continue
        fallback_event = event  # oldest-first -> last covering wins as fallback
        dist = commits_between(verified_commit, latest_change)
        if dist is None:
            continue
        if best_dist is None or dist <= best_dist:  # tie -> most recent (later) wins
            best_dist = dist
            best_event = event
    if best_event is not None:
        return best_event, best_dist, saw_undetermined
    return fallback_event, None, saw_undetermined


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
    covering_event, commits_behind, earlier_undetermined = _tightest_covering_event(
        entity_change_commits[:-1], verification_events, covers, commits_between, latest_change
    )
    if covering_event is not None:
        return {
            "state": "stale",
            "last_verified_at": covering_event.get("verified_at"),
            "last_verified_commit": covering_event.get("commit_sha"),
            "decay": {"commits_behind": commits_behind},
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
