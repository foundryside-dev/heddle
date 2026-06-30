from __future__ import annotations

import pytest

from warpline.reverify import render_reverify_worklist


def test_reverify_worklist_is_machine_first() -> None:
    items, work_seen, candidates = render_reverify_worklist(
        changed=[{"entity": {"locator": "python:function:a", "sei": None}}],
        affected=[
            {
                "entity": {"locator": "python:function:b", "sei": None},
                "depth": 1,
                "via_edges": [{"from": "1", "to": "2", "kind": "calls", "confidence": "resolved"}],
            }
        ],
        completeness="FULL",
        staleness={"snapshot_commit": "c1", "commits_behind": None},
    )
    changed_item = next(item for item in items if item["reason"] == "changed")
    assert changed_item["entity"]["locator"] == "python:function:a"
    downstream = next(item for item in items if item["reason"] == "downstream")
    assert downstream["entity"]["locator"] == "python:function:b"
    assert downstream["why"][0]["kind"] == "calls"
    assert downstream["depth"] == 1
    assert downstream["enrichment"] == {
        "work": [],
        "risk": [],
        "governance": [],
        "requirements": [],
    }
    assert work_seen is False
    assert candidates == []


def test_reverify_worklist_raises_on_equal_length_order_drift() -> None:
    """U2: an equal-length ORDER drift between the entity rows and their paired
    ``(entity_key_id, locator)`` verification axis must fail LOUDLY.

    The call-site length guard only checks ``len(changed) == len(key_ids)``; with
    two rows it passes (2 == 2) even when the pairing is PERMUTED, so the wrong
    verification block silently attaches to the wrong entity. Here ``changed`` is
    ``[a, b]`` but the pairs are reversed to ``[(7, b-locator), (3, a-locator)]``
    — same length, wrong order. The per-row identity echo catches it: row ``a``'s
    live locator does not match the frozen locator ``key id 7`` was derived from.
    """

    changed = [
        {"entity": {"locator": "python:function:a", "sei": None}},
        {"entity": {"locator": "python:function:b", "sei": None}},
    ]
    # Equal length (2 == 2) but the (key_id, locator) pairs are in REVERSE order
    # relative to `changed`: pair[0] carries b's locator while changed[0] is a.
    drifted_pairs: list[tuple[int | None, str | None]] = [
        (7, "python:function:b"),
        (3, "python:function:a"),
    ]

    with pytest.raises(ValueError, match="identity echo failed"):
        render_reverify_worklist(
            changed=changed,
            affected=[],
            completeness="FULL",
            staleness={"snapshot_commit": "c1", "commits_behind": None},
            changed_key_ids=drifted_pairs,
        )


def test_reverify_worklist_correctly_ordered_pairs_do_not_raise() -> None:
    """U2: the echo is a NO-OP on correctly-ordered input — aligned
    ``(entity_key_id, locator)`` pairs render without raising, proving the
    tripwire is behavior-preserving on every currently-valid input."""

    changed = [
        {"entity": {"locator": "python:function:a", "sei": None}},
        {"entity": {"locator": "python:function:b", "sei": None}},
    ]
    aligned_pairs: list[tuple[int | None, str | None]] = [
        (3, "python:function:a"),
        (7, "python:function:b"),
    ]

    items, _work_seen, _candidates = render_reverify_worklist(
        changed=changed,
        affected=[],
        completeness="FULL",
        staleness={"snapshot_commit": "c1", "commits_behind": None},
        changed_key_ids=aligned_pairs,
    )
    assert [it["entity"]["locator"] for it in items] == [
        "python:function:a",
        "python:function:b",
    ]
