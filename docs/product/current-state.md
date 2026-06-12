# Current State - Heddle

Checkpoint: 2026-06-13 - branch `codex/implement-heddle` after release-candidate gate

## The bet right now

Make Heddle a first-class agentic MCP product candidate and first-class Weft
federation candidate without crossing the owner-reserved admission boundary.

## In flight

- Agent-first MCP productization - status: product design bootstrapped; PRD-0001
  ready for planning if the next implementation slice is authorized.
- Federation admission readiness - status: Heddle-owned contracts and consumer
  ticket package exist as pre-admission drafts; sibling repos remain untouched.
- Product continuity - status: `docs/product/` created; future sessions should
  RESUME here before reinterpreting the design.

## Open questions / blocked-on-owner

- Owner admission: Heddle is not an admitted Weft member until john explicitly
  makes that call.
- Glossary/wire freeze: MCP and JSON shapes remain pre-admission draft until
  glossary clearance and conformance-oracle inclusion.
- Dogfood evidence: the north-star needs a 10-diff MCP dogfood run before an
  admission recommendation should be treated as validated.

## Last checkpoint did

- Promoted Heddle from spike-only prose to product-candidate ownership posture.
- Recorded PDR-0001 and PRD-0001.
- Added falsifiable metrics and guardrails for agentic MCP usability.
- Made MCP deficiencies explicit P0 product defects, not polish.

## Next session, start here

Run a focused MCP usability review against PRD-0001. If an agent cannot discover
and use the core flow from `tools/list` and structured responses alone, dispatch
a refactor plan instead of polishing around the deficiency.
