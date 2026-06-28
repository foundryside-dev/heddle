"""Risk-as-verification consumer of a wardline-attest-2 bundle (Rung 2).

``_attest`` is pure: it maps (impact_completeness, affected SEIs, a PUSHED
attest-2 bundle, the current commit, an injected per-SEI content_hash) into a
risk-as-verification verdict. It closes D1's ``verification_source_absent`` gap —
a complete worklist whose every entity is attested clean at its current body
reads PROVEN-GOOD — while degrading to ``unavailable`` (never silent-clean) on
every honesty edge. The SEI + content_hash below are REAL loomweave values
(confirmed identical across loomweave's MCP surface and the HTTP identity
endpoint wardline's bundle-builder reads).
"""

from __future__ import annotations

from typing import Any

from warpline._attest import ATTEST_RISK_CODES, ATTEST_SCHEMA, worklist_risk
from warpline._completeness import COMPLETENESS_RISK_CODES

# Real loomweave values for warpline.reverify.render_reverify_worklist.
SEI_A = "loomweave:eid:9adc480cd5aa4d71503c19fd8b29907e"
HASH_A = "42f3670f4875735e840fe62a5efe2895a58ea2dd19e740b866e8be6af26208cc"
SEI_B = "loomweave:eid:00000000000000000000000000000bbb"
HASH_B = "bbbb670f4875735e840fe62a5efe2895a58ea2dd19e740b866e8be6af260bbbb"
COMMIT = "a5547265b157bf8bb6e9bc306fd611eb2ad8694d"

_COMPLETE = {"status": "complete", "reasons": []}
_PARTIAL = {"status": "partial", "reasons": ["depth_capped"]}


def _boundary(sei: str, content_hash: str | None, verdict: str = "clean") -> dict[str, Any]:
    return {
        "qualname": "warpline.x",
        "sei": sei,
        "content_hash": content_hash,
        "verdict": verdict,
        "tier": "INTEGRAL",
    }


def _bundle(
    *,
    boundaries: list[dict[str, Any]],
    commit: str | None = COMMIT,
    dirty: bool = False,
    sei_source: str = "loomweave",
    schema: str = ATTEST_SCHEMA,
) -> dict[str, Any]:
    return {
        "schema": schema,
        "payload": {
            "wardline_version": "1.0.7",
            "attested_at": "2026-06-27",
            "commit": commit,
            "dirty": dirty,
            "ruleset_hash": "sha256:deadbeef",
            "posture": {},
            "boundaries": boundaries,
            "sei_source": sei_source,
        },
        "signature": {"alg": "HMAC-SHA256", "value": "deadbeef", "key_id": "04e04fc4"},
    }


def _hashes(mapping: dict[str, str]):
    return lambda sei: mapping.get(sei)


def _risk(**kw):
    return worklist_risk(**kw)


# ------------------------------------------------------------------- PROVEN-GOOD
def test_complete_worklist_all_attested_reads_proven_good() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)]),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["risk"] == "proven"
    assert verdict["reason_code"] == "attested_clean"
    assert verdict["authority"] == "wardline"
    assert verdict["source"] == ATTEST_SCHEMA
    # the honest ceiling: warpline did NOT verify the HMAC; this is an echo.
    assert verdict["signature_verified"] is False
    assert verdict["matched"] == verdict["affected"] == 1
    # never a warpline-minted clean/allowed scalar
    assert verdict["risk"] not in {"clean", "allowed"}


def test_proven_good_requires_every_affected_entity_all_or_nothing() -> None:
    # SEI_A matches; SEI_B has no boundary -> the whole worklist is NOT proven.
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A, SEI_B],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)]),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A, SEI_B: HASH_B}),
    )
    assert verdict["risk"] == "unavailable"
    assert verdict["reason_code"] == "attestation_incomplete"


# ------------------------------------------------------------------- completeness gate first
def test_partial_completeness_can_never_be_proven_even_with_bundle() -> None:
    verdict = _risk(
        impact_completeness=_PARTIAL,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)]),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["risk"] == "unavailable"
    assert verdict["reason_code"] == "completeness_partial"


def test_absent_completeness_is_not_declared() -> None:
    verdict = _risk(impact_completeness=None, affected_seis=[], bundle=None)
    assert verdict["risk"] == "unavailable"
    assert verdict["reason_code"] == "completeness_not_declared"


