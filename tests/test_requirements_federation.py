"""requirements — Plainweave as the 4th federation member (the one warpline never wired).

Plainweave OWNS ``weft.plainweave.requirements_enrichment.v1``; warpline consults it
READ-ONLY through ``PlainweaveRequirementsClient`` and surfaces honest per-entity
requirement facts + a real ``enrichment.requirements`` scalar, replacing the reserved
``disabled`` default.

These pin, mirroring the legis member:

  1. ``plainweave`` is in ``FEDERATION_MEMBERS`` and the federation block on EVERY
     federated run (``disabled`` when unwired, never silently dropped).
  2. status pass-through: ``present`` -> facts + scalar ``present``/``clean``; reachable
     all-``absent`` -> scalar ``absent``/``unresolved_input`` (earned-empty);
     reachable all-``unavailable`` -> scalar ``unavailable`` (NEVER collapsed to absent);
     transport raised -> ``unreachable``.
  3. advisory, never gates: flipping the requirements facts never moves the decision.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from warpline import commands
from warpline._enrichment import requirements_reason, requirements_reason_for
from warpline.federation import (
    FEDERATION_MEMBERS,
    consult_federation,
    federation_transport_blockers,
)
from warpline.store import WarplineStore, default_store_path


# --------------------------------------------------------------------------- fakes
def _present(ref: str) -> dict[str, Any]:
    return {
        "entity_ref": ref,
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


def _absent(ref: str) -> dict[str, Any]:
    return {
        "entity_ref": ref,
        "status": "absent",
        "requirements": [],
        "reason": "Entity resolves locally but no requirement is bound to it.",
        "freshness": "unavailable",
    }


def _unavailable(ref: str) -> dict[str, Any]:
    return {
        "entity_ref": ref,
        "status": "unavailable",
        "requirements": [],
        "reason": "Entity identity is not resolvable locally; cannot determine requirements.",
        "freshness": "unavailable",
    }


class _FakeReq:
    """A RequirementsClient stand-in: returns canned items for known refs."""

    def __init__(self, by_ref: dict[str, dict[str, Any]]) -> None:
        self._by_ref = by_ref

    def requirements_for_refs(self, refs: list[str]) -> dict[str, dict[str, Any]]:
        return {r: self._by_ref[r] for r in refs if r in self._by_ref}


class _BoomReq:
    """A RequirementsClient whose transport raises mid-consult (unreachable)."""

    def requirements_for_refs(self, refs: list[str]) -> dict[str, dict[str, Any]]:
        raise RuntimeError("plainweave requirements-enrichment exploded")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def _seed(tmp_path: Path, locators: list[str]) -> tuple[Path, list[int], list[str]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "agent@example.test")
    _git(repo, "config", "user.name", "Agent")
    (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-m", "init")
    head = _git(repo, "rev-parse", "HEAD")
    keys: list[int] = []
    seis: list[str] = []
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        for i, locator in enumerate(locators):
            sei = f"loomweave:eid:{i}"
            seis.append(sei)
            keys.append(store.ensure_entity_key(repo_id, locator=locator, sei=sei, commit_sha=head))
    return repo, keys, seis


_SEI0 = "loomweave:eid:0"
_LOC0 = "python:function:a.py::a"
_ITEMS = [{"entity": {"locator": _LOC0, "sei": _SEI0}}]


def _pw_class(fed: dict[str, Any]) -> str:
    """The plainweave member's weft-reason class within a federation block."""
    return fed["members"]["plainweave"]["weft_reason"]["reason_class"]


# --------------------------------------------------------------------------- (1) membership
def test_plainweave_is_a_federation_member() -> None:
    assert "plainweave" in FEDERATION_MEMBERS


def test_disabled_plainweave_is_named_not_dropped() -> None:
    fed = consult_federation(_ITEMS)  # no requirements_client
    assert "plainweave" in fed["members"]
    wr = fed["members"]["plainweave"]["weft_reason"]
    assert wr["reason_class"] == "disabled"
    assert wr["cause"] and wr["fix"]


