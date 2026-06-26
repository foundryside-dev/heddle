"""Impact-completeness self-assessment (federation D1) — pure, enrich-only.

Mirrors ``_enrichment`` / ``verification`` in posture: imports only ``typing`` +
``warpline._enrichment.is_stale`` + ``warpline.listing.reason`` — the structural
proof that this module cannot gate, mirror a sibling, open a store, or perform
I/O. It maps signals warpline has ALREADY computed (the snapshot edge-completeness
enum, the staleness block, the resolve-join miss-set, and a depth-cap flag from
the blast traversal) into:

  * ``compute_impact_completeness`` — the producer side: the
    ``data.impact_completeness`` object carried on every ``reverify_worklist.v1``.
    wardline mirrors this object VERBATIM into its own ``producer_completeness``
    scope-honesty field; the shape here is the federation coordination point.

  * ``completeness_risk`` — the consumer side (risk-as-verification): given the
    ``impact_completeness`` of a (pushed, untrusted) worklist, a missing or
    non-``complete`` assessment CANNOT be read as proven-good, so warpline
    degrades to ``risk=unavailable`` with an explicit machine reason. It never
    returns ``clean`` — warpline declares no change verified/allowed.

Honesty doctrine: ``status="complete"`` is emitted ONLY when the impact set is
genuinely exhaustive (a positively-fresh FULL graph, no depth cap, zero
unresolved entities). Anything else is ``partial``; when coverage cannot be
assessed at all (no graph) it is ``unknown``. Never ``complete`` on a guess.

The contract object lives at ``data.impact_completeness`` (NOT ``data.completeness``,
which is the FROZEN raw snapshot-completeness STRING enum on ``v1``). This is an
additive ``v1`` field — raw signal (string) vs. derived assessment (object).
"""

from __future__ import annotations

from typing import Any

from warpline._enrichment import is_stale
from warpline.listing import reason

# Closed status vocabulary for impact_completeness.status.
IMPACT_COMPLETENESS_STATUS = frozenset({"complete", "partial", "unknown"})

# Closed machine-code vocabulary for impact_completeness.reasons. Federation
# consumers (wardline) switch on these codes, never on prose.
COMPLETENESS_REASON_CODES = frozenset(
    {
        "graph_stale",  # snapshot is behind HEAD
        "graph_freshness_unknown",  # commits_behind could not be computed
        "partial_snapshot",  # snapshot itself is a DELTA (capped/failed at capture)
        "depth_capped",  # blast traversal truncated at the depth horizon
        "unresolved_entities",  # changed refs that did not map to graph nodes
        "no_snapshot",  # no edge snapshot exists at all
        "snapshot_skipped",  # snapshot capture was SKIPPED (loomweave absent)
    }
)

# Closed machine-code vocabulary for the consumer-side risk gate.
COMPLETENESS_RISK_CODES = frozenset(
    {
        "completeness_not_declared",  # worklist carried no impact_completeness
        "completeness_partial",  # declared, but status != complete
        "verification_source_absent",  # complete, but no proven-good source wired
    }
)

# Snapshot edge-completeness enum (the raw data.completeness STRING) for which an
# edge graph genuinely exists and downstream coverage is therefore assessable.
_GRAPH_PRESENT = frozenset({"FULL", "DELTA"})


