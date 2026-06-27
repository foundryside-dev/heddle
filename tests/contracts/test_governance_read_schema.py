"""legis governance_read.v1 — warpline's mirrored consumer contract.

legis OWNS this contract; warpline mirrors it at
``contracts/governance_read.v1.schema.json`` as the source of truth for its
advisory ``LegisGovernanceClient``. These vectors are the contract's CANONICAL
LITERAL SAMPLES (from the legis-authored spec) — NOT a live capture: at the time
of writing the installed legis exposes no ``governance-read`` verb yet, so there
is no running surface to capture from. They validate the mirrored schema is a
faithful, well-formed copy of what the consumer will parse.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = _ROOT / "contracts" / "governance_read.v1.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate(instance: dict) -> None:
    jsonschema.validate(instance=instance, schema=_schema())


def _rejects(instance: dict) -> None:
    with pytest.raises(jsonschema.ValidationError):
        _validate(instance)


# --- canonical contract samples (legis-authored; not a live capture) ----------
CHECKED_WITH_CLEARANCES = {
    "status": "checked",
    "sei": "loomweave:eid:7Q3fc1",
    "records": [
        {
            "sei": "loomweave:eid:7Q3fc1",
            "disposition": "cleared",
            "posture": "protected_override",
            "authority": "operator",
            "as_of": "2026-06-27T14:02:11Z",
            "reasons": ["operator_override"],
            "content_hash": "b3:9f2ce7",
        },
        {
            "sei": "loomweave:eid:7Q3fc1",
            "disposition": "cleared",
            "posture": "operator_signoff",
            "authority": "operator",
            "as_of": "2026-06-26T09:41:55+00:00",
            "reasons": ["signoff_cleared"],
            "content_hash": "b3:5a1092",
        },
    ],
}
CHECKED_EMPTY = {"status": "checked", "sei": "loomweave:eid:unknown", "records": []}
UNAVAILABLE = {
    "status": "unavailable",
    "sei": "loomweave:eid:7Q3fc1",
    "records": [],
    "unavailable": [{"reason": "trail not signature-verifiable (no protected gate / verifier)"}],
}


def test_schema_is_wellformed_draft_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(_schema())


def test_canonical_samples_validate() -> None:
    _validate(CHECKED_WITH_CLEARANCES)
    _validate(CHECKED_EMPTY)  # earned-empty: no verified clearance, NOT "ungoverned"
    _validate(UNAVAILABLE)


def test_both_postures_and_reason_codes_round_trip() -> None:
    postures = {r["posture"] for r in CHECKED_WITH_CLEARANCES["records"]}
    reasons = {c for r in CHECKED_WITH_CLEARANCES["records"] for c in r["reasons"]}
    assert postures == {"protected_override", "operator_signoff"}
    assert reasons == {"operator_override", "signoff_cleared"}


# --- rejections: the schema must be tight, not permissive ---------------------
def test_rejects_record_missing_content_hash() -> None:
    bad = json.loads(json.dumps(CHECKED_WITH_CLEARANCES))
    del bad["records"][0]["content_hash"]
    _rejects(bad)


def test_rejects_non_cleared_disposition() -> None:
    # A BLOCKED/pending record has no place in v1 (cleared-only); the schema
    # enforces the cleared-only scope so a future drift cannot smuggle in-flight
    # governance through this channel without a v2 bump.
    bad = json.loads(json.dumps(CHECKED_WITH_CLEARANCES))
    bad["records"][0]["disposition"] = "blocked"
    _rejects(bad)


def test_rejects_status_outside_enum() -> None:
    _rejects({"status": "cleared", "sei": "loomweave:eid:x", "records": []})


def test_rejects_unknown_posture() -> None:
    bad = json.loads(json.dumps(CHECKED_WITH_CLEARANCES))
    bad["records"][0]["posture"] = "structured"
    _rejects(bad)


def test_rejects_empty_reasons() -> None:
    bad = json.loads(json.dumps(CHECKED_WITH_CLEARANCES))
    bad["records"][0]["reasons"] = []
    _rejects(bad)


def test_rejects_unknown_top_level_key() -> None:
    bad = json.loads(json.dumps(CHECKED_EMPTY))
    bad["verdict"] = "allow"  # no verdict leaks through a governance READ
    _rejects(bad)


# --- discriminated union (legis hardened the contract; backward-compatible) ----
# These pin the status<->shape coupling the `allOf` enforces, so warpline's
# consumer validates with EXACTLY the tightness legis emits — an 'unavailable'
# that could masquerade as a clean/empty 'checked' is the false-green this kills.
def test_rejects_checked_carrying_an_unavailable_key() -> None:
    # status 'checked' MUST NOT carry the unavailable reasons array.
    _rejects({"status": "checked", "sei": "loomweave:eid:x", "records": [],
              "unavailable": [{"reason": "leaked"}]})


def test_rejects_unavailable_missing_its_reasons() -> None:
    # status 'unavailable' REQUIRES the unavailable array.
    _rejects({"status": "unavailable", "sei": "loomweave:eid:x", "records": []})


def test_rejects_unavailable_with_empty_reasons() -> None:
    # the unavailable array must be non-empty (minItems: 1) — never a silent empty.
    _rejects({"status": "unavailable", "sei": "loomweave:eid:x", "records": [],
              "unavailable": []})


def test_rejects_unavailable_with_a_blank_reason_string() -> None:
    _rejects({"status": "unavailable", "sei": "loomweave:eid:x", "records": [],
              "unavailable": [{"reason": ""}]})


def test_rejects_unavailable_carrying_records() -> None:
    # 'unavailable' must carry [] records (maxItems: 0) — no clearance rides an
    # unverifiable answer.
    bad = json.loads(json.dumps(UNAVAILABLE))
    bad["records"] = CHECKED_WITH_CLEARANCES["records"]
    _rejects(bad)
