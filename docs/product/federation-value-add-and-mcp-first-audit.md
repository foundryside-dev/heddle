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

## Interface Endorsement Package

Status: proposed for federation endorsement. If the federation side endorses
this section, treat these names and shapes as the agreed Heddle interfaces for
the next implementation slice. Until then, this remains a Heddle-owned proposal.

This package does not admit Heddle to the federation, freeze glossary terms, or
authorize sibling repo changes. It defines the narrow interface Heddle proposes
to expose and consume while preserving Weft doctrine: enrich-only, local-first,
SEI opaque, no shared runtime, no shared store, no Heddle-owned governance,
work-state, trust, requirements, or current-graph truth.

### Authority Boundaries

| Domain | Owning member | Heddle behavior |
| --- | --- | --- |
| Current structure, entity catalog, SEI minting/resolution | Loomweave | Consume and store SEI opaque; capture dated graph snapshots; never claim current graph truth. |
| Work state, issues, observations, claims, lifecycle | Filigree | Read or propose links; never file, close, claim, or mutate work by default. |
| Trust policy, findings, waivers, baselines, taint lattice | Wardline | Consume risk/finding facts as enrichment; never declare a change allowed or clean. |
| Governance, signoff, CI/git attestations, overrides | Legis | Consume provenance and rename facts; emit advisory impact only; never govern. |
| Requirements, traceability, verification evidence, baselines | Charter | Consume obligation context; never emit requirement satisfaction or release readiness. |
| Demo corpus | Lacuna | Use as optional dogfood/showcase corpus; never as product authority. |
| Change execution | Future Shuttle/Codeweave-style member | Do not bind until a real member exists. |

### MCP Tool Names

The endorsed surface should use namespaced object-action names. The current short
names remain compatibility shims until glossary freeze.

| Endorsed tool | Compatibility shim | Mutates | Purpose |
| --- | --- | --- | --- |
| `heddle_change_list` | `changed` | No | List temporal change facts for a repo and rev range. |
| `heddle_entity_timeline_get` | `timeline` | No | Return ordered change history for one entity reference. |
| `heddle_impact_radius_get` | `blast_radius` | No | Return downstream affected entities from dated snapshots. |
| `heddle_reverify_worklist_get` | `reverify` | No | Return an agent-first worklist for what to reverify. |
| `heddle_edge_snapshot_capture` | `capture_snapshot` | Yes, local Heddle state only | Capture a dated edge snapshot into `.weft/heddle/`. |
| `heddle_project_context_get` | none | No | Return Heddle project context, capabilities, contract URIs, and current store status. |

Tool aliases must return the same `schema` and data contract as the endorsed
tool name. Agents should prefer the endorsed name when both are present.

### Common Success Envelope

Every Heddle MCP tool returns `structuredContent` with this envelope. The text
content may contain the same object serialized as compact JSON for older hosts,
but agents should not have to parse text to recover the contract.

```json
{
  "schema": "heddle.<contract>.v1",
  "ok": true,
  "query": {
    "repo": "/abs/path",
    "tool": "heddle_change_list",
    "arguments": {},
    "filters": {},
    "sort": {"by": "changed_at", "order": "asc"},
    "page": {"limit": 50, "cursor": null}
  },
  "data": {},
  "warnings": [],
  "next_actions": {},
  "enrichment": {
    "sei": "present|absent|unavailable",
    "edges": "present|absent|stale|partial|skipped|unavailable",
    "work": "present|absent|unavailable",
    "risk": "present|absent|unavailable",
    "governance": "present|absent|unavailable",
    "requirements": "present|absent|unavailable"
  },
  "meta": {
    "producer": {"tool": "heddle", "version": "0.1.0"},
    "local_only": true,
    "peer_side_effects": []
  }
}
```

Rules:

- `data` is tool-specific and schema-bound.
- `query` echoes normalized inputs, defaults, filters, sort, and page controls.
- `warnings` carry human-readable summaries; machines switch on structured
  fields in `data`, `enrichment`, and `meta`.
