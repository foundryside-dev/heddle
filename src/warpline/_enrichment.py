"""Pure staleness/completeness enrichment helpers (internal API).

Extracted from ``commands.py`` (Rung 0). Dependency is strictly one-way:
``commands.py -> _enrichment``; this module imports only from ``warpline.listing``
(no store, no git, no I/O — enrich-only doctrine preserved) and is structurally
incapable of gating (enrich-only doctrine, verified by its import list: only
``typing.Any`` and ``warpline.listing.reason``). No store, no git, no I/O.
"""

from __future__ import annotations

from typing import Any

from warpline.listing import reason

# enrichment.edges value for each completeness level.
EDGES_FOR_COMPLETENESS = {
    "FULL": "present",
    "DELTA": "partial",
    "NO_SNAPSHOT": "absent",
    "SKIPPED": "skipped",
}


def is_stale(staleness: dict[str, Any]) -> bool:
    """The snapshot was captured at a commit behind HEAD.

    ``commits_behind`` is the live answer to ``snapshot_commit..HEAD``; any
    positive count means the stored edge graph no longer describes HEAD. A
    ``None`` count means we could not ask git (detached snapshot commit, shallow
    clone) — we treat that as *unknown, therefore not-proven-fresh* and surface
    it as stale rather than silently claiming completeness.
    """

    behind = staleness.get("commits_behind")
    if behind is None:
        return staleness.get("snapshot_commit") is not None
    return int(behind) > 0


def edges_enrichment(completeness: str, staleness: dict[str, Any]) -> str:
    """Map (completeness, staleness) → the closed ``enrichment.edges`` vocab.

    A FULL-or-DELTA snapshot that is *behind HEAD* downgrades to the live
    ``"stale"`` value: the edge graph is real but no longer describes the
    working tree, so completeness must NOT be claimed. Without this, a stale-
    but-FULL snapshot would emit ``edges:"present"`` and hand an agent a
    confident affected-set with zero freshness warning (PDR-0023: the quiet
    segfault). NO_SNAPSHOT / SKIPPED are already-honest "we have nothing" states
    and are reported as-is regardless of staleness.
    """

    base = EDGES_FOR_COMPLETENESS.get(completeness, "absent")
    if completeness in {"FULL", "DELTA"} and is_stale(staleness):
        return "stale"
    return base


def staleness_warnings(completeness: str, staleness: dict[str, Any]) -> list[str]:
    if completeness in {"FULL", "DELTA"} and is_stale(staleness):
        behind = staleness.get("commits_behind")
        commit = str(staleness.get("snapshot_commit") or "unknown")[:8]
        if behind is None:
            tail = "snapshot commit is not on HEAD's history; freshness unknown"
        else:
            tail = f"{behind} commit(s) behind HEAD"
        return [
            f"STALE: edge snapshot @ {commit} is {tail}; affected set is not complete for "
            "HEAD — recapture (warpline capture-snapshot) before trusting completeness"
        ]
    return []


def completeness_warnings(completeness: str) -> list[str]:
    return {
        "NO_SNAPSHOT": ["NO_SNAPSHOT: downstream traversal unavailable; changed set only"],
        "SKIPPED": ["SKIPPED: graph snapshot was skipped; changed set only"],
        "DELTA": ["DELTA: graph snapshot is partial; inspect failed_entities or staleness"],
    }.get(completeness, [])


def requirements_reason() -> dict[str, Any]:
    """The stable reserved-but-honest triple for the ``requirements`` dimension.

    ``requirements`` is in the FROZEN enrichment vocab but no requirements-trace
    transport is wired today. It defaults to scalar ``unavailable``; this triple
    makes that absence EXPLAINED (reserved, not yet wired) rather than a bare,
    unexplained scalar. Reuses the canonical ``disabled`` class (no transport) —
    no new reason_class, so the frozen canonical-11 contract is untouched.
    """

    return reason(
        "disabled",
        cause=(
            "the requirements dimension is reserved in the frozen enrichment vocab but no "
            "requirements-trace transport is wired in warpline yet"
        ),
        fix=(
            "wire a requirements-trace consumer (e.g. a legis/requirements read keyed on the "
            "SEI) and populate enrichment.requirements; until then it is honestly reserved, "
            "not an earned-empty"
        ),
    )