def compute_impact_completeness(
    *,
    as_of: str,
    completeness: str,
    staleness: dict[str, Any],
    unresolved: list[Any],
    depth_capped: bool,
) -> dict[str, Any]:
    """Build the ``impact_completeness`` object. See module docstring for the
    honesty contract. ``as_of`` is the producer generation timestamp (ISO 8601) —
    the staleness axis of the assessment, which wardline echoes as an unverified
    proxy; ``completeness`` is the raw snapshot edge-completeness enum
    (FULL/DELTA/NO_SNAPSHOT/SKIPPED); ``staleness`` is the worklist staleness
    block; ``unresolved`` is the resolve-join miss-set; ``depth_capped`` is the
    blast-traversal truncation flag.

    The object carries BOTH axes of the derived assessment in one place — the
    staleness axis (``as_of`` + ``graph_fresh`` + ``graph_ref``) and the
    completeness axis (``status`` + ``depth_capped`` + ``unresolved_count``) —
    so a single federation field declares warpline's completeness AND staleness.
    """

    unresolved_count = len(unresolved)
    graph_ref = staleness.get("snapshot_commit")
    reasons: list[str] = []
    depth_capped = bool(depth_capped)

    if completeness not in _GRAPH_PRESENT:
        # No edge graph captured -> downstream coverage cannot be assessed. This
        # is "unknown" (we cannot tell), never "partial" (which implies we mapped
        # some-but-not-all of a known graph) and never "complete".
        reasons.append("no_snapshot" if completeness == "NO_SNAPSHOT" else "snapshot_skipped")
        if unresolved_count:
            reasons.append("unresolved_entities")
        return {
            "status": "unknown",
            "as_of": as_of,
            "graph_fresh": False,
            "graph_ref": graph_ref,
            "depth_capped": depth_capped,
            "unresolved_count": unresolved_count,
            "reasons": reasons,
        }

    # A graph exists (FULL or DELTA). Defer to the canonical staleness notion
    # (is_stale): behind > 0 is stale, and an uncomputable distance (behind is
    # None, snapshot commit present) is treated as not-proven-fresh — both block
    # "complete". We keep the finer reason granularity (definitely-stale vs
    # freshness-unknown) for the consumer.
    behind = staleness.get("commits_behind")
    # A claimed FULL/DELTA graph with no commit ref is incoherent input; refuse to
    # call it fresh (defensive — never claim complete without a real graph_ref).
    graph_fresh = graph_ref is not None and not is_stale(staleness)
    if not graph_fresh:
        if isinstance(behind, int) and behind > 0:
            reasons.append("graph_stale")
        else:
            reasons.append("graph_freshness_unknown")
    if completeness == "DELTA":
        reasons.append("partial_snapshot")
    if depth_capped:
        reasons.append("depth_capped")
    if unresolved_count:
        reasons.append("unresolved_entities")

    exhaustive = (
        completeness == "FULL"
        and graph_fresh
        and not depth_capped
        and unresolved_count == 0
    )
    return {
        "status": "complete" if exhaustive else "partial",
        "as_of": as_of,
        "graph_fresh": graph_fresh,
        "graph_ref": graph_ref,
        "depth_capped": depth_capped,
        "unresolved_count": unresolved_count,
        "reasons": reasons,
    }


def completeness_risk(impact: dict[str, Any] | None) -> dict[str, Any]:
    """Consumer-side risk-as-verification gate over a worklist's impact
    completeness.

    A worklist is a PUSHED, UNTRUSTED payload; its self-declared completeness is
    an unverified producer claim. When that claim is absent or anything other than
    ``complete``, the impact set is narrowed/partial and CANNOT be treated as
    authoritative, so warpline reports ``risk=unavailable`` with an explicit
    machine reason. Even a ``complete`` claim is not, by itself, a proven-good
    verdict — that requires the risk-as-verification source (the wardline attest
    bundle), which is out of D1 scope. This function therefore NEVER returns
    ``clean`` / ``allowed``.

    Returns ``{risk, reason_code, reason}`` where ``reason`` is a canonical
    ``listing.reason()`` weft triple (non-clean: carries cause + fix).
    """

    if not isinstance(impact, dict) or "status" not in impact:
        return {
            "risk": "unavailable",
            "reason_code": "completeness_not_declared",
            "reason": reason(
                "disabled",
                cause=(
                    "the worklist declares no impact-completeness assessment "
                    "(data.impact_completeness is absent), so its coverage is "
                    "unknown and the change cannot be treated as exhaustively analysed"
                ),
                fix=(
                    "regenerate the worklist with a warpline that emits "
                    "data.impact_completeness; until then treat the change as unverified"
                ),
            ),
        }

    status = impact.get("status")
    if status != "complete":
        codes = impact.get("reasons") or []
        return {
            "risk": "unavailable",
            "reason_code": "completeness_partial",
            "reason": reason(
                "partial",
                cause=(
                    f"impact completeness is {status!r}, not 'complete' (reasons: "
                    f"{list(codes)}); the impact set is narrowed/partial and is not "
                    "authoritative"
                ),
                fix=(
                    "resolve the partial-coverage reasons (recapture a fresh graph, "
                    "raise traversal depth, resolve unmapped entities) and regenerate "
                    "the worklist"
                ),
            ),
        }

    # status == complete: the completeness gate does not degrade, but warpline
    # still never declares clean. The proven-good verdict is owned by the
    # (out-of-scope) risk-as-verification consumer; until it is wired this is a
    # gap, not a pass.
    return {
        "risk": "unavailable",
        "reason_code": "verification_source_absent",
        "reason": reason(
            "disabled",
            cause=(
                "impact completeness is 'complete', but no risk-as-verification "
                "source (wardline attest bundle) is wired to prove the change good"
            ),
            fix=(
                "wire the wardline attestation consumer (Rung 2) so a complete impact "
                "set can be turned into a verified verdict"
            ),
        ),
    }
