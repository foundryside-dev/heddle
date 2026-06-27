"""G1 — weft-reason vocabulary conformance lock for warpline.

SOURCE OF TRUTH: /home/john/weft/contracts/weft-reason-vocab.json — the closed
11 canonical ``reason_class`` values plus the carrier rule (every NON-clean
result carries {reason_class, cause, fix}; a clean result omits cause+fix).

This test introspects warpline's ACTUAL reason vocabulary
(``warpline.listing.REASON_CLASSES``) and asserts it is a SUBSET of the
canonical 11, AND that ``warpline.listing.reason()`` enforces the carrier rule.
It FAILS if warpline ever drifts — adds a non-canonical reason_class, or stops
requiring cause+fix on a non-clean carrier (or starts requiring them on clean).

NOTE: the FROZEN ``warpline.error.v1`` envelope (errors.py: ERROR_CODES like
``invalid_filter`` / ``invalid_sort``) is a SEPARATE hard-rejection contract,
NOT weft-reason — it is deliberately NOT checked here and must not be conflated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from warpline.listing import REASON_CLASSES, reason

# The canonical contract is an out-of-repo weft-hub artifact (members stay
# independent repos with no shared runtime dep). If it is reachable we load the
# closed set from it directly; otherwise we fall back to the inline mirror below
# so the conformance assertion still runs in an isolated checkout.
_CANONICAL_CONTRACT = Path("/home/john/weft/contracts/weft-reason-vocab.json")

_CANONICAL_11 = frozenset(
    {
        "clean",
        "disabled",
        "unresolved_input",
        "rejected",
        "dead_path",
        "unreachable",
        "misrouted",
        "error",
        "scheme_mismatch",
        "stale",
        "partial",
    }
)


def _load_canonical() -> tuple[frozenset[str], dict]:
    """Return (canonical reason_class set, carrier spec). Prefer the on-disk
    contract; fall back to the inline mirror when it is not reachable."""

    if _CANONICAL_CONTRACT.is_file():
        data = json.loads(_CANONICAL_CONTRACT.read_text(encoding="utf-8"))
        classes = frozenset(data["reason_classes"])
        carrier = data["carrier"]
        return classes, carrier
    return _CANONICAL_11, {
        "required_on_non_clean": ["reason_class", "cause", "fix"],
        "clean_omits": ["cause", "fix"],
    }


def test_inline_mirror_matches_canonical_contract_when_present() -> None:
    """Guard the inline fallback: if the canonical contract is reachable, our
    mirror of the closed 11 must match it exactly (catches contract drift)."""

    if not _CANONICAL_CONTRACT.is_file():
        pytest.skip("canonical contract not reachable in this checkout")
    canonical, _carrier = _load_canonical()
    assert canonical == _CANONICAL_11, (
        "inline canonical mirror drifted from contracts/weft-reason-vocab.json"
    )


def test_reason_vocabulary_is_subset_of_canonical_11() -> None:
    """warpline's emitted reason_class set must be a SUBSET of the canonical 11.
    A non-canonical class added to REASON_CLASSES fails here."""

    canonical, _carrier = _load_canonical()
    extra = set(REASON_CLASSES) - set(canonical)
    assert not extra, f"non-canonical reason_class(es) emitted by warpline: {sorted(extra)}"


def test_reason_vocabulary_is_the_full_canonical_11() -> None:
    """warpline (post-G2) defines the full canonical 11. This pins that exact
    intent so a silent DROP of a class is also caught, not just an addition."""

    assert set(REASON_CLASSES) == set(_CANONICAL_11)


def test_carrier_clean_omits_cause_and_fix() -> None:
    """A clean carrier is exactly {reason_class: clean} — cause/fix omitted, so
    an earned true-negative is byte-distinguishable from a degraded empty."""

    carrier = reason("clean")
    assert carrier == {"reason_class": "clean"}
    assert "cause" not in carrier and "fix" not in carrier


@pytest.mark.parametrize(
    "reason_class",
    sorted(_CANONICAL_11 - {"clean"}),
)
def test_carrier_non_clean_requires_cause_and_fix(reason_class: str) -> None:
    """Every NON-clean class must carry both cause and fix, and reason() must
    REFUSE to build one missing either (the carrier rule is enforced, not
    advisory)."""

    carrier = reason(reason_class, cause="why", fix="do this")
    assert carrier["reason_class"] == reason_class
    assert carrier["cause"] == "why"
    assert carrier["fix"] == "do this"

    with pytest.raises(ValueError):
        reason(reason_class)  # both missing
    with pytest.raises(ValueError):
        reason(reason_class, cause="why")  # fix missing
    with pytest.raises(ValueError):
        reason(reason_class, fix="do this")  # cause missing


def test_reason_rejects_non_canonical_class() -> None:
    """reason() refuses to emit a class outside its own closed set — the guard
    that keeps drift from leaking through the constructor at runtime."""

    with pytest.raises(ValueError):
        reason("truncated", cause="x", fix="y")  # not one of the canonical 11
