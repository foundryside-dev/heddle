"""Unit tests for the impact-completeness self-assessment (federation D1).

``_completeness`` is pure (no store, no git, no I/O): it maps the already-computed
snapshot completeness + staleness + unresolved miss-set + depth-cap flag into the
federation-facing ``impact_completeness`` object, and provides the consumer-side
risk gate (risk-as-verification). Mirrors ``_enrichment`` / ``verification`` in
posture: it can only narrow toward honesty, never claim clean.
"""

from __future__ import annotations

from warpline._completeness import (
    COMPLETENESS_REASON_CODES,
    COMPLETENESS_RISK_CODES,
    IMPACT_COMPLETENESS_STATUS,
    completeness_risk,
    compute_impact_completeness,
)
from warpline.listing import REASON_CLASSES

_FRESH = {"snapshot_commit": "c0ffee00", "commits_behind": 0}
_STALE = {"snapshot_commit": "c0ffee00", "commits_behind": 3}
_UNKNOWN_FRESH = {"snapshot_commit": "c0ffee00", "commits_behind": None}
_NO_SNAP = {"snapshot_commit": None, "commits_behind": None}
_AS_OF = "2026-01-01T00:00:00+00:00"


def _ic(**kwargs: object) -> dict:
    """compute_impact_completeness with a pinned as_of (the producer timestamp is
    a passthrough; these tests exercise the derived assessment)."""
    kwargs.setdefault("as_of", _AS_OF)
    return compute_impact_completeness(**kwargs)  # type: ignore[arg-type]


def _assert_well_formed(obj: dict) -> None:
    assert obj["status"] in IMPACT_COMPLETENESS_STATUS
    assert obj["as_of"] == _AS_OF
    assert isinstance(obj["graph_fresh"], bool)
    assert obj["graph_ref"] is None or isinstance(obj["graph_ref"], str)
    assert isinstance(obj["depth_capped"], bool)
    assert isinstance(obj["unresolved_count"], int)
    assert isinstance(obj["reasons"], list)
    assert set(obj["reasons"]) <= COMPLETENESS_REASON_CODES
    # the closed contract key set — wardline mirrors these verbatim. Both axes:
    # staleness (as_of/graph_fresh/graph_ref) + completeness (status/depth_capped/
    # unresolved_count) + the machine reasons.
    assert set(obj) == {
        "status",
        "as_of",
        "graph_fresh",
        "graph_ref",
        "depth_capped",
        "unresolved_count",
        "reasons",
    }


# ----------------------------------------------------------------- producer


def test_full_fresh_unresolved_zero_no_cap_is_complete() -> None:
    obj = _ic(
        completeness="FULL", staleness=_FRESH, unresolved=[], depth_capped=False
    )
    _assert_well_formed(obj)
    assert obj["status"] == "complete"
    assert obj["graph_fresh"] is True
    assert obj["graph_ref"] == "c0ffee00"
    assert obj["depth_capped"] is False
    assert obj["unresolved_count"] == 0
    assert obj["reasons"] == []


def test_stale_graph_is_partial_never_complete() -> None:
    obj = _ic(
        completeness="FULL", staleness=_STALE, unresolved=[], depth_capped=False
    )
    _assert_well_formed(obj)
    assert obj["status"] == "partial"
    assert obj["graph_fresh"] is False
    assert "graph_stale" in obj["reasons"]


def test_unknown_freshness_is_not_complete() -> None:
    # git could not compute commits_behind -> we cannot positively claim fresh,
    # so we must NOT claim complete (conservative honesty).
    obj = _ic(
        completeness="FULL", staleness=_UNKNOWN_FRESH, unresolved=[], depth_capped=False
    )
    _assert_well_formed(obj)
    assert obj["status"] != "complete"
    assert obj["graph_fresh"] is False
    assert "graph_freshness_unknown" in obj["reasons"]


