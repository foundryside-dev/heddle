"""Risk-as-verification consumer of a wardline-attest-2 bundle (Rung 2) — pure.

This is warpline's consumer of wardline's ``wardline-attest-2`` evidence bundle.
It closes the ``verification_source_absent`` gap that D1's completeness consumer
left open: an impact-complete worklist whose every entity is *attested clean at
its current body* can finally read **proven-good**, instead of merely "not
partial".

Posture (mirrors ``_completeness`` / ``verification``): pure, enrich-only — it
imports only ``typing`` + ``warpline.listing.reason`` + ``warpline._completeness``;
no store, no git, no I/O. The current commit and the per-SEI current content_hash
are INJECTED (a ``content_hash_for_sei`` callable), so the equality logic is
testable without a live loomweave.

The check is MECHANICAL, exactly as the contract names it:

  * the bundle is a PUSHED, UNTRUSTED payload — its HMAC signature is NOT verified
    (warpline does not hold wardline's shared project key; see the attest threat
    model). A proven-good verdict is therefore an *echo of wardline's authority,
    mechanically confirmed current*, NOT a warpline-minted "clean" and NOT a
    cryptographic proof. This ceiling is stated in every proven verdict
    (``signature_verified: false``, ``authority: "wardline"``).
  * per affected entity (keyed on SEI): the matching bundle boundary must carry a
    ``"clean"`` verdict AND its ``content_hash`` must equal the entity's CURRENT
    content_hash (entity-body equality — both sides read loomweave's per-entity
    hash, confirmed byte-identical), AND the bundle's ``commit`` must equal the
    worklist's commit AND not be ``dirty`` (so the commit truthfully pins).

Honesty edges (every one degrades to ``unavailable`` with a machine reason, NEVER
silent-clean): a missing bundle, an unknown schema, a dirty tree, a null commit,
``sei_source: "unavailable"`` (nothing keyable), a null per-boundary sei /
content_hash, a non-``clean`` verdict, or ANY affected entity left unmatched
(all-or-nothing — one miss sinks the whole worklist's proven-good).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from warpline._completeness import completeness_risk
from warpline.listing import reason

ATTEST_SCHEMA = "wardline-attest-2"
# The wardline boundary verdict vocab is three-valued (defect|clean|unknown); only
# "clean" is proven-good. "unknown" is fail-closed (under-scanned), NEVER clean.
_CLEAN_VERDICT = "clean"

# Closed machine-code vocabulary for the risk-as-verification verdict.
ATTEST_RISK_CODES = frozenset(
    {
        "attested_clean",  # PROVEN: every affected entity attested clean at current body
        "verification_source_absent",  # complete, but no attest bundle supplied
        "attestation_schema_unknown",  # bundle is not wardline-attest-2
        "attestation_dirty",  # bundle attested a dirty tree — commit does not pin
        "attestation_no_commit",  # bundle commit is null (non-git) — cannot pin
        "attestation_commit_mismatch",  # bundle commit != the worklist's commit
        "attestation_unkeyed",  # sei_source unavailable — no boundary is SEI-keyed
        "attestation_incomplete",  # >=1 affected entity not attested-clean-at-current-body
    }
)


class AttestBundleError(ValueError):
    """A bundle that is structurally unusable (not a dict / no payload)."""


def parse_attest_bundle(bundle: Any) -> dict[str, Any]:
    """Normalize a wardline-attest-2 bundle into ``{schema, commit, dirty,
    sei_source, by_sei}`` where ``by_sei`` maps each SEI-carrying boundary's sei
    to its boundary dict. Raises :class:`AttestBundleError` on a structurally
    unusable bundle; an UNKNOWN schema is NOT raised here (it is an honest
    ``attestation_schema_unknown`` verdict downstream)."""

    if not isinstance(bundle, dict):
        raise AttestBundleError("attestation bundle must be a JSON object")
    payload = bundle.get("payload")
    if not isinstance(payload, dict):
        raise AttestBundleError("attestation bundle payload must be a JSON object")
    boundaries = payload.get("boundaries")
    by_sei: dict[str, dict[str, Any]] = {}
    if isinstance(boundaries, list):
        for b in boundaries:
            if isinstance(b, dict):
                sei = b.get("sei")
                if isinstance(sei, str) and sei:
                    by_sei[sei] = b
    return {
        "schema": bundle.get("schema"),
        "commit": payload.get("commit"),
        "dirty": payload.get("dirty"),
        "sei_source": payload.get("sei_source"),
        "by_sei": by_sei,
    }


def _entity_attested(
    boundary: dict[str, Any] | None,
    *,
    current_content_hash: str | None,
) -> bool:
    """Mechanical per-entity equality: a matching boundary with a ``clean`` verdict
    whose ``content_hash`` equals the entity's current content_hash. A null
    boundary / sei / content_hash, or a non-clean verdict, is NOT attested."""

    if boundary is None:
        return False
    if boundary.get("verdict") != _CLEAN_VERDICT:
        return False
    attested_hash = boundary.get("content_hash")
    if not isinstance(attested_hash, str) or not attested_hash:
        return False
    if not isinstance(current_content_hash, str) or not current_content_hash:
        return False
    return attested_hash == current_content_hash


def _unavailable(reason_code: str, *, cause: str, fix: str) -> dict[str, Any]:
    return {
        "risk": "unavailable",
        "reason_code": reason_code,
        "reason": reason("disabled", cause=cause, fix=fix),
    }


def worklist_risk(
    impact_completeness: dict[str, Any] | None,
    *,
    affected_seis: list[str],
    bundle: Any = None,
    current_commit: str | None = None,
    content_hash_for_sei: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    """The full risk-as-verification verdict for a worklist.

    Layered on D1's completeness gate: a worklist whose impact set is not
    genuinely ``complete`` can NEVER read proven-good (you cannot prove a
    narrowed/partial scope good), so that case returns
    :func:`completeness_risk`'s ``unavailable`` verdict unchanged. Only on a
    ``complete`` worklist does the attest bundle decide:

      * no bundle           -> ``unavailable(verification_source_absent)`` (the gap)
      * bundle present, every affected entity attested-clean-at-current-body
                            -> ``proven`` (``attested_clean``) — echo of wardline
      * any honesty edge / unmatched entity
                            -> ``unavailable(<specific reason>)``

    ``affected_seis`` is every entity the worklist would have you re-verify; the
    proven-good verdict is ALL-OR-NOTHING across them. ``content_hash_for_sei``
    yields the entity's CURRENT content_hash (loomweave) or None when unresolvable.
    Never returns ``clean`` on warpline's own authority.
    """

    # 1. Completeness gate first (D1). Absent / partial / unknown can never be proven.
    if not isinstance(impact_completeness, dict) or impact_completeness.get("status") != "complete":
        return completeness_risk(impact_completeness)

    # 2. complete, but no attestation supplied -> the honest Rung-2 gap.
    if bundle is None:
        return _unavailable(
            "verification_source_absent",
            cause=(
                "impact completeness is 'complete', but no wardline-attest-2 bundle was "
                "supplied to prove the change good"
            ),
            fix=(
                "hand warpline a wardline-attest-2 bundle for this commit "
                "(`wardline attest . --out bundle.json`) so the change can read proven-good"
            ),
        )

    try:
        parsed = parse_attest_bundle(bundle)
    except AttestBundleError as exc:
        return _unavailable(
            "attestation_schema_unknown",
            cause=f"the supplied attestation bundle is structurally unusable: {exc}",
            fix="supply a well-formed wardline-attest-2 bundle",
        )

    # 3. Bundle-level honesty edges — each blocks a proven-good verdict.
    if parsed["schema"] != ATTEST_SCHEMA:
        return _unavailable(
            "attestation_schema_unknown",
            cause=f"attestation schema is {parsed['schema']!r}, not {ATTEST_SCHEMA!r}",
            fix=f"supply a {ATTEST_SCHEMA} bundle (a newer/older attest schema is not honored)",
        )
    if parsed["dirty"] is not False:
        return _unavailable(
            "attestation_dirty",
            cause=(
                "the attestation did not explicitly report dirty=false, so its commit does "
                "not truthfully pin the attested source"
            ),
            fix="re-attest a clean (committed) tree so the bundle records dirty=false",
        )
    if not isinstance(parsed["commit"], str) or not parsed["commit"]:
        return _unavailable(
            "attestation_no_commit",
            cause="the attestation has no commit (non-git tree), so it cannot pin a source",
            fix="attest a committed git tree so the bundle records a pinning commit",
        )
    if current_commit is not None and parsed["commit"] != current_commit:
        return _unavailable(
            "attestation_commit_mismatch",
            cause=f"the attestation pins commit {str(parsed['commit'])[:8]}, not the worklist's "
            f"commit {str(current_commit)[:8]}",
            fix="attest the same commit the worklist describes, then re-consult",
        )
    if parsed["sei_source"] == "unavailable":
        return _unavailable(
            "attestation_unkeyed",
            cause="the attestation resolved no SEIs (sei_source='unavailable'), so no boundary "
            "is keyable to an affected entity",
            fix="build the attestation with loomweave wired (--loomweave-url) so boundaries "
            "carry SEIs",
        )

    # 4. Per-entity mechanical match. ALL-OR-NOTHING across the worklist.
    #
    # An EMPTY affected set cannot be proven: the all-or-nothing loop below is
    # vacuously satisfied (zero unmatched), but no affected entity was actually
    # attested. A complete worklist with no SEI-keyed entity (e.g. an install /
    # backfill run while loomweave was unavailable) is UNKEYED, not proven-good —
    # fail closed rather than mint a vacuous proven verdict with matched/affected 0.
    if not affected_seis:
        return _unavailable(
            "attestation_unkeyed",
            cause="the worklist's impact set carries no SEI-keyed entity, so no affected "
            "entity can be matched against the attestation (an unkeyed/backfill worklist "
            "cannot be proven good)",
            fix="re-index with loomweave wired so the worklist's entities carry SEIs, then "
            "re-consult — an empty/unkeyed affected set is never proven-good",
        )

    chash = content_hash_for_sei or (lambda _sei: None)
    by_sei = parsed["by_sei"]
    unmatched: list[str] = []
    for sei in affected_seis:
        if not _entity_attested(by_sei.get(sei), current_content_hash=chash(sei)):
            unmatched.append(sei)

    if unmatched:
        shown = ", ".join(unmatched[:5]) + (" …" if len(unmatched) > 5 else "")
        return _unavailable(
            "attestation_incomplete",
            cause=f"{len(unmatched)}/{len(affected_seis)} affected entit"
            f"{'y is' if len(unmatched) == 1 else 'ies are'} not attested clean at their "
            f"current body (missing boundary, non-clean verdict, or content_hash drift): {shown}",
            fix="re-run wardline's gate and re-attest at this commit so every affected entity "
            "carries a clean, body-matching attestation",
        )

    # 5. PROVEN-GOOD. An echo of wardline's clean attestation, mechanically confirmed
    #    current — NOT a warpline-minted clean, and the HMAC is NOT verified here.
    return {
        "risk": "proven",
        "reason_code": "attested_clean",
        "authority": "wardline",
        "source": ATTEST_SCHEMA,
        "signature_verified": False,
        "basis": "mechanical (commit, content_hash) equality vs wardline's attestation; "
        "HMAC signature NOT verified by warpline",
        "commit": parsed["commit"],
        "matched": len(affected_seis),
        "affected": len(affected_seis),
        "reason": reason("clean"),
    }
