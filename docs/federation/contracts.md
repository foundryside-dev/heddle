# Heddle Federation Contracts

Status: productization-ready pre-admission draft, Heddle-owned, backed by the
dogfood readiness gate in `spike/REPORT.md`.
These fixtures are non-normative until owner admission and glossary clearance.

Heddle exposes read-only, local-first CLI and MCP surfaces over its temporal store.
It owns temporal change facts and dated edge snapshots. It does not own current
structure, requirements, work state, trust policy, or governance.

## MCP tools

- `changed` - changed entities for a rev/range/diff.
- `timeline` - ordered change events for an entity.
- `blast_radius` - downstream affected set over dated snapshots.
- `reverify` - agent-consumable re-verification worklist.
- `capture_snapshot` - local dated edge snapshot capture from Loomweave's
  published read surface.

These short names are current compatibility shims. The Heddle-owned proposed
endorsed names are `heddle_change_list`, `heddle_entity_timeline_get`,
`heddle_impact_radius_get`, `heddle_reverify_worklist_get`, and
`heddle_edge_snapshot_capture`; see the Interface Endorsement Package in
[`../product/federation-value-add-and-mcp-first-audit.md`](../product/federation-value-add-and-mcp-first-audit.md).

All peer-facing behavior is local-only. `capture_snapshot` mutates Heddle's
local `.weft/heddle/` state only; it never mutates sibling repos. Sibling
absence returns explicit enrichment/completeness fields, not transport failure.

`tools/list` currently advertises output schemas plus metadata for read-only
status, local writes, idempotency, touched paths, concurrency, repo requirement,
and federation dependencies. Specific output schemas, MCP resources, filters,
sort controls, and pagination remain pre-admission contract-refactor work.