def test_transport_blockers_name_plainweave() -> None:
    blockers = federation_transport_blockers(
        work_client=None, risk_client=None, legis_client=None, requirements_client=None
    )
    assert {b["member"] for b in blockers} == set(FEDERATION_MEMBERS)
    pw = next(b for b in blockers if b["member"] == "plainweave")
    assert "requirements-enrichment" in pw["need"]


# --------------------------------------------------------------------------- (2) status passthrough
def test_present_carries_requirements_and_is_clean() -> None:
    fed = consult_federation(_ITEMS, requirements_client=_FakeReq({_SEI0: _present(_SEI0)}))
    assert _pw_class(fed) == "clean"
    entity = next(e for e in fed["entities"] if e["locator"] == _LOC0)
    assert entity["requirements"]
    assert entity["requirements"][0]["stable_id"] == "plainweave:req:AUTH:0001"


def test_reachable_all_absent_is_clean_earned_empty() -> None:
    fed = consult_federation(_ITEMS, requirements_client=_FakeReq({_SEI0: _absent(_SEI0)}))
    assert _pw_class(fed) == "clean"
    assert fed["members"]["plainweave"]["entity_count"] == 0


def test_omitted_ref_sets_unavailable_seen_not_a_clean_empty() -> None:
    # A REACHABLE producer that SILENTLY OMITS a requested ref (returns no item for it)
    # is "I can't tell", not "none bound": it must mark unavailable_seen so the scalar
    # never collapses to the confident-empty absent (no-silent-clean, omitted-ref branch).
    fed = consult_federation(_ITEMS, requirements_client=_FakeReq({}))
    assert _pw_class(fed) == "clean"  # transport reachable
    assert fed["members"]["plainweave"]["entity_count"] == 0
    assert fed["members"]["plainweave"]["unavailable_seen"] is True


def test_sei_less_entity_is_unavailable_not_absent() -> None:
    # An affected entity warpline cannot resolve to a SEI is identity-unresolved — it
    # can't even be sent to plainweave. That is the canonical per-entity "unavailable"
    # ("could not determine identity"), NEVER the definitive earned-empty "absent" whose
    # reason would falsely claim plainweave determined none are bound.
    items = [{"entity": {"locator": "python:function:a.py::a"}}]  # no "sei"
    fed = consult_federation(items, requirements_client=_FakeReq({}))
    assert _pw_class(fed) == "clean"  # transport reachable
    assert fed["members"]["plainweave"]["unavailable_seen"] is True


def test_raising_transport_is_unreachable_not_empty() -> None:
    fed = consult_federation(_ITEMS, requirements_client=_BoomReq())
    wr = fed["members"]["plainweave"]["weft_reason"]
    assert wr["reason_class"] == "unreachable"
    assert "exploded" in wr["cause"] and wr["fix"]


# --------------------------------------------------------------------------- reason helper
def test_requirements_reason_for_maps_the_closed_vocab() -> None:
    assert requirements_reason_for("present")["reason_class"] == "clean"
    assert requirements_reason_for("absent")["reason_class"] == "unresolved_input"
    assert requirements_reason_for("unavailable")["reason_class"] == "unreachable"
    for state in ("absent", "unavailable"):
        triple = requirements_reason_for(state)
        assert triple["cause"] and triple["fix"]


def test_static_requirements_reason_stays_disabled() -> None:
    # the reserved/not-consulted fallback is unchanged (frozen non-federated fixture)
    assert requirements_reason()["reason_class"] == "disabled"


