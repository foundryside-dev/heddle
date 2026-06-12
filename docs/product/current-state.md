# Current State - Heddle

Checkpoint: 2026-06-13 - `main` after MCP smoke and dogfood readiness gates

## The bet right now

Keep Heddle product-candidate ready while preserving the owner-reserved
federation admission boundary. Heddle must remain at least as good as existing
tools in solo mode and better with federation member enrichment.

## In flight

- Agent-first MCP productization - status: **product-candidate ready**. The
  dogfood evaluator now gates readiness on a real Lacuna benchmark: executed
  `git diff --name-only` plus `rg` baseline, MCP `capture_snapshot`, MCP
  `changed`, and MCP `reverify` with a non-empty worklist.
- MCP-first federation polish - status: **partially implemented while awaiting
  federation review**.
  See
  [`federation-value-add-and-mcp-first-audit.md`](federation-value-add-and-mcp-first-audit.md)
  for the remaining P1 surface gaps: namespaced aliases, specific output
  schemas, filters/sort/pagination, and broader recoverable error taxonomy.
  Live `tools/list` now includes mutability/idempotency metadata, and
  `heddle mcp-smoke` proves initialize, tool inventory, structured tool-error
  recovery, and post-error survivability over real stdio.
- Federation admission readiness - status: Heddle-owned contracts and consumer
  ticket package exist as pre-admission drafts; Heddle-side federation uplift is
  implemented and proven against actual Loomweave MCP on Lacuna. Sibling-side
  tickets remain post-admission work.
- Product continuity - status: `docs/product/` created; future sessions should
  RESUME here before reinterpreting the design.

## Current non-admission gaps

- Production ingest/backfill can optionally resolve SEI through Loomweave's
  published `entity_resolve` surface; default hook ingest still avoids the
  dependency.
- Production snapshot capture now has CLI/MCP entrypoints, but `blast_radius` /
  `reverify` must stay covered by dogfood as the surface evolves.
- Federation uplift is Heddle-side ready by implementation plus draft specs;
  sibling-side work remains deferred until owner admission.
- MCP recovery, C-9 runtime placement, and C-13 hostile-input handling are
  covered by tests and must stay release-gated.

## Open questions / blocked-on-owner

- Owner admission: Heddle is not an admitted Weft member until john explicitly
  makes that call.
- Glossary/wire freeze: MCP and JSON shapes remain pre-admission draft until
  glossary clearance and conformance-oracle inclusion.
- Owner decision: whether product-candidate readiness becomes federation
  admission, glossary freeze, and sibling ticket dispatch.

## Last checkpoint did

- Recorded the live-review verdict as `not-ready` in the spike report and
  product docs.
- Hardened initial MCP/runtime defects: malformed JSON degrades instead of
  killing the server, tools advertise output schemas, `changed` feeds
  `reverify` ids, default state moves to `.weft/heddle/`, and undecodable Python
  files degrade to file locators.
- Added `capture-snapshot` / `capture_snapshot` as the production path for
  dated Loomweave edge snapshot capture into local Heddle state.
- Added optional Loomweave-backed SEI resolution for `backfill` and
  `ingest-commit`, with clean degradation when Loomweave is unavailable.
- Tightened `dogfood-eval`, producing `/tmp/heddle-dogfood-results.json`;
  current run proves 1/1 real-member baseline parity, 1/1 real Loomweave uplift
  with 522 captured edges and 4 reverify items, plus 10/10 seeded federation
  smoke cases.
- Added MCP-first wait-time polish: `tools/list` metadata for read/local-write
  status, idempotency, touched paths, and federation dependencies; configurable
  `dogfood-eval --real-member-repo`; and `heddle mcp-smoke` for a real stdio
  initialize/tools/list/tool-error survivability check.
- Refreshed README and evidence docs so the agent-facing entry point documents
  the shipped MCP workflow, verification gates, and remaining P1 contract
  refactor.
- Added the federation value-add and MCP-first audit that maps pairwise value
  against Loomweave, Filigree, Wardline, Legis, Charter, Lacuna, and a future
  Shuttle/Codeweave-style execution member.
- Expanded that audit with an endorsement-ready interface package: endorsed MCP
  names, compatibility shims, success/error envelopes, entity refs, list
  controls, resource URIs, tool contracts, and pairwise payload names.

## Next session, start here

Execute [`docs/plans/2026-06-13-heddle-1-0-readiness.md`](../plans/2026-06-13-heddle-1-0-readiness.md).
Keep productization evidence fresh by running `heddle dogfood-eval` and
`heddle mcp-smoke` before `heddle productization-gate`. For further product
work, start with the remaining P1 MCP contract refactor in
[`federation-value-add-and-mcp-first-audit.md`](federation-value-add-and-mcp-first-audit.md).
If the federation side endorses that document, treat its Interface Endorsement
Package as the agreed implementation target. Do not dispatch sibling tickets
until owner admission is explicit.
