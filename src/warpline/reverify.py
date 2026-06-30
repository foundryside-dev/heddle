from __future__ import annotations

from collections.abc import Callable
from typing import Any

from warpline.listing import reason
from warpline.siblings import WorkClient, priority_from_work, work_enrichment_for_sei

_SUGGESTED_VERIFICATION = [
    {"kind": "test", "command": "run tests touching this entity if known"},
    {"kind": "inspection", "command": "inspect callers and behavior at this boundary"},
]


def _empty_enrichment() -> dict[str, list[Any]]:
    # advisory facts only; absence is explicit emptiness, never an implied
    # clean/allowed state (DECONFLICTION-FIRST).
    return {"work": [], "risk": [], "governance": [], "requirements": []}


def _default_verification() -> dict[str, Any]:
    """Honest default when no verification source is wired (advisory)."""

    return {
        "state": "unverified",
        "last_verified_at": None,
        "last_verified_commit": None,
        "decay": {"commits_behind": None},
        "reason": reason(
            "disabled",
            cause="no local verification source is configured for this worklist",
            fix=(
                "record a gate pass with `warpline verify-record --commit <sha> "
                "--kind test_pass`"
            ),
        ),
    }


def _echo_identity(
    entity: dict[str, Any], kid: int | None, frozen_loc: str | None, axis: str
) -> None:
    """Per-row identity echo (U2): the frozen ``locator`` paired with ``kid`` at
    the call site must match the locator of the row it now sits beside.

    A mismatch means an equal-length ORDER drift permuted one of the parallel
    axes (the verification key id and the entity row) but not the other — so the
    verification-freshness block ``kid`` resolves to would attach to the WRONG
    entity. That is a silent wrong answer the call-site length guard cannot
    catch, so we raise LOUDLY. NO-OP on correctly-ordered input (locators match);
    skipped when no key id / no frozen locator is supplied (nothing to echo).
    """

    if kid is None or frozen_loc is None:
        return
    live_loc = entity.get("locator")
    if live_loc != frozen_loc:
        raise ValueError(
            "reverify identity echo failed: verification key id was derived from "
            f"locator {frozen_loc!r} but now sits beside entity {live_loc!r} on the "
            f"{axis} axis — an equal-length order drift permuted one of the parallel "
            "verification axes, which would silently attach the wrong verification "
            "block to the wrong entity"
        )


def render_reverify_worklist(
    *,
    changed: list[dict[str, Any]],
    affected: list[dict[str, Any]],
    completeness: str,
    staleness: dict[str, Any],
    work_client: WorkClient | None = None,
    changed_key_ids: list[tuple[int | None, str | None]] | None = None,
    affected_key_ids: list[tuple[int | None, str | None]] | None = None,
    verification_for: Callable[[int | None], dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]]]:
    """Render the frozen reverify worklist items.

    Returns ``(items, work_seen, filigree_candidates)``. The changed entities are
    always present (reason ``changed``) so a solo/NO_SNAPSHOT worklist is still
    non-empty; downstream entities are added when a snapshot exists.

    ``verification_for`` (advisory, Rung 2 Track B) maps an ``entity_key_id`` to
    its verification-freshness block. ``changed_key_ids`` / ``affected_key_ids``
    are ``(entity_key_id, locator)`` pairs aligned 1:1 with ``changed`` /
    ``affected`` so the block can be attached without threading the internal key
    id into the FROZEN ``{locator, sei}`` entity view.

    U2 per-row identity ECHO: each pair's ``locator`` is the SEI-orthogonal
    identity (frozen at the call site, from the entity the key id was derived
    from) of the row it must align with. Before attaching the verification block
    we echo the row's OWN live ``locator`` against the frozen one; a mismatch
    means an equal-length ORDER drift permuted one axis but not the other — a
    silent wrong answer the call-site length guard cannot catch — so we raise
    LOUDLY instead. The echo is a NO-OP on every correctly-ordered input (the
    locators match by construction) and is skipped when no pairing is supplied
    (``None`` pairs) or when the row carries no key id / no locator to echo.
    When ``verification_for`` is None the block defaults to an honest
    ``unverified`` (no source configured).
    """

    cpairs = changed_key_ids or [(None, None)] * len(changed)
    apairs = affected_key_ids or [(None, None)] * len(affected)
    rows: list[tuple[dict[str, Any], str, int, list[Any], int | None]] = []
    for entry, (kid, frozen_loc) in zip(changed, cpairs, strict=True):
        entity = entry.get("entity", {})
        _echo_identity(entity, kid, frozen_loc, "changed")
        rows.append((entity, "changed", 0, [], kid))
    for entry, (kid, frozen_loc) in zip(affected, apairs, strict=True):
        entity = entry.get("entity", {})
        _echo_identity(entity, kid, frozen_loc, "downstream")
        rows.append(
            (
                entity,
                "downstream",
                entry.get("depth", 1),
                entry.get("via_edges", []),
                kid,
            )
        )

    items: list[dict[str, Any]] = []
    work_seen = False
    candidates: list[dict[str, Any]] = []
    for entity, reason_str, depth, why, kid in rows:
        enrichment = _empty_enrichment()
        priority = "unknown"
        sei = entity.get("sei")
        if work_client is not None and isinstance(sei, str) and sei:
            work_items = work_enrichment_for_sei(work_client, sei)
            if work_items:
                work_seen = True
                enrichment["work"] = work_items
                priority = priority_from_work(work_items)
                for work_item in work_items:
                    candidates.append(
                        {
                            "proposed_action": "review_linked_issue",
                            "issue_id": work_item.get("issue_id"),
                            "entity": entity,
                        }
                    )
        verification = (
            verification_for(kid) if verification_for is not None else _default_verification()
        )
        items.append(
            {
                "entity": entity,
                "priority": priority,
                "reason": reason_str,
                "depth": depth,
                "why": why,
                "suggested_verification": _SUGGESTED_VERIFICATION,
                "enrichment": enrichment,
                "verification": verification,
            }
        )
    return items, work_seen, candidates
