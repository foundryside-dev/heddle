# PRD-0001 - Agent-First MCP Productization

Status: implemented-for-product-candidate; P1 contract refactor remains
Decision: PDR-0001
Bet (roadmap.md): Now
Target metric (metrics.md): Agent impact answer success rate

## Problem

Coding agents working in Weft member repos need to decide what changed, what may
be affected, and what to reverify before they claim work is complete. Today that
job falls back to manual grep, memory, raw git inspection, or human judgment.
Warpline has enough implementation to answer the job, but it must be productized
around the MCP surface because agents experience Warpline primarily through
`tools/list` and structured tool calls, not through architecture documents.

## Success metric

Agent impact answer success rate reaches at least one real-member benchmark
where an executed existing-tools baseline (`git diff --name-only` plus `rg`)
matches Warpline MCP changed output, actual Loomweave MCP snapshot capture
provides enrichment, and MCP `reverify` returns a non-empty worklist before
admission recommendation.

Baseline: measured on Lacuna as of 2026-06-13. The current dogfood run captures
522 Loomweave edges and returns 4 real-member reverify items. Planted corpus and
synthetic federation cases remain smoke coverage, not readiness evidence.

## Acceptance criteria (falsifiable)

1. SUCCESS - An agent starting from MCP `tools/list` can discover the core flow
   and answer changed-set plus reverify context with parity against an executed
   real-member `git diff --name-only` plus `rg` baseline.
   Reject branch: If the real-member lane requires raw SQLite inspection or
   manual grep outside the measured baseline, the bet is rejected and an MCP
   refactor plan is opened.
2. FEDERATION UPLIFT - When federation member enrichment is available, the
   real-member dogfood lane captures a sibling MCP snapshot and returns a
   non-empty Warpline reverify worklist that existing tools alone do not provide.
   Reject branch: If enriched answers are merely equal to existing tools, the
   federation value claim is unproven and the bet is rejected.
3. MCP STRUCTURE - Every core MCP response includes schema/version, query
   metadata, enrichment state, warnings when degraded, and actionable next-step
   fields where applicable.
   Reject branch: any core response that returns opaque text without structured
   recovery fields blocks acceptance.
   Current read: core tool responses include `structuredContent`, live
   `tools/list` includes local-write/idempotency metadata, and `mcp-smoke`
   proves structured bad-input recovery. Specific output schemas,
   namespaced aliases, filters/sort, pagination, and resource contracts remain
   the next P1 refactor.
4. FEDERATION BOUNDARY - Warpline responses identify absent, stale, skipped, or
   no-snapshot enrichment without claiming sibling-owned current truth.
   Reject branch: any response that treats Loomweave, Plainweave, Legis, Wardline,
   or Filigree data as Warpline-owned truth blocks acceptance.
5. SOLO MODE - With no sibling enrichment, Warpline still returns useful
   locator-keyed changed/timeline/reverify facts and explicit `NO_SNAPSHOT` or
   absent enrichment state.
   Reject branch: sibling absence causing crash, empty ambiguity, or hidden
   degradation blocks acceptance.
6. RELEASE HYGIENE - The release-candidate gate passes with member-diff guard,
   spike harness, productization gate, lint, types, and tests.
   Reject branch: any Warpline-caused sibling repo diff or failing gate blocks
   acceptance.

## Non-goals (this bet)

- Do not declare federation admission.
- Do not patch sibling repos.
- Do not design pricing, hosting, telemetry, or external release posture.
- Do not turn Warpline into a tracker, governance gate, trust engine, or current
  structure authority.

## Constraints & guardrails

- Warpline must remain local-first and read-only against analyzed repos.
- Missing sibling data must degrade honestly and explicitly.
- MCP deficiencies are P0 product defects; they are not documentation polish.
- A broken Warpline hook must never block a commit.
- Warpline-owned draft contracts remain non-normative until owner admission and
  glossary clearance.

## Open questions / assumptions

- Broaden real-member dogfood beyond the current Lacuna/Loomweave case after
  Wardline, Filigree, and Legis interfaces are endorsed.
- Broaden specific output schemas and MCP resources after federation interface
  endorsement.

## Handoff

- Product owns this PRD, acceptance criteria, and the value verdict.
- Planning owns the executable implementation plan for any MCP refactor.
- Solution architecture owns any changes to server shape, schema versioning, or
  contract-freeze posture.
- Program-management owns sequencing if multiple productization slices compete.
