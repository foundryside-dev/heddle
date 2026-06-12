# Federation Value Add and MCP-First Audit - Heddle

Date: 2026-06-13
Status: Heddle-owned analysis, pre-admission

This audit asks two questions:

1. How each other Weft system can enhance Heddle, and how Heddle can enhance it,
   without violating enrich-only federation doctrine.
2. Whether Heddle's MCP surface is agent-first enough to be a first-class
   federation product.

Verdict: Heddle now has a credible product-candidate core, but the next value
step is not more raw temporal storage. The next value step is an MCP surface and
pairwise enrichment model that makes agents prefer Heddle in real member repos.
Any interface friction below is at least P1 because MCP is the primary product
surface.

## Federation Value Add

### Loomweave

Loomweave enhances Heddle by supplying stable identity and current structural
truth: locator to SEI resolution, entity lineage, current neighborhoods, source
context, summaries, and graph shape. Heddle should treat all of that as dated
enrichment and store only the temporal facts it owns.

Heddle enhances Loomweave by adding time: high-churn entities, recently changed
entities, stale snapshots, dated graph deltas, and "this entity changed recently
and its downstream callers were affected" context inside Loomweave entity
briefings.

Heddle-side changes:

- Add batch capture and refresh controls around Loomweave neighborhoods, with
  completeness, staleness, truncation, and failure reasons preserved per entity.
- Accept locator or SEI inputs everywhere an agent currently needs internal
  `changed_entity_key_ids`.
- Surface entity churn and recent-change summaries as first-class MCP results,
  not only as raw `timeline` reads.

Loomweave-side changes after admission:

- Consume Heddle for `entity_high_churn_list` and `entity_recent_change_list`
  rather than deriving recency from only current graph state.
- Add a Heddle-backed temporal panel in entity orientation packs.
- Keep Loomweave as identity/current-graph authority; Heddle facts must be
  clearly marked dated and advisory.

Priority: P1. This is the most natural first federation uplift because Heddle's
dogfood federation lane already proves the dated-edge model.

### Filigree

Filigree enhances Heddle by supplying work context: which issue, observation,
plan, claim, or finding is already attached to a changed entity. That lets
Heddle distinguish "reverify this changed code" from "reverify this changed
code because it closes a claimed P1 and has linked observations."

Heddle enhances Filigree by generating reverify worklists from actual temporal
impact instead of manual issue notes. It can propose observations, issue links,
or closure checklist items, but should not file or mutate work by default.

Heddle-side changes:

- Read Filigree entity associations and reconciliation changes when available.
- Add work-state enrichment to `reverify`: linked issue ids, issue status,
  claim state, stale claim flags, and suggested explicit Filigree next action.
- Never auto-file by default. Emit a candidate `next_actions.filigree` block
  that a human or a separate write-capable Filigree tool must execute.

Filigree-side changes after admission:

- Consume Heddle reverify worklists as optional observations or closure-check
  evidence after an explicit user action.
- Add "changed since issue was claimed/closed" filters for issue lists.
- Preserve Filigree as work-state authority; Heddle only supplies temporal
  impact facts.

Priority: P1. This makes federation membership visibly better for agents doing
real work, not only code analysis.

### Wardline

Wardline enhances Heddle by supplying trust/risk context: active findings,
suppression state, taint facts, trust-boundary decorators, and whether a changed
entity sits on a sensitive boundary. That lets Heddle sort and explain reverify
work by risk instead of graph distance alone.

Heddle enhances Wardline by giving it a precise affected set for scoped rescans,
baseline freshness checks, and "which trust finding might have been invalidated
by this change" prompts.

Heddle-side changes:

- Add optional Wardline enrichment to `reverify`: active findings, suppression
  state, taint-boundary facts, and trust-boundary proximity.
- Add sort/filter knobs for risk-aware worklists: `risk_min`, `finding_state`,
  `trust_boundary_only`, and `sort_by=risk|depth|changed_at`.
- Mark Wardline absence as risk enrichment unavailable, never as clean.

Wardline-side changes after admission:

- Accept Heddle affected sets as scoped scan hints.
- Report when a scan was Heddle-scoped and include Heddle completeness/staleness
  in the scan result metadata.
- Keep full scan as the authoritative fallback.

Priority: P1. Without this, Heddle's worklists are useful but not yet
risk-sensitive.

### Legis

