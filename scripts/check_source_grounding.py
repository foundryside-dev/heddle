from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_SOURCES = [
    "/home/john/weft/doctrine.md",
    "/home/john/weft/pm/product/decisions/0013-post-launch-priority-stack-and-discovery-pipeline.md",
    "/home/john/weft/federation-sdk.md",
    "/home/john/weft/members/heddle.md",
    "/home/john/loomweave/README.md",
    "/home/john/loomweave/crates/loomweave-mcp/src/lib.rs",
    "/home/john/loomweave/crates/loomweave-cli/src/cli.rs",
    "/home/john/loomweave/crates/loomweave-storage/src/sei.rs",
    "/home/john/legis/src/legis/api/app.py",
    "/home/john/legis/tests/git/test_rename_feed.py",
    "/home/john/filigree/docs/federation/contracts.md",
    "/home/john/filigree/tests/fixtures/contracts/weft/scan-results.json",
    "/home/john/wardline/src/wardline/core/agent_summary.py",
    "/home/john/wardline/src/wardline/core/filigree_emit.py",
    "/home/john/charter/src/charter/mcp_surface.py",
    "/home/john/charter/docs/agentic-doors-replacement-roadmap.md",
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
