"""PlainweaveRequirementsClient — warpline's read-only consumer of
``weft.plainweave.requirements_enrichment.v1``.

The client invokes ``plainweave requirements-enrichment <refs...> --json``
(mirroring ``WardlineDossierClient`` over ``wardline dossier`` and
``LegisGovernanceClient`` over ``legis governance-read``) and maps the producer
envelope onto the ``RequirementsClient`` Protocol:

  * ok=True            -> index ``data.items`` by ``entity_ref`` (an empty list is
    an earned-empty, returned as ``{}``)
  * ok!=True / nonzero exit / unparseable / shape-mismatch -> raise
    ``PlainweaveRequirementsUnavailable`` (so ``_consult_plainweave`` reports
    ``unreachable``, never a confident-empty).

The producer is ``local_only:true, live_peer_calls:false``; this one CLI hop is
warpline's only call and never mutates plainweave state. Requirement item bodies
are treated as OPAQUE (passed through, never minted or parsed).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from warpline.federation import (
    PlainweaveRequirementsClient,
    PlainweaveRequirementsUnavailable,
    RequirementsClient,
)

_SEI = "loomweave:eid:public00000000000000000000000000"
_ITEM = {
    "entity_ref": _SEI,
    "status": "present",
    "requirements": [
        {
            "requirement_id": "req-1",
            "stable_id": "plainweave:req:AUTH:0001",
            "version": 1,
            "type": "functional",
            "criticality": "medium",
            "binding": {"relation": "satisfies", "actor_kind": "human", "freshness": "current"},
        }
    ],
    "reason": None,
    "freshness": "current",
}


def _envelope(items: list[dict[str, Any]]) -> dict[str, Any]:
    """A producer-shaped CLI envelope: items ride under ``data`` (NOT top-level)."""
    present = sum(1 for it in items if it["status"] == "present")
    absent = sum(1 for it in items if it["status"] == "absent")
    unavailable = sum(1 for it in items if it["status"] == "unavailable")
    return {
        "schema": "weft.plainweave.requirements_enrichment.v1",
        "ok": True,
        "data": {
            "items": items,
            "summary": {"present": present, "absent": absent, "unavailable": unavailable},
            "authority_boundary": {
                "local_only": True,
                "live_peer_calls": False,
                "governance_verdicts": False,
                "requirements_owner": "plainweave",
            },
        },
        "warnings": [],
        "meta": {"producer": {"tool": "plainweave", "version": "1.1.0"}},
    }


class _FakeProc:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def _patch(monkeypatch, fake_run) -> None:
    monkeypatch.setattr("warpline.federation.subprocess.run", fake_run)


# --- the Protocol is satisfied ------------------------------------------------
def test_client_satisfies_requirements_client_protocol() -> None:
    client: RequirementsClient = PlainweaveRequirementsClient(Path("/repo"))
    assert callable(client.requirements_for_refs)


def test_invokes_requirements_enrichment_with_json_flag_and_all_refs(monkeypatch) -> None:
    # plainweave's CLI is `plainweave requirements-enrichment <refs...> --json`;
    # entity_ref is nargs="+", so ALL refs ride in ONE subprocess call (cheaper than
    # per-SEI). Pin the exact argv so the invocation form can never drift.
    seen: dict[str, Any] = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        seen["cwd"] = kw.get("cwd")
        return _FakeProc(stdout=json.dumps(_envelope([_ITEM])))

    _patch(monkeypatch, fake_run)
    PlainweaveRequirementsClient(Path("/repo"), command="plainweave").requirements_for_refs(
        [_SEI, "loomweave:eid:other0000000000000000000000000"]
    )
    assert seen["cmd"] == [
        "plainweave",
        "requirements-enrichment",
        _SEI,
        "loomweave:eid:other0000000000000000000000000",
        "--json",
    ]
    assert seen["cwd"] == Path("/repo")


def test_indexes_items_by_entity_ref(monkeypatch) -> None:
    _patch(monkeypatch, lambda cmd, **kw: _FakeProc(stdout=json.dumps(_envelope([_ITEM]))))
    out = PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs([_SEI])
    assert set(out) == {_SEI}
    # the item body is passed through OPAQUELY (not re-minted)
    assert out[_SEI] is not _ITEM  # round-tripped through JSON
    assert out[_SEI]["status"] == "present"
    assert out[_SEI]["requirements"][0]["stable_id"] == "plainweave:req:AUTH:0001"


def test_empty_refs_makes_no_subprocess_call(monkeypatch) -> None:
    def boom(cmd, **kw):
        raise AssertionError("no subprocess call for an empty ref list")

    _patch(monkeypatch, boom)
    assert PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs([]) == {}


def test_ok_false_raises_unavailable(monkeypatch) -> None:
    payload = {"schema": "weft.plainweave.requirements_enrichment.v1", "ok": False, "error": "boom"}
    _patch(monkeypatch, lambda cmd, **kw: _FakeProc(stdout=json.dumps(payload)))
    with pytest.raises(PlainweaveRequirementsUnavailable):
        PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs([_SEI])


def test_nonzero_exit_raises_unavailable(monkeypatch) -> None:
    def fake_run(cmd, **kw):
        raise subprocess.CalledProcessError(returncode=2, cmd=cmd)

    _patch(monkeypatch, fake_run)
    with pytest.raises(PlainweaveRequirementsUnavailable):
        PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs([_SEI])


def test_missing_binary_raises_unavailable(monkeypatch) -> None:
    def fake_run(cmd, **kw):
        raise FileNotFoundError("plainweave not on PATH")

    _patch(monkeypatch, fake_run)
    with pytest.raises(PlainweaveRequirementsUnavailable):
        PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs([_SEI])


def test_unparseable_output_raises_unavailable(monkeypatch) -> None:
    _patch(monkeypatch, lambda cmd, **kw: _FakeProc(stdout="not json {"))
    with pytest.raises(PlainweaveRequirementsUnavailable):
        PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs([_SEI])


def test_missing_data_section_raises_unavailable(monkeypatch) -> None:
    payload = {"schema": "weft.plainweave.requirements_enrichment.v1", "ok": True}
    _patch(monkeypatch, lambda cmd, **kw: _FakeProc(stdout=json.dumps(payload)))
    with pytest.raises(PlainweaveRequirementsUnavailable):
        PlainweaveRequirementsClient(Path("/repo")).requirements_for_refs([_SEI])


# --- the capability probe -----------------------------------------------------
def test_available_true_when_verb_advertised(monkeypatch) -> None:
    help_text = "usage: plainweave ... {req,trace,requirements-enrichment,web} ..."
    _patch(monkeypatch, lambda cmd, **kw: _FakeProc(stdout=help_text))
    assert PlainweaveRequirementsClient.available(Path("/repo")) is True


def test_available_false_when_verb_absent(monkeypatch) -> None:
    _patch(monkeypatch, lambda cmd, **kw: _FakeProc(stdout="usage: plainweave ... {req,trace,web}"))
    assert PlainweaveRequirementsClient.available(Path("/repo")) is False


def test_available_false_when_binary_missing(monkeypatch) -> None:
    def fake_run(cmd, **kw):
        raise FileNotFoundError("plainweave not on PATH")

    _patch(monkeypatch, fake_run)
    assert PlainweaveRequirementsClient.available(Path("/repo")) is False