Legis enhances Heddle by supplying governance and git/CI provenance: approved
rev ranges, rename feeds, branch/commit/PR state, signoff binding, override
state, and whether a change is operating under a protected policy cell.

Heddle enhances Legis by supplying advisory impacted entities and stale
verification context for preflight or signoff review. Legis should never let
Heddle decide a governance verdict.

Heddle-side changes:

- Consume Legis rename feeds so `timeline` and `changed` stay stable across
  common file moves.
- Add governance context to outputs: branch/commit provenance, signoff binding
  presence, and policy cell context when Legis is available.
- Add filters for governed ranges: `rev_range`, `branch`, `pr`, `signoff_id`,
  and `governance_state`.

Legis-side changes after admission:

- Read Heddle affected-set summaries as advisory preflight facts.
- Show Heddle completeness/staleness next to identity gaps and lineage integrity.
- Preserve Legis as the only governance authority.

Priority: P1 for rename/provenance consumption; P2 for deeper preflight
composition.

### Charter

Charter enhances Heddle by supplying obligation context: requirements linked to
changed or affected entities, verification freshness, stale evidence, baseline
drift, and accepted trace links.

Heddle enhances Charter by supplying temporal affected sets that help Charter
answer "which obligations might this change touch?" without requiring a full
manual trace walk.

Heddle-side changes:

- Add optional Charter enrichment to `reverify`: requirement ids, verification
  freshness, baseline exposure, and obligation severity.
- Add filters for `requirement_id`, `verification_state`, and
  `baseline_exposure`.
- Keep Charter facts as obligation context only; Heddle must not produce a
  release-readiness verdict.

Charter-side changes after admission:

- Consume Heddle affected entities in requirement dossiers and impact analysis.
- Include Heddle completeness/staleness in obligation impact reports.
- Preserve Charter as requirements and verification authority.

Priority: P2 until Charter's federation adapters are live, then P1 because this
is a strong pair-mode story.

### Lacuna

Lacuna is the demo specimen, not a domain authority. It enhances Heddle by
providing a stable seeded corpus for dogfood and federation demos.

Heddle enhances Lacuna by adding a temporal-impact lane to the tour: changed
entity, affected entity, linked finding/work/governance context, and reverify
recommendation.

Heddle-side changes:

- Add Lacuna scenarios to `dogfood-eval` after the synthetic corpus remains
  stable.
- Keep synthetic dogfood as the release gate, because demo drift should not
  block core product validation.

Lacuna-side changes after admission:

- Add Heddle to the generated matrix and tour explainers.
- Seed one or two history-dependent examples where Heddle is visibly better
  than grep or current graph inspection.

Priority: P2. It is valuable for proof and sales, not for core authority.

### Shuttle or a Future Codeweave-Style Execution Member

Shuttle is currently speculative and not a member. If a change-execution product
such as Shuttle or Codeweave becomes real, Heddle should not pre-bind to it.

That future product would enhance Heddle by supplying execution records: planned
edits, applied hunks, rollback points, and post-check results. Heddle would then
be able to explain not only what changed in git, but what an execution agent
attempted and how that maps to later impact.

Heddle would enhance the execution product by supplying impact boundaries before
and after changes: likely affected entities, stale snapshots, and reverify
worklists before a change is considered complete.

Priority: no current implementation priority. Reserve names and concepts only;
do not ship bindings to a non-member.

## MCP-First Evaluation

### Federation verb consistency

Peer pattern observed:

- Loomweave and Charter favor namespaced object-action verbs:
  `entity_neighborhood_get`, `entity_recent_change_list`,
  `charter_requirement_search`, `charter_baseline_list`.
- Legis favors domain-object verbs with action suffixes:
  `git_rename_list`, `policy_evaluate`, `signoff_status_get`,
  `identity_gap_list`.
- Filigree and Wardline retain shorter workflow verbs, but they compensate with
  rich descriptions, structured envelopes, guards, and workflow-specific
  recovery paths.

Heddle's current names (`changed`, `timeline`, `blast_radius`, `reverify`,
`capture_snapshot`) are concise, but they are under-namespaced in a multi-server
agent context and inconsistent with the strongest federation naming pattern.

Recommendation: add namespaced aliases before admission, keeping current names
as compatibility shims until glossary freeze:

