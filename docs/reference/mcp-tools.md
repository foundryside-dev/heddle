# MCP tool reference

warpline exposes its surface over an MCP stdio server (JSON-RPC 2.0). Launch it
with the `warpline-mcp` executable, or as a module:

```bash
warpline-mcp                 # installed entry point
python -m warpline.mcp        # module form
```

The server speaks line-delimited JSON-RPC on stdin/stdout and supports the
`2024-11-05` and `2025-03-26` MCP protocol versions. Three methods are handled:

| Method | Purpose |
| --- | --- |
| `initialize` | Handshake. Returns `serverInfo {name: "warpline", version}`, the negotiated `protocolVersion`, and `instructions`. |
| `tools/list` | List every tool with its `inputSchema`, `outputSchema`, and `metadata`. |
| `tools/call` | Invoke a tool by `name` with `arguments`. |

## Six tools, twelve names

There are **six** frozen federation tools. Each is registered under **two** names
— an endorsed name and a short shim — that return identical schema and data. So
`tools/list` reports twelve entries; they collapse to six tools.

| Endorsed name | Shim | Schema | Mutating? |
| --- | --- | --- | --- |
| `warpline_change_list` | `changed` | `warpline.change_list.v1` | no |
| `warpline_entity_timeline_get` | `timeline` | `warpline.entity_timeline.v1` | no |
| `warpline_entity_churn_count_get` | `churn` | `warpline.entity_churn_count.v1` | no |
| `warpline_impact_radius_get` | `blast_radius` | `warpline.impact_radius.v1` | no |
| `warpline_reverify_worklist_get` | `reverify` | `warpline.reverify_worklist.v1` | no |
| `warpline_edge_snapshot_capture` | `capture_snapshot` | `warpline.edge_snapshot.v1` | yes (local only) |
| `warpline_verification_record` | `verify_record` | `warpline.verification_record.v1` | yes (local only) |

All tools require `repo` (a path string). The read tools are marked
`read_only: true` but may initialize `.weft/warpline/` state on first touch.
`warpline_edge_snapshot_capture` and `warpline_verification_record` are the two
mutating tools — both write only to `.weft/warpline/`.

## The success envelope

Every outbound tool returns the same frozen envelope. Only `data`, `next_actions`,
and the relevant `enrichment` keys differ between tools.

```json
{
  "schema": "warpline.<contract>.v1",
  "ok": true,
  "query": {
    "repo": "...", "tool": "...", "arguments": {},
    "filters": {}, "sort": {"by": "...", "order": "asc"},
    "page": {"limit": 50, "cursor": null}
  },
  "data": { },
  "warnings": [],
  "next_actions": {},
  "enrichment": {"sei": "...", "edges": "...", "work": "...",
                 "risk": "...", "governance": "...", "requirements": "..."},
  "meta": {
    "producer": {"tool": "warpline", "version": "1.1.1"},
    "local_only": true,
    "peer_side_effects": []
  }
}
```

- `enrichment` is a **closed vocabulary**: `present` (peer present, fact attached),
  `absent` (peer present, no fact), `unavailable` (peer unreachable), plus `stale |
  partial | skipped` for `edges`. None is ever a transport error or an implied
  clean state. See [Degrade behavior](../concepts/degrade.md).
- `meta.local_only` is always `true`; `meta.peer_side_effects` is always `[]`.
- Over JSON-RPC, a successful `tools/call` returns the envelope in both
  `result.structuredContent` (the object) and `result.content[0].text` (the same
  object, JSON-serialized).

## The error envelope

Recoverable errors are returned as a JSON-RPC `error` whose `data` is a
`warpline.error.v1` object:

```json
{
  "jsonrpc": "2.0", "id": 1,
  "error": {
    "code": -32602, "message": "invalid params",
    "data": {
      "schema": "warpline.error.v1",
      "error_code": "invalid_rev_range",
      "rejected_field": "rev_range",
      "retryability": "retry_with_changes",
      "hint": "Pass a git revision range resolvable from repo, e.g. HEAD~1..HEAD.",
      "details": {"message": "..."}
    }
  }
}
```