# --------------------------------------------------------------------------- (acceptance 1) present
def test_reverify_lights_requirements_present(tmp_path: Path) -> None:
    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    client = _FakeReq({seis[0]: _present(seis[0])})
    env = commands.reverify_worklist(
        repo, keys, depth=2, include_federation=True, requirements_client=client
    )
    assert env["enrichment"]["requirements"] == "present"
    assert env["enrichment_reasons"]["requirements"]["reason_class"] == "clean"
    item = env["data"]["items"][0]
    assert item["enrichment"]["requirements"][0]["stable_id"] == "plainweave:req:AUTH:0001"
    # member is clean and named.
    assert _pw_class(env["data"]["federation"]) == "clean"
    # HI4 local-only seam: the one plainweave CLI hop never leaks a peer side effect.
    assert env["meta"]["local_only"] is True
    assert env["meta"]["peer_side_effects"] == []


# --------------------------------------------------------------------------- (acceptance 2) absent
def test_reverify_shows_absent_for_known_entity_with_no_binding(tmp_path: Path) -> None:
    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    client = _FakeReq({seis[0]: _absent(seis[0])})
    env = commands.reverify_worklist(
        repo, keys, depth=2, include_federation=True, requirements_client=client
    )
    assert env["enrichment"]["requirements"] == "absent"
    assert env["enrichment_reasons"]["requirements"]["reason_class"] == "unresolved_input"
    assert env["data"]["items"][0]["enrichment"]["requirements"] == []


# --------------------------------------------------------------- (acceptance 3 / no-silent-clean)
def test_reverify_all_unavailable_is_unavailable_never_absent(tmp_path: Path) -> None:
    """The DISCRIMINATING case: a REACHABLE producer that returns per-entity
    ``status:"unavailable"`` for every ref (e.g. SEIs absent from plainweave's
    catalog on a stale sync) must surface envelope ``unavailable`` — NEVER collapsed
    to the confident-empty ``absent``."""

    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    client = _FakeReq({seis[0]: _unavailable(seis[0])})
    env = commands.reverify_worklist(
        repo, keys, depth=2, include_federation=True, requirements_client=client
    )
    assert env["enrichment"]["requirements"] == "unavailable"
    assert env["enrichment"]["requirements"] != "absent"
    # member transport was reachable (clean), but identity could not be determined.
    assert env["enrichment_reasons"]["requirements"]["reason_class"] == "unreachable"