# ------------------------------------------------------------------- the Rung-2 gap (no bundle)
def test_complete_without_bundle_is_verification_source_absent() -> None:
    verdict = _risk(impact_completeness=_COMPLETE, affected_seis=[SEI_A], bundle=None)
    assert verdict["risk"] == "unavailable"
    assert verdict["reason_code"] == "verification_source_absent"


# ------------------------------------------------------------------- honesty edges
def test_unknown_schema_is_rejected() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)], schema="wardline-attest-1"),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_schema_unknown"


def test_dirty_tree_attestation_refused() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)], dirty=True),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_dirty"


def test_missing_dirty_flag_is_not_treated_as_clean() -> None:
    bundle = _bundle(boundaries=[_boundary(SEI_A, HASH_A)])
    del bundle["payload"]["dirty"]

    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=bundle,
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )

    assert verdict["risk"] == "unavailable"
    assert verdict["reason_code"] == "attestation_dirty"


def test_null_commit_cannot_pin() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)], commit=None),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_no_commit"


def test_commit_mismatch_blocks_proven() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)], commit="0" * 40),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_commit_mismatch"


def test_sei_source_unavailable_is_unkeyed() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[], sei_source="unavailable"),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_unkeyed"


def test_empty_affected_set_with_valid_bundle_is_unkeyed_not_proven() -> None:
    # A complete worklist with NO SEI-keyed affected entity (e.g. an install /
    # backfill run while loomweave was unavailable) must NOT vacuously read
    # proven on the empty all-or-nothing loop. A syntactically valid, SEI-keyed
    # bundle is supplied, yet the worklist itself keys nothing → unavailable.
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)]),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["risk"] == "unavailable"
    assert verdict["reason_code"] == "attestation_unkeyed"
    # never the vacuous proven-good with matched/affected 0
    assert verdict["risk"] not in {"proven", "clean", "allowed"}


def test_content_hash_drift_is_not_proven() -> None:
    # boundary attests an OLD hash; the entity's current body moved -> not proven.
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, "old" + HASH_A[3:])]),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_incomplete"


def test_non_clean_verdict_is_not_proven() -> None:
    for bad in ("defect", "unknown"):
        verdict = _risk(
            impact_completeness=_COMPLETE,
            affected_seis=[SEI_A],
            bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A, verdict=bad)]),
            current_commit=COMMIT,
            content_hash_for_sei=_hashes({SEI_A: HASH_A}),
        )
        assert verdict["reason_code"] == "attestation_incomplete"


def test_null_content_hash_boundary_is_not_proven() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, None)]),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_incomplete"


def test_unresolvable_current_hash_is_not_proven() -> None:
    # loomweave could not give warpline the current content_hash -> cannot match.
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)]),
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({}),  # returns None for SEI_A
    )
    assert verdict["reason_code"] == "attestation_incomplete"


def test_structurally_unusable_bundle_is_schema_unknown() -> None:
    verdict = _risk(
        impact_completeness=_COMPLETE,
        affected_seis=[SEI_A],
        bundle="not-a-bundle",
        current_commit=COMMIT,
        content_hash_for_sei=_hashes({SEI_A: HASH_A}),
    )
    assert verdict["reason_code"] == "attestation_schema_unknown"


def test_all_reason_codes_are_in_the_closed_vocab() -> None:
    # exercise every branch once and assert the code is declared.
    seen = set()
    cases = [
        dict(impact_completeness=None, affected_seis=[], bundle=None),
        dict(impact_completeness=_PARTIAL, affected_seis=[], bundle=None),
        dict(impact_completeness=_COMPLETE, affected_seis=[SEI_A], bundle=None),
        dict(impact_completeness=_COMPLETE, affected_seis=[SEI_A],
             bundle=_bundle(boundaries=[_boundary(SEI_A, HASH_A)]), current_commit=COMMIT,
             content_hash_for_sei=_hashes({SEI_A: HASH_A})),
    ]
    for c in cases:
        seen.add(_risk(**c)["reason_code"])
    # worklist_risk's verdicts draw from its own attest vocab PLUS the completeness
    # codes it delegates to completeness_risk for a non-complete worklist.
    assert seen <= (ATTEST_RISK_CODES | COMPLETENESS_RISK_CODES)