**Switch on `error_code`, not on message text.** Both vocabularies are closed:

| `error_code` | `retryability` | Meaning |
| --- | --- | --- |
| `missing_required_field` | `retry_with_changes` | A required argument was absent. |
| `invalid_repo` | `retry_with_changes` | `repo` is not a readable git repository. |
| `invalid_rev_range` | `retry_with_changes` | The `rev_range` did not resolve. |
| `invalid_entity_ref` | `retry_with_changes` | The `entity_ref` had an unknown shape/kind. |
| `invalid_changed_refs` | `retry_with_changes` | `changed_refs` was not a list of `{kind, value}`. |
| `invalid_depth` | `retry_with_changes` | `depth` was not an integer in `0`–`5`. |
| `invalid_filter` | `retry_with_changes` | A `filters` key was not recognised. |
| `invalid_sort` | `retry_with_changes` | `sort_by`/`sort_order` was not recognised. |
| `peer_unavailable` | `retry_safe` | A federation peer was unreachable. |
| `snapshot_unavailable` | `retry_with_changes` | A graph-enriched answer was requested with no snapshot. |
| `internal_error` | `fatal` | A warpline defect. Inspect logs before retrying. |

`retryability` is one of `retry_safe`, `retry_with_changes`, `fatal`.

JSON-RPC transport codes used: `-32700` parse error, `-32600` invalid request,
`-32601` unknown method/tool, `-32602` invalid params (recoverable
`warpline.error.v1`), `-32603` internal error.

## Entity refs and keying

Inputs that name an entity accept a `{kind, value}` ref (a bare string is treated
as `kind: auto`). Accepted `kind` values:

```text
auto | locator | sei | path | qualname | warpline_entity_key_id
```

Every entity in a response carries **both** `locator` and `sei` (`sei: null` when
unresolved). Key on `sei` (preferred) or `locator`. `warpline_entity_key_id` is a
warpline-internal row id echoed for convenience — **not** a federation key. See
[SEI](../concepts/sei.md).

---

## `warpline_change_list` / `changed`

`warpline.change_list.v1` — changed entities for a repo and rev range; returns
ready-to-call `next_actions`. **Call this first.**

**Input**

| Field | Type | Notes |
| --- | --- | --- |
| `repo` | string | (required) |
| `rev_range` | string | git revision range, e.g. `HEAD~1..HEAD`. Omit for all recorded changes. |
| `base_ref`, `head_ref` | string | accepted in the schema. |
| `filters` | object | reserved. |
| `sort_by`, `sort_order` | string | reserved. |
| `limit` | integer | default `50`. |
| `cursor` | string \| null | reserved (single page; `next_cursor` is always `null`). |
| `include_next_actions` | boolean | — |

**`data`**

```json
{
  "items": [
    {
      "change_id": "warpline:change:3",
      "entity": {"locator": "...", "sei": null, "warpline_entity_key_id": 1, "path": "..."},
      "change_kind": "added | modified | removed | moved",
      "actor": "...", "commit": "...", "changed_at": "<iso8601>"
    }
  ],
  "changed_refs": [{"kind": "sei | locator", "value": "..."}],
  "page": {"limit": 50, "next_cursor": null, "has_more": false}
}
```

`next_actions` names `warpline_reverify_worklist_get` and
`warpline_impact_radius_get`, each with ready-to-call `arguments` (the resolved
`changed_entity_key_ids`, `changed_refs`, and `depth: 2`). `enrichment.sei` is
`present` if any item resolved a SEI, else `absent`.

---

## `warpline_entity_timeline_get` / `timeline`

`warpline.entity_timeline.v1` — ordered change history for one entity.

**Input**

| Field | Type | Notes |
| --- | --- | --- |
| `repo` | string | (required) |
| `entity_ref` | object | `{kind, value}`. |
| `entity` | string | bare-string alternative to `entity_ref` (kind `auto`). |
| `filters`, `sort_by`, `sort_order`, `limit`, `cursor` | — | `limit` default `50`. |