| Current | Preferred alias | Reason |
| --- | --- | --- |
| `changed` | `heddle_change_list` | List temporal change facts; avoids adjective-as-verb ambiguity. |
| `timeline` | `heddle_entity_timeline_get` | Returns timeline for one entity. |
| `blast_radius` | `heddle_impact_radius_get` | "Impact" is clearer to agents than metaphorical "blast". |
| `reverify` | `heddle_reverify_worklist_get` | Names the returned artifact. |
| `capture_snapshot` | `heddle_edge_snapshot_capture` | Mutating local capture over dated edges. |

Priority: P1. The current names pass dogfood, but federation cohabitation will
put them beside many peer tools. Ambiguous verbs are agent friction.

### Cross-cutting MCP gaps

1. P1 - Responses are JSON serialized inside text content only.
   Heddle should add `structuredContent` with the same object and keep text as a
   compact human-readable fallback. Agents should not have to parse a string
   field to recover the product contract.

2. P1 - Output schemas are too generic.
   Every tool advertises the same `{schema, ok, data, warnings, meta}` shell.
   That is better than no schema, but it does not tell an agent the shape of
   `data`, bounds, sort semantics, or recovery fields. Each core tool needs a
   specific output schema or contract resource.

3. P1 - List-like tools lack filters, sort, bounds, and cursor discipline.
   `changed`, `timeline`, `blast_radius`, and `reverify` can grow with history
   or graph size. Every list-like result needs `limit`, `cursor` or `offset`,
   `sort_by`, and `sort_order`, plus documented default ordering.

4. P1 - Tool descriptions are not workflow-oriented enough.
   They state what each tool returns, but they do not consistently describe
   when to call it, what to do next, whether it mutates local state, and how to
   recover from thin or degraded answers.

5. P1 - Error envelopes are JSON-RPC structured, but not yet product
   recoverable.
   Errors include a reason string, but they need stable `error.code`,
   `retryability`, `hint`, and the rejected field. Agents should switch on code,
   not parse text.

6. P1 - `changed_entity_key_ids` leaks internal database ids into the primary
   agent workflow.
   The happy path works because `changed.next_actions.reverify.arguments`
   carries ids forward, but agents entering from paths, locators, SEIs, or
   prior tool output need first-class inputs that do not require knowing Heddle
   internals.

7. P1 - Mutability and idempotency are not visible in `tools/list`.
   `capture_snapshot` mutates only `.weft/heddle`, but the tool should declare
   idempotency, concurrency, local-only mutation, and peer side-effect facts in
   the live MCP tool definition, not only in fixtures/docs.

8. P2 - MCP resources are missing.
   Contract resources like `heddle://contracts/heddle.change_list.v1`,
   `heddle://contracts/heddle.reverify_worklist.v1`, and
   `heddle://project/context` would reduce pressure on tool descriptions.

### Tool-by-tool audit

#### `changed`

Current strength: it returns changed events, `changed_entity_key_ids`, and a
ready-to-call `next_actions.reverify.arguments` block. This is the best current
agent workflow.

MCP gaps:

- P1: no `limit`, `cursor`, `sort_by`, or `sort_order`.
- P1: no filters for `path`, `entity`, `entity_kind`, `change_kind`, `actor`,
  `commit`, `since`, `until`, `has_sei`, or `enrichment`.
- P1: no structured `query` object in the outer envelope that repeats repo,
  rev range, filters, ordering, and result bounds.
- P1: `rev_range` is an unvalidated free string. It should either report a
  recoverable invalid-revision error or expose safer common modes like
  `base_ref` plus `head_ref`.

Recommended next shape: `heddle_change_list(repo, rev_range, filters, sort,
limit, cursor, include_next_actions=true)`.

#### `timeline`

Current strength: simple one-entity temporal history.

MCP gaps:

- P1: accepts only a single `entity` string without declaring whether locator,
  SEI, path, or qualname are valid.
- P1: no time/rev filters, change-kind filters, actor filters, or bounds.
- P1: no sort controls despite temporal ordering being the product claim.
- P1: no next actions for "capture snapshot", "resolve SEI", or "reverify this
  entity's downstream dependents."

Recommended next shape:
`heddle_entity_timeline_get(repo, entity_ref, ref_kind=auto|locator|sei|path,
filters, sort_by=changed_at, sort_order=asc|desc, limit, cursor)`.

#### `blast_radius`

Current strength: it honestly reports `NO_SNAPSHOT`, `SKIPPED`, `DELTA`, or
`FULL`, and it uses dated snapshots rather than pretending to own current graph
truth.

