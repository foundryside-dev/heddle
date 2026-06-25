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

from collections.abc import Callable
from typing import Any

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