**`data`**

```json
{
  "entity": {"locator": "...", "sei": "... | null",
             "sei_resolution": "resolved | unresolved | unknown"},
  "items": [{"change_kind": "...", "actor": "...", "commit": "...",
             "changed_at": "<iso8601>", "path": "..."}],
  "page": {"limit": 50, "next_cursor": null, "has_more": false}
}
```

`sei_resolution` is warpline's local honesty signal about its own resolution state
— **not** a lineage claim. `enrichment.governance` is `present` only when a rename
feed was supplied (timeline stitched across renames), else `unavailable`.

---

## `warpline_entity_churn_count_get` / `churn`

`warpline.entity_churn_count.v1` — per-entity change-event counts over an optional
window. A never-observed entity returns `churn_count: 0` (not omitted, not an
error).

**Input**

| Field | Type | Notes |
| --- | --- | --- |
| `repo` | string | (required) |
| `entity_refs` | array of `{kind, value}` | (required) |
| `window` | object | `{since, until, rev_range}`, all optional. |
| `sort_by` | string | `churn_count` (default) or `sei`. |
| `sort_order` | string | `desc` (default) or `asc`. |
| `limit` | integer | default `100`. |
| `cursor` | string \| null | reserved. |

**`data`**

```json
{
  "items": [
    {"entity": {"sei": "... | null", "locator": "..."},
     "churn_count": 2,
     "first_changed_at": "<iso8601 | null>",
     "last_changed_at": "<iso8601 | null>",
     "last_actor": "... | null"}
  ],
  "window": {"since": null, "until": null, "rev_range": null},
  "page": {"limit": 100, "next_cursor": null, "has_more": false}
}
```

---

## `warpline_impact_radius_get` / `blast_radius`

`warpline.impact_radius.v1` — downstream affected entities over the latest dated
snapshot, with mandatory `completeness` + `staleness`.

**Input**

| Field | Type | Notes |
| --- | --- | --- |
| `repo` | string | (required) |
| `rev_range` | string | seed from a rev range's change events. |
| `changed_refs` | array of `{kind, value}` | seed entities (SEIs preferred). |
| `changed_entity_key_ids` | array of integers | seed entities by internal key id. |
| `depth` | integer | `0`–`5`, default `2`. |
| `filters`, `sort_by`, `sort_order`, `limit`, `cursor` | — | `limit` default `100`. |

Seeds are the union of `changed_entity_key_ids`, the resolved `changed_refs`, and
the change events in `rev_range`.

**`data`**

```json
{
  "completeness": "FULL | DELTA | NO_SNAPSHOT | SKIPPED",
  "staleness": {"snapshot_commit": "... | null", "commits_behind": 0},
  "changed": [{"entity": {"locator": "...", "sei": "..."}}],
  "affected": [
    {"entity": {"locator": "...", "sei": "..."},
     "depth": 1,
     "via_edges": [{"from": "...", "to": "...", "kind": "calls | references", "confidence": "..."}]}
  ],
  "page": {"limit": 100, "next_cursor": null, "has_more": false}
}
```

`completeness` and `staleness` are **mandatory in every answer**. A non-`FULL`
completeness adds a `warnings[]` entry. `enrichment.edges` mirrors completeness
(`present`/`partial`/`absent`/`skipped`). An empty `affected` under `NO_SNAPSHOT`
means "no graph to traverse," never "nothing affected." See
[Blast-radius](../concepts/blast-radius.md).

---

## `warpline_reverify_worklist_get` / `reverify`

`warpline.reverify_worklist.v1` — the worklist to recheck before claiming
completion. Same input as `impact_radius`, plus `group_by` and
`include_federation`.

**`data`**