MCP gaps:

- P1: primary input is internal ids only.
- P1: no filters for edge kind, confidence, max staleness, included entity kind,
  or path prefix.
- P1: no sorting for affected entities by depth, confidence, path, churn, risk,
  or verification priority.
- P1: output can grow with graph fanout; `depth` is bounded but result size is
  not separately bounded.

Recommended next shape:
`heddle_impact_radius_get(repo, changed_refs|changed_entity_key_ids|rev_range,
depth, filters, sort_by=depth, limit, cursor)`.

#### `reverify`

Current strength: it converts impact data into an agent-consumable worklist and
is the right flagship surface.

MCP gaps:

- P1: input inherits `blast_radius` internal-id leakage.
- P1: no priority, risk, requirement, finding, issue, path, or verification-kind
  filters.
- P1: no `sort_by=priority|risk|depth|changed_at|staleness` controls.
- P1: suggested verification commands are generic; enriched commands should
  cite the source of confidence and whether a sibling supplied the hint.
- P1: no stable grouping option such as `group_by=entity|file|requirement|issue`.

Recommended next shape:
`heddle_reverify_worklist_get(repo, changed_refs|rev_range|changed_result,
filters, sort, group_by, limit, cursor, include_federation=true)`.

#### `capture_snapshot`

Current strength: it is local-only, never mutates sibling repos, and degrades to
`SKIPPED` when Loomweave is unavailable.

MCP gaps:

- P1: mutating local state without a visible idempotency and concurrency
  contract in live `tools/list`.
- P1: `loomweave_command` is an agent-supplied string. Prefer server/project
  configuration or a constrained capability choice; arbitrary command path
  selection is unnecessary agent burden.
- P1: no `force`, `if_stale_after`, `max_entities`, `entity_filter`,
  `snapshot_mode=full|changed_only`, or dry-run/preview mode.
- P1: no clear "already current" idempotent result for repeated calls on the
  same commit.

Recommended next shape:
`heddle_edge_snapshot_capture(repo, commit, mode=full|changed_only,
if_stale_after, max_entities, idempotency_key, dry_run=false)`.

## Recommended Product Slices

### Slice 1 - MCP contract refactor

Priority: P1.

Add namespaced aliases, `structuredContent`, specific output schemas, list
pagination, filter/sort parameters, and live tool metadata for mutability,
local-only behavior, idempotency, and authority boundaries.

Acceptance:

- Every core tool has a namespaced alias.
- Every result has `structuredContent` and a bounded/paginated data shape.
- Every list-like tool supports filters, sort, and limit/cursor.
- Every error has stable code, retryability, rejected field, and hint.
- Golden MCP fixtures cover the new aliases and the old shims.

### Slice 2 - Risk-weighted reverify

Priority: P1.

Compose Heddle with Loomweave, Wardline, Filigree, and Legis where available to
sort and explain reverify worklists by impact, risk, work state, and governance
context. Missing peers must produce explicit unavailable enrichment.

Acceptance:

- Reverify output can sort by `risk`, `depth`, `changed_at`, and `staleness`.
- Each enriched fact carries `source`, `freshness`, and authority boundary.
- Wardline/Filigree/Legis absence leaves solo reverify useful.

### Slice 3 - Obligation-aware impact

Priority: P2 until Charter adapters are live, then P1.

Add Charter requirement and verification freshness enrichment to Heddle reverify
and affected-set outputs.

Acceptance:

- Requirement ids and verification states appear only when Charter supplies them.
- Heddle never emits release-readiness or requirement-satisfaction verdicts.

### Slice 4 - Demo and dogfood expansion

Priority: P2.

Extend dogfood with Lacuna scenarios after the MCP contract refactor lands.

Acceptance:

- Synthetic dogfood remains the release gate.
- Lacuna dogfood demonstrates at least one pairwise Heddle uplift story for
  Loomweave, Wardline, Filigree, and Legis.

## Bottom Line

Heddle's federation value is strongest when it acts as the temporal connective
tissue: it tells agents what changed over time, what dated graph facts imply,
and what to reverify next. The next gating concern is not whether Heddle has a
temporal store. It does. The concern is whether the MCP surface is as deliberate
as the product claim. Today it is usable and dogfood-passing, but not yet as
structured, filterable, sortable, recoverable, and verb-consistent as a first
class federation member should be.
