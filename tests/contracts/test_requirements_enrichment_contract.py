"""weft.plainweave.requirements_enrichment.v1 — warpline's consumer contract.

plainweave OWNS this contract; warpline vendors plainweave's frozen producer golden
(``requirements-enrichment.golden.json``) and pins the SHAPE IT CONSUMES against it.

STRUCTURE/STATUS-pinned, deliberately NOT byte-pinned: the requirement ITEM schema is
proposed-but-unratified (sibling interface-lock prompt #3), and warpline consumes the
item bodies OPAQUELY (it surfaces them, never parses internals). Asserting item
internals now would force a re-freeze on every pre-ratification tweak — and would couple
warpline to a shape it deliberately does not interpret. When the item schema is ratified,
convert this to a byte-pin mirroring ``legis-governance-read.golden.json`` (the two-layer
pattern in ``test_governance_read_schema.py``).

Three guards:
  1. the vendored golden satisfies the STATUS SEMANTICS warpline relies on
     (present/absent/unavailable distinct; the no-silent-clean distinction);
  2. the REAL consumer (``PlainweaveRequirementsClient``) parses the golden — wrapped in
     the producer's CLI envelope — into ``{entity_ref: item}``, agreeing on the status
     set and item keys (item-shape round-trip across all three statuses);
  3. the consumer parses a REAL, vendored ``plainweave requirements-enrichment --json``
     CLI envelope (``requirements-enrichment.cli-envelope.golden.json``, captured verbatim
     from the producer) — pinning the ENVELOPE WRAPPER itself (top-level ``ok`` + ``data``,
     items under ``data.items``), the load-bearing part of the consumed shape that guard 2
     cannot pin because it hand-builds the wrapper. This is the interface-agreement guard:
     it fails loud if plainweave's emitted wrapper and warpline's consumed shape diverge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from warpline.federation import PlainweaveRequirementsClient

_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN_PATH = _ROOT / "fixtures" / "contracts" / "warpline" / "requirements-enrichment.golden.json"
_FIXTURES = _ROOT / "fixtures" / "contracts" / "warpline"
_CLI_ENVELOPE_PATH = _FIXTURES / "requirements-enrichment.cli-envelope.golden.json"

# warpline's OWN mirror of the status/key vocab it consumes (not imported from plainweave's
# test tree — the consumer pins its own expectations).
_STATUSES = {"present", "absent", "unavailable"}
_DATA_KEYS = {"items", "summary", "authority_boundary"}
_ITEM_KEYS = {"entity_ref", "status", "requirements", "reason", "freshness"}
_AUTHORITY_KEYS = {"local_only", "live_peer_calls", "governance_verdicts", "requirements_owner"}
_VERDICT_TOKENS = {
    "allow", "allowed", "block", "blocked", "deny", "denied", "approved", "rejected", "verdict",
}


def _golden() -> dict[str, Any]:
    return json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))


def _no_verdicts(node: Any) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            assert k.lower() not in _VERDICT_TOKENS, f"verdict-like key {k!r}"
            _no_verdicts(v)
    elif isinstance(node, list):
        for v in node:
            _no_verdicts(v)
    elif isinstance(node, str):
        assert node.strip().lower() not in _VERDICT_TOKENS, f"verdict-like value {node!r}"


# --- guard 1: status semantics --------------------------------------------------
def test_golden_carries_the_schema_id() -> None:
    assert _golden()["schema"] == "weft.plainweave.requirements_enrichment.v1"


def test_golden_data_sections_and_item_keys() -> None:
    data = {k: v for k, v in _golden().items() if k != "schema"}
    assert set(data) == _DATA_KEYS
    for item in data["items"]:
        assert set(item) == _ITEM_KEYS, f"item key drift: {sorted(item)}"
        assert item["status"] in _STATUSES


def test_golden_exercises_all_three_statuses() -> None:
    # the consumer contract must cover the FULL vocab — present, the earned-empty
    # absent, AND the could-not-determine unavailable (so the no-silent-clean
    # distinction is a tested shape, not a hypothesis).
    statuses = {item["status"] for item in _golden()["items"]}
    assert statuses == _STATUSES


def test_golden_present_carries_facts_absent_unavailable_carry_reasons() -> None:
    for item in _golden()["items"]:
        if item["status"] == "present":
            assert item["requirements"], "present must carry a non-empty requirements array"
            assert item["reason"] is None
        else:
            # absent AND unavailable are explicit, distinct, and never a silent clean.
            assert item["requirements"] == [], "non-present must carry an empty array"
            assert isinstance(item["reason"], str) and item["reason"]


def test_golden_summary_agrees_with_item_counts() -> None:
    items = _golden()["items"]
    counts = {s: sum(1 for it in items if it["status"] == s) for s in _STATUSES}
    assert _golden()["summary"] == counts


def test_golden_authority_boundary_is_local_only_no_verdicts() -> None:
    authority = _golden()["authority_boundary"]
    assert set(authority) == _AUTHORITY_KEYS
    assert authority["local_only"] is True
    assert authority["live_peer_calls"] is False
    assert authority["governance_verdicts"] is False
    assert authority["requirements_owner"] == "plainweave"


def test_golden_carries_no_verdict_tokens() -> None:
    _no_verdicts(_golden())


# --- guard 2: the real consumer round-trips the golden --------------------------
class _FakeProc:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = 0


def test_consumer_parses_the_producer_golden(monkeypatch) -> None:
    """The interface-agreement guard: wrap the vendored golden in the producer's CLI
    envelope (items ride under ``data``) and confirm the REAL consumer extracts every
    item by ``entity_ref`` and agrees on the status set + item keys. Fails loud if
    plainweave's emitted shape and warpline's consumed shape ever diverge."""

    golden = _golden()
    data = {k: v for k, v in golden.items() if k != "schema"}
    envelope = {
        "schema": golden["schema"],
        "ok": True,
        "data": data,
        "warnings": [],
        "meta": {"producer": {"tool": "plainweave", "version": "x"}},
    }
    monkeypatch.setattr(
        "warpline.federation.subprocess.run",
        lambda cmd, **kw: _FakeProc(json.dumps(envelope)),
    )
    refs = [item["entity_ref"] for item in data["items"]]
    parsed = PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs(refs)

    assert set(parsed) == set(refs)
    assert {item["status"] for item in parsed.values()} == {it["status"] for it in data["items"]}
    for item in parsed.values():
        assert set(item) == _ITEM_KEYS


def test_consumer_parses_a_real_captured_cli_envelope(monkeypatch) -> None:
    """Guard 3 — the WRAPPER guard. Feed a REAL, vendored ``plainweave
    requirements-enrichment --json`` envelope (captured verbatim from the producer) to the
    consumer WITHOUT re-shaping it. This pins the actual envelope wrapper (top-level ``ok``
    + ``data``, items under ``data.items``) — the one part of the consumed shape guard 2
    fabricates and therefore cannot detect drift in. Fails loud if plainweave renames/moves
    the wrapper out from under the consumer."""

    raw = _CLI_ENVELOPE_PATH.read_text(encoding="utf-8")
    captured = json.loads(raw)
    # sanity: this fixture really is a full CLI envelope (wrapper present), not a bare data
    # payload — otherwise the guard would silently degrade to guard 2.
    assert captured["ok"] is True
    assert "data" in captured and "items" in captured["data"]
    assert captured["schema"] == "weft.plainweave.requirements_enrichment.v1"

    monkeypatch.setattr(
        "warpline.federation.subprocess.run",
        lambda cmd, **kw: _FakeProc(raw),  # the verbatim captured bytes
    )
    refs = [item["entity_ref"] for item in captured["data"]["items"]]
    parsed = PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs(refs)

    assert set(parsed) == set(refs)
    for item in parsed.values():
        assert set(item) == _ITEM_KEYS
        assert item["status"] in _STATUSES
