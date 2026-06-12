from __future__ import annotations

from heddle.reverify import render_reverify_worklist


def test_reverify_worklist_is_machine_first() -> None:
    blast = {
        "changed": [{"locator": "python:function:a"}],
        "affected": [
            {
                "locator": "python:function:b",
                "depth": 1,
                "via_edges": [{"from": "a", "to": "b", "kind": "calls"}],
            }
        ],
        "staleness": {"snapshot_commit": "c1", "commits_behind": None},
        "completeness": "FULL",
    }
    out = render_reverify_worklist(blast)
    assert out["format"] == "heddle.reverify.v1"
    assert out["items"][0]["entity"]["locator"] == "python:function:b"
    assert out["items"][0]["why"][0]["kind"] == "calls"
    assert out["staleness"] == blast["staleness"]
    assert out["completeness"] == "FULL"