def requirements_reason_for(req_state: str) -> dict[str, Any]:
    """Map a closed ``enrichment.requirements`` scalar to its weft-reason triple.

    Mirrors :func:`sei_reason` for the requirements member (Plainweave producer):

      * ``present`` -> earned ``clean`` (≥1 alive requirement bound);
      * ``absent``  -> ``unresolved_input`` (entity KNOWN to plainweave, none bound —
        a definitive "none here", with the recruiting fix to bind one or accept it);
      * ``unavailable`` -> ``unreachable`` (plainweave could NOT determine requirements
        for one or more entities — identity not resolvable locally — never "no
        requirements"). This is the live explanation for a reachable producer that
        returned per-entity ``unavailable``; a member with NO transport (disabled) or a
        transport that raised carries its OWN federation weft-reason instead.

    Raises ValueError for any value outside the closed vocab so a caller never attaches
    a triple it cannot explain. Reuses the canonical 11 — no new reason_class. The
    static :func:`requirements_reason` (``disabled``) remains the not-consulted/unwired
    fallback.
    """

    if req_state == "present":
        return reason("clean")
    if req_state == "absent":
        return reason(
            "unresolved_input",
            cause=(
                "plainweave knows the entity but no requirement is bound to it "
                "(a definitive none-here, not an unknown)"
            ),
            fix=(
                "bind a requirement to this entity in plainweave (a satisfies/verifies "
                "trace), or accept it as honestly unbound; until then requirements is "
                "absent, not an earned-empty clean"
            ),
        )
    if req_state == "unavailable":
        return reason(
            "unreachable",
            cause=(
                "plainweave could not determine requirements for one or more affected "
                "entities (identity not resolvable locally — never 'no requirements')"
            ),
            fix=(
                "run `loomweave analyze <repo>` so the entity gets a stable SEI plainweave "
                "can resolve (or confirm plainweave's catalog is in sync), then re-query"
            ),
        )
    raise ValueError(
        f"req_state {req_state!r} is outside the closed enrichment.requirements vocab "
        "(present|absent|unavailable)"
    )


def sei_reason(sei_state: str) -> dict[str, Any]:
    """Map a closed ``enrichment.sei`` scalar to its explanatory weft-reason triple.

    ``present`` is an earned ``clean``; ``absent`` (peer present, the changed
    locator never resolved to an SEI) is ``unresolved_input``; ``unavailable``
    (the Loomweave SEI authority was unreachable, e.g. mid-capture) is
    ``unreachable``. Raises ValueError for any value outside the closed vocab so a
    caller never attaches a triple it cannot explain (and so the call sites need no
    narrowing assert). Reuses the canonical 11 — no new reason_class.
    """

    if sei_state == "present":
        return reason("clean")
    if sei_state == "absent":
        return reason(
            "unresolved_input",
            cause=(
                "the changed entity's locator never resolved to a Loomweave SEI "
                "(peer present, no stable-entity-identity for this locator yet)"
            ),
            fix=(
                "run `loomweave analyze <repo>` so the locator gets a stable SEI, then re-query; "
                "until then sei is honestly absent, not an earned-empty"
            ),
        )
    if sei_state == "unavailable":
        return reason(
            "unreachable",
            cause=(
                "the Loomweave SEI authority was unreachable, so SEI resolution could not be "
                "attempted (peer down — never an implied clean/resolved state)"
            ),
            fix=(
                "confirm `loomweave serve` is reachable (or the loomweave CLI is on PATH), then "
                "recapture/re-query so SEIs can be resolved"
            ),
        )
    raise ValueError(
        f"sei_state {sei_state!r} is outside the closed enrichment.sei vocab "
        "(present|absent|unavailable)"
    )