def test_reverify_sei_less_entity_is_unavailable_not_absent(tmp_path: Path) -> None:
    """End-to-end no-silent-clean: a worklist entity with NO SEI (identity unresolved)
    must surface envelope ``unavailable`` with the could-not-determine reason — NEVER
    ``absent`` with a reason falsely claiming plainweave found none bound."""

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "agent@example.test")
    _git(repo, "config", "user.name", "Agent")
    (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-m", "init")
    head = _git(repo, "rev-parse", "HEAD")
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        key = store.ensure_entity_key(
            repo_id, locator="python:function:a.py::a", sei=None, commit_sha=head
        )
    env = commands.reverify_worklist(
        repo, [key], depth=2, include_federation=True, requirements_client=_FakeReq({})
    )
    assert env["enrichment"]["requirements"] == "unavailable"
    assert env["enrichment"]["requirements"] != "absent"
    assert env["enrichment_reasons"]["requirements"]["reason_class"] == "unreachable"


def test_reverify_producer_fault_is_unavailable_not_absent(tmp_path: Path) -> None:
    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    env = commands.reverify_worklist(
        repo, keys, depth=2, include_federation=True, requirements_client=_BoomReq()
    )
    assert env["enrichment"]["requirements"] == "unavailable"
    assert (
        env["data"]["federation"]["members"]["plainweave"]["weft_reason"]["reason_class"]
        == "unreachable"
    )


def test_reverify_disabled_when_no_client(tmp_path: Path) -> None:
    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    env = commands.reverify_worklist(repo, keys, depth=2, include_federation=True)
    assert env["enrichment"]["requirements"] == "unavailable"
    wr = env["data"]["federation"]["members"]["plainweave"]["weft_reason"]
    assert wr["reason_class"] == "disabled"
    # the disabled fix recruits installing/upgrading plainweave, not a faked-empty.
    assert "requirements-enrichment" in wr["fix"]


def test_reverify_mixed_present_and_unavailable_is_present(tmp_path: Path) -> None:
    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a", "python:function:a.py::b"])
    client = _FakeReq({seis[0]: _present(seis[0]), seis[1]: _unavailable(seis[1])})
    env = commands.reverify_worklist(
        repo, keys, depth=2, include_federation=True, requirements_client=client
    )
    # ≥1 entity present -> present (the present signal wins).
    assert env["enrichment"]["requirements"] == "present"


# --------------------------------------------------------------------------- advisory never gates
def _find_key(node: Any, key: str) -> bool:
    if isinstance(node, dict):
        return key in node or any(_find_key(v, key) for v in node.values())
    if isinstance(node, list):
        return any(_find_key(v, key) for v in node)
    return False


def test_requirements_is_advisory_never_gates(tmp_path: Path) -> None:
    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    present = commands.reverify_worklist(
        repo, keys, depth=2, include_federation=True,
        requirements_client=_FakeReq({seis[0]: _present(seis[0])}),
    )
    absent = commands.reverify_worklist(
        repo, keys, depth=2, include_federation=True,
        requirements_client=_FakeReq({seis[0]: _absent(seis[0])}),
    )
    # the advisory scalar DID flip (the signal is real)...
    assert present["enrichment"]["requirements"] == "present"
    assert absent["enrichment"]["requirements"] == "absent"

    def _decision(env: dict[str, Any]) -> dict[str, Any]:
        ic = {k: v for k, v in env["data"]["impact_completeness"].items() if k != "as_of"}
        return {
            "verification_summary": env["data"]["verification_summary"],
            "risk_verification": env["data"]["risk_verification"],
            "impact_completeness": ic,
            "resolved": env["data"]["resolved"],
            "unresolved": env["data"]["unresolved"],
        }

    assert _decision(present) == _decision(absent)
    assert [i["entity"]["locator"] for i in present["data"]["items"]] == [
        i["entity"]["locator"] for i in absent["data"]["items"]
    ]
    # requirements never masquerades as a verdict, never leaks into the posture.
    assert not _find_key(present, "verdict")
    assert not _find_key(present["data"]["risk_verification"], "requirements")


# --------------------------------------------------------- MCP capability gate
def test_h_reverify_capability_gate_lights_requirements(tmp_path: Path, monkeypatch) -> None:
    from warpline import mcp
    from warpline.federation import PlainweaveRequirementsClient

    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    monkeypatch.setattr(
        PlainweaveRequirementsClient, "available", classmethod(lambda cls, repo: True)
    )
    monkeypatch.setattr(
        PlainweaveRequirementsClient,
        "requirements_for_refs",
        lambda self, refs: {r: _present(r) for r in refs},
    )
    env = mcp._h_reverify(
        {"repo": str(repo), "changed_entity_key_ids": keys, "depth": 2, "include_federation": True}
    )
    assert env["enrichment"]["requirements"] == "present"
    assert _pw_class(env["data"]["federation"]) == "clean"


def test_h_reverify_capability_gate_disabled_when_verb_absent(tmp_path: Path, monkeypatch) -> None:
    """The other half of the gate: when the installed plainweave does NOT advertise the
    verb, ``available()`` is False, no client is wired, and the member is honestly
    ``disabled`` -> scalar ``unavailable`` (never a forced unreachable, never a faked-empty)."""

    from warpline import mcp
    from warpline.federation import PlainweaveRequirementsClient

    repo, keys, seis = _seed(tmp_path, ["python:function:a.py::a"])
    monkeypatch.setattr(
        PlainweaveRequirementsClient, "available", classmethod(lambda cls, repo: False)
    )
    env = mcp._h_reverify(
        {"repo": str(repo), "changed_entity_key_ids": keys, "depth": 2, "include_federation": True}
    )
    assert env["enrichment"]["requirements"] == "unavailable"
    wr = env["data"]["federation"]["members"]["plainweave"]["weft_reason"]
    assert wr["reason_class"] == "disabled"
    assert "requirements-enrichment" in wr["fix"]