- `next_actions` contains ready-to-call MCP tool names and arguments.
- Missing peers produce explicit `unavailable` enrichment, not transport
  failure, empty ambiguity, or implied clean state.

### Common Error Envelope

Heddle should keep JSON-RPC error codes for protocol compatibility, but the
`error.data` object should be stable and recoverable.

```json
{
  "code": -32602,
  "message": "invalid params",
  "data": {
    "schema": "heddle.error.v1",
    "error_code": "invalid_rev_range",
    "rejected_field": "rev_range",
    "retryability": "retry_with_changes",
    "hint": "Pass a git revision range resolvable from repo, such as HEAD~1..HEAD.",
    "details": {}
  }
}
```

Required `retryability` values:

- `retry_safe` - transient; retry same arguments.
- `retry_with_changes` - caller must change an argument.
- `fatal` - no agent-side recovery; surface to user.

Initial `error_code` vocabulary:

- `missing_required_field`
- `invalid_repo`
- `invalid_rev_range`
- `invalid_entity_ref`
- `invalid_changed_refs`
- `invalid_depth`
- `invalid_filter`
- `invalid_sort`
- `peer_unavailable`
- `snapshot_unavailable`
- `internal_error`

### Common Input Objects

Entity references should not force agents to know Heddle internal database ids.
Tools may still accept `changed_entity_key_ids` for compatibility, but endorsed
interfaces should prefer `entity_ref` and `changed_refs`.

```json
{
  "entity_ref": {
    "kind": "auto|locator|sei|path|qualname|heddle_entity_key_id",
    "value": "src/pkg/mod.py::fn"
  }
}
```

```json
{
  "changed_refs": [
    {"kind": "locator", "value": "src/pkg/mod.py::fn"},
    {"kind": "sei", "value": "loomweave:eid:..."}
  ]
}
```

Common list controls:

```json
{
  "limit": 50,
  "cursor": null,
  "sort_by": "changed_at",
  "sort_order": "asc",
  "filters": {}
}
```

List outputs include:

```json
{
  "items": [],
  "page": {
    "limit": 50,
    "next_cursor": null,
    "has_more": false
  }
}
```

### Tool Contracts

#### `heddle_change_list`

Intent: list temporal change facts for a repo and revision range, then hand the
agent ready-to-call impact/reverify actions.

Input:

```json
{
  "repo": "/abs/path",
  "rev_range": "HEAD~1..HEAD",
  "base_ref": null,
  "head_ref": null,
  "filters": {
    "path_prefix": null,
    "entity_kind": null,
    "change_kind": null,
    "actor": null,
    "commit": null,
    "since": null,
    "until": null,
    "has_sei": null
  },
  "sort_by": "changed_at|path|actor|change_kind",
  "sort_order": "asc|desc",
  "limit": 50,
  "cursor": null,
  "include_next_actions": true
}
```

Output `data`:

```json
{
  "items": [
    {
      "change_id": "heddle:change:...",
      "entity": {
        "heddle_entity_key_id": 1,
        "locator": "python:function:src/pkg/mod.py::fn",
        "sei": null,
        "path": "src/pkg/mod.py"
      },
      "change_kind": "modified",
      "actor": "agent:codex",
      "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "changed_at": "2026-06-13T00:00:00Z"
    }
  ],
  "changed_refs": [
    {"kind": "heddle_entity_key_id", "value": "1"}
  ],
  "page": {"limit": 50, "next_cursor": null, "has_more": false}
}
```

Required `next_actions`:

- `heddle_reverify_worklist_get`
- `heddle_impact_radius_get`

#### `heddle_entity_timeline_get`

Intent: return the ordered temporal history for one entity reference.

Input:

```json
{
  "repo": "/abs/path",
  "entity_ref": {"kind": "auto", "value": "src/pkg/mod.py::fn"},
  "filters": {
    "change_kind": null,
    "actor": null,
    "commit": null,
    "since": null,
    "until": null
  },
  "sort_by": "changed_at|commit",
  "sort_order": "asc|desc",
  "limit": 50,
  "cursor": null
}
```

Output `data`:

```json
{
  "entity": {
    "locator": "python:function:src/pkg/mod.py::fn",
    "sei": null,
    "identity_status": "stable|fragile|unknown"
  },
  "items": [],
  "page": {"limit": 50, "next_cursor": null, "has_more": false}
}
```

#### `heddle_impact_radius_get`

Intent: return affected downstream entities from Heddle's dated snapshots,
without claiming current graph truth.

Input:

```json
{
  "repo": "/abs/path",
  "rev_range": null,
  "changed_refs": [],
  "changed_entity_key_ids": [],
  "depth": 2,
  "filters": {
    "edge_kind": null,
    "confidence": null,
    "path_prefix": null,
    "max_commits_behind": null
  },
  "sort_by": "depth|confidence|path|changed_at|risk",
  "sort_order": "asc|desc",
  "limit": 100,
  "cursor": null
}
```

Output `data`:

```json
{
  "completeness": "FULL|DELTA|NO_SNAPSHOT|SKIPPED",
  "staleness": {
    "snapshot_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "commits_behind": 0
  },
  "changed": [],
  "affected": [
    {
      "entity": {"locator": "python:function:src/pkg/consumer.py::consumer", "sei": null},
      "depth": 1,
      "via_edges": [{"from": "1", "to": "2", "kind": "calls", "confidence": "resolved"}]
    }
  ],
  "page": {"limit": 100, "next_cursor": null, "has_more": false}
}
```

#### `heddle_reverify_worklist_get`

Intent: return the flagship agent worklist: what to reverify, why, how stale or
complete the evidence is, and which sibling facts enriched the recommendation.

Input:

```json
{
  "repo": "/abs/path",
  "rev_range": "HEAD~1..HEAD",
  "changed_refs": [],
  "changed_entity_key_ids": [],
  "depth": 2,
  "filters": {
    "path_prefix": null,
    "risk_min": null,
    "finding_state": null,
    "requirement_id": null,
    "verification_state": null,
    "issue_status": null,
    "governance_state": null,
    "max_commits_behind": null
  },
  "sort_by": "priority|risk|depth|changed_at|staleness",
  "sort_order": "asc|desc",
  "group_by": "entity|file|requirement|issue|none",
  "limit": 100,
  "cursor": null,
  "include_federation": true
}
```

Output `data`:

```json
{
  "completeness": "FULL|DELTA|NO_SNAPSHOT|SKIPPED",
  "staleness": {"snapshot_commit": null, "commits_behind": null},
  "items": [
    {
      "entity": {"locator": "python:function:src/pkg/mod.py::fn", "sei": null},
      "priority": "P1|P2|P3|unknown",
      "reason": "changed|downstream|risk_enriched|requirement_enriched",
      "depth": 0,
      "why": [],
      "suggested_verification": [
        {"kind": "test", "command": "run tests touching this entity if known"}
      ],
      "enrichment": {
        "work": [],
        "risk": [],
        "governance": [],
        "requirements": []
      }
    }
  ],
  "page": {"limit": 100, "next_cursor": null, "has_more": false}
}
```

#### `heddle_edge_snapshot_capture`

Intent: capture a dated snapshot of Loomweave edges into Heddle's local state.
This is the only endorsed mutating tool, and it mutates only `.weft/heddle/`.

Input:

```json
{
  "repo": "/abs/path",
  "commit": "HEAD",
  "mode": "full|changed_only",
  "changed_refs": [],
  "if_stale_after": null,
  "max_entities": 1000,
  "dry_run": false,
  "idempotency_key": null
}
```

Output `data`:

```json
{
  "snapshot_id": 1,
  "commit_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "source": "loomweave",
  "source_version": "1.1.0-rc4",
  "completeness": "FULL|DELTA|SKIPPED",
  "entities": 10,
  "edges": 12,
  "failed_entities": [],
  "idempotency": "created|already_current|dry_run"
}
```

Idempotency contract: repeated calls for the same repo, commit, mode, and
effective entity set must return `already_current` or replace the local Heddle
snapshot atomically without mutating siblings.

#### `heddle_project_context_get`

Intent: let an agent discover Heddle's local project state and contract
resources before calling task tools.

Input:

```json
{
  "repo": "/abs/path",
  "include_contracts": true
}
```

Output `data`:

```json
{
  "store": {"path": ".weft/heddle/heddle.db", "schema_version": 1},
  "capabilities": [
    {"name": "heddle_change_list", "mutates": false, "local_only": true}
  ],
  "contract_resources": [
    "heddle://contracts/heddle.change_list.v1",
    "heddle://contracts/heddle.reverify_worklist.v1"
  ],
  "peer_status": {
    "loomweave": "available|unavailable|unknown",
    "filigree": "available|unavailable|unknown",
    "wardline": "available|unavailable|unknown",
    "legis": "available|unavailable|unknown",
    "charter": "available|unavailable|unknown"
  }
}
```

### MCP Resource Contracts

Endorsed resources:

- `heddle://project/context`
- `heddle://contracts/heddle.error.v1`
- `heddle://contracts/heddle.change_list.v1`
- `heddle://contracts/heddle.entity_timeline.v1`
- `heddle://contracts/heddle.impact_radius.v1`
- `heddle://contracts/heddle.reverify_worklist.v1`
- `heddle://contracts/heddle.edge_snapshot.v1`

Resources are read-only and local. They document contract shapes; they do not
act as a registry or shared runtime.

### Pairwise Federation Interfaces

These are the proposed pairwise interfaces to endorse. Each is optional and
enrich-only.

| Pair | Heddle consumes | Heddle exposes | Degradation rule |
| --- | --- | --- | --- |
| Loomweave + Heddle | `entity_resolve`, `entity_neighborhood_get`, current locator/SEI facts | `heddle.edge_snapshot.v1`, `heddle.entity_temporal_summary.v1` | If Loomweave is absent, Heddle returns locator-keyed facts with `sei=unavailable`, `edges=unavailable` or `SKIPPED`. |
| Filigree + Heddle | Entity associations, issue/work status, reconciliation feed | `heddle.reverify_worklist.v1` candidate work context and optional `next_actions.filigree` | If Filigree is absent, Heddle omits work enrichment and never auto-files work. |
| Wardline + Heddle | Finding/risk facts, suppression state, taint/trust-boundary context | `heddle.affected_scope.v1` for scoped scan hints | If Wardline is absent, Heddle says `risk=unavailable`; it never treats absence as clean. |
| Legis + Heddle | `git_rename_list` / rename feed, branch/commit/PR/governance context | `heddle.preflight_impact.v1` advisory affected-set facts | If Legis is absent, Heddle uses raw git history and marks governance enrichment unavailable. |
| Charter + Heddle | Requirement links, verification freshness, baseline exposure | `heddle.obligation_impact_context.v1` advisory impacted obligations | If Charter is absent, Heddle omits requirement enrichment and never emits readiness verdicts. |
| Lacuna + Heddle | Seeded demo changes, real-member parity benchmark, and tour cases | Dogfood/demo results only | If Lacuna drifts, dogfood must either find another real code-change worklist or fail ready; synthetic cases are smoke coverage only. |

Proposed payload names:

- `heddle.entity_temporal_summary.v1` - per-entity churn, recent changes,
  last-touched actor/time, and snapshot staleness.
- `heddle.affected_scope.v1` - changed and affected entity refs with
  completeness/staleness for peer scoping.
- `heddle.preflight_impact.v1` - advisory impacted entities for governance
  context.
