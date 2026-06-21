# Warpline Source Grounding Evidence

## Productization Gate

- `spike/REPORT.md` is the required authority for design-spike findings.
- Product release work proceeds only on `Recommendation: go`.
- Owner admission is required before member-side consumer wiring.
- Phase 0 rule: no sibling repo patches in `<filigree-root>`, `<wardline-root>`, `<loomweave-root>`, `<legis-root>`, or `<charter-root>`.
- pre-existing sibling dirty state must be recorded before implementation starts. This plan does not authorize cleaning, reverting, or patching sibling repos.

## Sources Checked

- `<weft-root>/doctrine.md` - federation doctrine, enrich-only, no shared runtime/store/broker, owner admission test.
- `<weft-root>/pm/product/decisions/0013-post-launch-priority-stack-and-discovery-pipeline.md` - Warpline discovery slot and agentic-first bar.
- `<weft-root>/federation-sdk.md` - member obligations, SEI opacity, honest degradation.
- `<weft-root>/members/warpline.md` - Warpline is design spike; no implementation yet.
- `<loomweave-root>/README.md` - graph/identity authority and live MCP families.
- `<loomweave-root>/crates/loomweave-mcp/src/lib.rs` - live MCP tool names.
- `<loomweave-root>/crates/loomweave-cli/src/cli.rs` - `analyze`, `serve`, `--legis-url`, `--no-sei`, `--no-incremental`.
- `<loomweave-root>/crates/loomweave-storage/src/sei.rs` - SEI prefix, opacity, lineage storage.
- `<legis-root>/src/legis/api/app.py` - git and governance HTTP routes.
- `<legis-root>/tests/git/test_rename_feed.py` - rename-feed shape and worktree flag semantics.
- `<filigree-root>/docs/federation/contracts.md` - named HTTP generations and `weft` envelope discipline.
- `<filigree-root>/tests/fixtures/contracts/weft/scan-results.json` - scan-results contract fixture.
- `<wardline-root>/src/wardline/core/agent_summary.py` - agent summary schema and next-action discipline.
- `<wardline-root>/src/wardline/core/filigree_emit.py` - native Filigree emit shape and fail-soft enrichment.
- `<charter-root>/src/charter/mcp_surface.py` - local-only read MCP tools and contract resources.
- `<charter-root>/docs/agentic-doors-replacement-roadmap.md` - impact analysis is P1/deferred and Charter integration is planned.
