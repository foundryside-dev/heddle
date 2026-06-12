from __future__ import annotations

from typing import Any


def render_reverify_worklist(blast_radius: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for affected in blast_radius.get("affected", []):
        if not isinstance(affected, dict):
            continue
        locator = affected.get("locator") or str(affected.get("entity_key_id"))
        items.append(
            {
                "entity": {"locator": locator},
                "reason": "downstream of changed entity",
                "depth": affected["depth"],
                "why": affected.get("via_edges", []),
                "suggested_verification": [
                    {"kind": "test", "command": "run tests touching this entity if known"},
                    {
                        "kind": "inspection",
                        "command": "inspect callers and behavior at this boundary",
                    },
                ],
            }
        )
    return {
        "format": "heddle.reverify.v1",
        "completeness": blast_radius["completeness"],
        "staleness": blast_radius["staleness"],
        "items": items,
    }