- `heddle.obligation_impact_context.v1` - advisory impacted entities grouped by
  Charter requirement ids.

### Endorsement Checklist

Federation endorsement should confirm:

- Heddle owns only temporal change facts and dated edge snapshots.
- Endorsed MCP names are acceptable in a multi-server tool list.
- The compatibility shims may remain until glossary freeze.
- The common envelope, error envelope, entity refs, list controls, and resource
  URIs are acceptable as Heddle's contract family.
- Pairwise payloads are enrich-only and do not require sibling presence.
- Sibling-side work remains post-admission or separately approved.

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
real-member dogfood lane now proves dated-edge capture through actual Loomweave
MCP.

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

- Keep Lacuna in `dogfood-eval` as the real-member readiness lane: executed
  baseline, actual Loomweave snapshot capture, and non-empty MCP reverify
  output.
- Keep synthetic cases as smoke coverage for the Heddle-owned graph contract;
  they must not be the release gate by themselves.

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

1. Resolved for core tool results - responses now include `structuredContent`.
   Text content remains as a compatibility fallback, but agents no longer have
   to parse a JSON string to recover the product contract.

2. P1 - Output schemas are too generic.
   Every tool advertises the same `{schema, ok, data, warnings, meta}` shell.
   That is better than no schema, but it does not tell an agent the shape of
   `data`, bounds, sort semantics, or recovery fields. Each core tool needs a
   specific output schema or contract resource.

3. P1 - List-like tools lack filters, sort, bounds, and cursor discipline.
   `changed`, `timeline`, `blast_radius`, and `reverify` can grow with history
   or graph size. Every list-like result needs `limit`, `cursor` or `offset`,
   `sort_by`, and `sort_order`, plus documented default ordering.

4. Partially resolved - tool descriptions now say when to call the tool, what
   to call next, and how degraded states should be interpreted. Namespaced
   aliases and specific output schemas remain the larger contract-refactor work.

5. Partially resolved - core recoverable errors now use `heddle.error.v1` with
   stable `error_code`, `retryability`, `hint`, and rejected-field data where
   applicable. A broader federation-wide error taxonomy is still needed before
   glossary freeze.

6. P1 - `changed_entity_key_ids` leaks internal database ids into the primary
   agent workflow.
   The happy path works because `changed.next_actions.reverify.arguments`
   carries ids forward, but agents entering from paths, locators, SEIs, or
   prior tool output need first-class inputs that do not require knowing Heddle
   internals.

7. Resolved for current tools - live `tools/list` metadata now declares
   read/local-write status, idempotency, touched local paths, concurrency, repo
   requirement, and federation dependencies.

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

Add namespaced aliases, specific output schemas, list pagination, filter/sort
parameters, and resource contracts. `structuredContent` and live
mutability/idempotency metadata are already present for current tools.

Acceptance:

- Every core tool has a namespaced alias.
- Every result keeps `structuredContent` and gains a bounded/paginated data
  shape where list-like.
- Every list-like tool supports filters, sort, and limit/cursor.
- Every error aligns with the federation-wide stable code taxonomy.
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

Extend dogfood beyond the current Lacuna/Loomweave lane after the MCP contract
refactor lands.

Acceptance:

- The release gate keeps at least one real-member benchmark with executed
  baseline, actual sibling MCP integration, and non-empty Heddle reverify
  output.
- Additional Lacuna dogfood demonstrates pairwise Heddle uplift stories for
  Wardline, Filigree, and Legis after those interfaces are endorsed.

## Bottom Line

Heddle's federation value is strongest when it acts as the temporal connective
tissue: it tells agents what changed over time, what dated graph facts imply,
and what to reverify next. The next gating concern is not whether Heddle has a
temporal store. It does. The concern is whether the MCP surface is as deliberate
as the product claim. Today it is usable and dogfood-passing, but not yet as
structured, filterable, sortable, recoverable, and verb-consistent as a first
class federation member should be.