def test_depth_capped_is_partial() -> None:
    obj = _ic(
        completeness="FULL", staleness=_FRESH, unresolved=[], depth_capped=True
    )
    _assert_well_formed(obj)
    assert obj["status"] == "partial"
    assert obj["depth_capped"] is True
    assert "depth_capped" in obj["reasons"]


def test_unresolved_entities_make_partial() -> None:
    obj = _ic(
        completeness="FULL",
        staleness=_FRESH,
        unresolved=[{"ref": {"kind": "sei", "value": "x"}, "reason": "sei_not_in_snapshot"}],
        depth_capped=False,
    )
    _assert_well_formed(obj)
    assert obj["status"] == "partial"
    assert obj["unresolved_count"] == 1
    assert "unresolved_entities" in obj["reasons"]


def test_delta_snapshot_is_partial_even_when_fresh() -> None:
    obj = _ic(
        completeness="DELTA", staleness=_FRESH, unresolved=[], depth_capped=False
    )
    _assert_well_formed(obj)
    assert obj["status"] == "partial"
    assert "partial_snapshot" in obj["reasons"]


def test_no_snapshot_is_unknown_not_complete() -> None:
    obj = _ic(
        completeness="NO_SNAPSHOT", staleness=_NO_SNAP, unresolved=[], depth_capped=False
    )
    _assert_well_formed(obj)
    assert obj["status"] == "unknown"
    assert obj["graph_fresh"] is False
    assert obj["graph_ref"] is None
    assert "no_snapshot" in obj["reasons"]


def test_skipped_snapshot_is_unknown() -> None:
    obj = _ic(
        completeness="SKIPPED", staleness=_NO_SNAP, unresolved=[], depth_capped=False
    )
    _assert_well_formed(obj)
    assert obj["status"] == "unknown"
    assert "snapshot_skipped" in obj["reasons"]


def test_invariant_never_complete_without_fresh_graph() -> None:
    # The single hard invariant: complete REQUIRES a positively-fresh full graph.
    for completeness in ("FULL", "DELTA", "NO_SNAPSHOT", "SKIPPED"):
        for staleness in (_STALE, _UNKNOWN_FRESH, _NO_SNAP):
            obj = _ic(
                completeness=completeness,
                staleness=staleness,
                unresolved=[],
                depth_capped=False,
            )
            assert obj["status"] != "complete"


# ----------------------------------------------------------------- consumer gate


def _assert_risk_verdict(verdict: dict) -> None:
    assert verdict["risk"] == "unavailable"  # warpline NEVER declares clean
    assert verdict["reason_code"] in COMPLETENESS_RISK_CODES
    carrier = verdict["reason"]
    assert carrier["reason_class"] in REASON_CLASSES
    assert carrier["reason_class"] != "clean"
    assert carrier.get("cause") and carrier.get("fix")


def test_consumer_absent_completeness_is_not_declared() -> None:
    for absent in (None, {}, {"graph_fresh": True}):  # missing 'status'
        verdict = completeness_risk(absent)
        _assert_risk_verdict(verdict)
        assert verdict["reason_code"] == "completeness_not_declared"


def test_consumer_partial_degrades_to_unavailable() -> None:
    verdict = completeness_risk({"status": "partial", "reasons": ["graph_stale"]})
    _assert_risk_verdict(verdict)
    assert verdict["reason_code"] == "completeness_partial"


def test_consumer_unknown_also_degrades() -> None:
    verdict = completeness_risk({"status": "unknown", "reasons": ["no_snapshot"]})
    _assert_risk_verdict(verdict)
    assert verdict["reason_code"] == "completeness_partial"


def test_consumer_complete_is_still_never_clean() -> None:
    # Even a complete impact set is not, by itself, a proven-good verdict: the
    # risk-as-verification source (wardline attest bundle) is out of scope (gap).
    verdict = completeness_risk({"status": "complete", "reasons": []})
    _assert_risk_verdict(verdict)
    assert verdict["reason_code"] == "verification_source_absent"