```json
{
  "completeness": "FULL | DELTA | NO_SNAPSHOT | SKIPPED",
  "staleness": {"snapshot_commit": "... | null", "commits_behind": 0},
  "items": [
    {
      "entity": {"locator": "...", "sei": "..."},
      "priority": "P1 | P2 | P3 | unknown",
      "reason": "changed | downstream",
      "depth": 0,
      "why": [ /* via_edges path for downstream items */ ],
      "suggested_verification": [{"kind": "test | inspection", "command": "..."}],
      "enrichment": {"work": [], "risk": [], "governance": [], "requirements": []}
    }
  ],
  "next_actions": {"filigree": [ /* candidate work items */ ]},
  "page": {"limit": 100, "next_cursor": null, "has_more": false}
}
```

Changed entities are always present (`reason: changed`); downstream items are added
when a snapshot exists. `priority` comes from sibling work enrichment, not from
warpline — `unknown` when there is no work seam. `next_actions.filigree[]` holds
**candidate** work items; warpline files nothing. `enrichment.work` is `present`
when work links were seen, `absent` when the filigree peer was consulted but had
none, `unavailable` when there was no work client.

When `include_federation=true`, the filigree work client reads the dashboard HTTP
API at `FILIGREE_API_URL` (default `http://localhost:8724`) for ADR-029 entity
association reverse lookups and issue records. Point `FILIGREE_API_URL` at a
non-default dashboard when filigree is not running locally. If that API is absent
or unreachable, the response stays local-only and records work enrichment as
`unavailable` with the filigree member reason `unreachable`; this is not a
confident empty result.

---

## `warpline_edge_snapshot_capture` / `capture_snapshot`

`warpline.edge_snapshot.v1` — the **only mutating tool**. Captures loomweave's
dated edges into `.weft/warpline/`. Never mutates a sibling repo.

**Input**

| Field | Type | Notes |
| --- | --- | --- |
| `repo` | string | (required) |
| `commit` | string | commit to stamp the snapshot at (default `HEAD`). |
| `mode` | string | `full` (default) or `changed_only`. |
| `changed_refs` | array of `{kind, value}` | for `changed_only` mode. |
| `if_stale_after` | string \| null | — |
| `max_entities` | integer | — |
| `dry_run` | boolean | report what would be captured without writing. |
| `idempotency_key` | string \| null | — |

The loomweave executable is **server/project config**, not a tool argument — set
`WARPLINE_LOOMWEAVE_COMMAND` (default `loomweave`).

**`data`**

```json
{
  "snapshot_id": 1,
  "commit_sha": "...",
  "source": "loomweave",
  "source_version": "... | no_index",
  "completeness": "FULL | DELTA | SKIPPED",
  "entities": 0,
  "edges": 0,
  "failed_entities": [{"locator": "...", "reason": "..."}],
  "idempotency": "created | already_current | dry_run"
}
```

With loomweave absent, `completeness` is `SKIPPED` and `source_version` is
`no_index` — an honest "no edges captured." `DELTA` means some entities failed to
capture (listed in `failed_entities`); the snapshot is usable but a floor.
`enrichment.sei` is `unavailable` when loomweave was unreachable (the SEI authority
could not be consulted), else `absent`.

---

## `warpline_verification_record` / `verify_record`

`warpline.verification_record.v1` — **2nd mutating tool**. Records a gate-pass
verification event for a commit into `.weft/warpline/`. Never mutates a sibling repo.
Advisory; warpline never gates. Idempotent on `(repo, commit, kind, source=warpline)`.

**Input**

| Field | Type | Notes |
| --- | --- | --- |
| `repo` | string | (required) |
| `commit` | string | (required) commit ref — resolved to object SHA before storage; symbolic refs are never persisted. |
| `kind` | string | (required) free-form non-empty provenance label, e.g. `test_pass`, `ci_pass`, `gate_pass`. |
| `actor` | string \| null | optional — who recorded the event. |

**`data`**

```json
{
  "commit_sha": "...",
  "kind": "test_pass",
  "verified_at": "2026-06-25T10:00:00+00:00",
  "actor": "ci",
  "source": "warpline",
  "idempotency": "recorded | already_recorded"
}
```

`idempotency: already_recorded` means the row already existed (a second call for
the same `(repo, commit, kind)` tuple is a no-op — exactly one row is stored).
All enrichment keys are `absent` (no graph-layer dependency).
