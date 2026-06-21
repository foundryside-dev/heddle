from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_SOURCES = [
    "<weft-root>/doctrine.md",
    "<weft-root>/pm/product/decisions/0013-post-launch-priority-stack-and-discovery-pipeline.md",
    "<weft-root>/federation-sdk.md",
    "<weft-root>/members/warpline.md",
    "<loomweave-root>/README.md",
    "<loomweave-root>/crates/loomweave-mcp/src/lib.rs",
    "<loomweave-root>/crates/loomweave-cli/src/cli.rs",
    "<loomweave-root>/crates/loomweave-storage/src/sei.rs",
    "<legis-root>/src/legis/api/app.py",
    "<legis-root>/tests/git/test_rename_feed.py",
    "<filigree-root>/docs/federation/contracts.md",
    "<filigree-root>/tests/fixtures/contracts/weft/scan-results.json",
    "<wardline-root>/src/wardline/core/agent_summary.py",
    "<wardline-root>/src/wardline/core/filigree_emit.py",
    "<charter-root>/src/charter/mcp_surface.py",
    "<charter-root>/docs/agentic-doors-replacement-roadmap.md",
]


def main() -> int:
    manifest = Path("docs/evidence/2026-06-13-source-grounding.md")
    if not manifest.exists():
        print("missing docs/evidence/2026-06-13-source-grounding.md", file=sys.stderr)
        return 1
    baseline = Path("docs/evidence/member-dirty-baseline.txt")
    if not baseline.exists():
        print("missing docs/evidence/member-dirty-baseline.txt", file=sys.stderr)
        return 1
    text = manifest.read_text(encoding="utf-8")
    missing = [path for path in REQUIRED_SOURCES if path not in text]
    missing_tokens = [
        token
        for token in (
            "spike/REPORT.md",
            "owner admission",
            "no sibling repo patches",
            "pre-existing sibling dirty state",
        )
        if token not in text
    ]
    if missing or missing_tokens:
        print({"missing_sources": missing, "missing_tokens": missing_tokens}, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
