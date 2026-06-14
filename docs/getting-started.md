# Getting Started

This guide takes you from an empty environment to reading your first
re-verification worklist. Every command and every block of output below was run
against a real warpline 1.0.0; the JSON is real output, abbreviated only where
noted.

warpline is local-first and enrich-only — none of the steps below need a sibling
tool installed. Where a sibling (loomweave) would deepen the answer, the guide
says so and shows what the degraded answer looks like.

## 1. Install

warpline is a zero-dependency Python package (≥ 3.12). Install it as a
[uv](https://docs.astral.sh/uv/) tool to put the `warpline` and `warpline-mcp`
executables on your `PATH`:

```bash
uv tool install warpline
```

```bash
pip install warpline        # alternative
```

Check the install:

```bash
warpline --version
```

```text
warpline 1.0.0
```

## 2. Ingest a repository's history

warpline stores temporal facts in a local SQLite store under `.weft/warpline/`.
Populate it from a repository's git history with `backfill`:

```bash
warpline backfill --repo /path/to/project --json
```

```json
{"commits": 2, "sei": {"absent": 0, "resolved": 0}}
```

`commits` is how many commits were ingested. The `sei` counters report SEI
resolution against loomweave; here loomweave is absent, so SEI resolution did not
run. Resolution is **on by default** and degrades cleanly when loomweave is not
present — pass `--no-resolve-sei` to skip the loomweave probe entirely (as this
guide does, to stay sibling-free).

!!! note "You usually do not run backfill by hand"
    `warpline install` (see step 6) wires a git `post-commit` hook that ingests
    each new commit as you make it, so the temporal store stays fresh without a
    manual backfill. `backfill` is for the initial import of existing history.

## 3. Ask what changed

`changed` lists the entities that changed over a git revision range. **Call it
first** — its response hands back ready-to-call arguments for the next tool.

```bash
warpline changed --repo /path/to/project --rev-range HEAD~1..HEAD
```

```json
{
  "schema": "warpline.change_list.v1",
  "ok": true,
  "data": {
    "items": [
      {
        "change_id": "warpline:change:3",
        "entity": {
          "locator": "python:function:src/demo/auth.py::login",
          "sei": null,
          "warpline_entity_key_id": 1,
          "path": "src/demo/auth.py"
        },
        "change_kind": "modified",
        "actor": "t <t@t.dev>",
        "commit": "ea7c6f28c77a6ce7f57ae246f576c90bcb9a9c60",
        "changed_at": "2026-06-14T03:53:39+10:00"
      }
    ],
    "changed_refs": [
      {"kind": "locator", "value": "python:function:src/demo/auth.py::login"}
    ],
    "page": {"limit": 50, "next_cursor": null, "has_more": false}
  },
  "next_actions": {
    "warpline_reverify_worklist_get": {
      "tool": "warpline_reverify_worklist_get",
      "arguments": {
        "repo": "/path/to/project",
        "changed_entity_key_ids": [1],
        "changed_refs": [{"kind": "locator", "value": "python:function:src/demo/auth.py::login"}],
        "depth": 2
      }
    },
    "warpline_impact_radius_get": { "...": "same shape" }
  },
  "enrichment": {"sei": "absent", "edges": "absent", "work": "unavailable",
                 "risk": "unavailable", "governance": "unavailable", "requirements": "unavailable"},
  "meta": {"producer": {"tool": "warpline", "version": "1.0.0"},
           "local_only": true, "peer_side_effects": []}
}
```

Read this honestly:

| Field | What it tells you |
| --- | --- |
| `data.items[].entity.locator` | The entity that changed. warpline derives `python:function:` / `python:class:` locators from `.py` sources; non-Python files are tracked as `file:<path>`. |
| `data.items[].entity.sei` | The Loomweave SEI (`loomweave:eid:...`), or `null` when warpline has not resolved one. Here loomweave is absent, so `sei` is `null`. |
| `data.changed_refs` | The deduplicated `{kind, value}` refs for the change set — SEIs preferred, locators when no SEI is known. |
| `next_actions` | Ready-to-call arguments for `reverify` and `blast_radius`. Copy these straight into the next call. |
| `enrichment` | A closed vocabulary. `absent` = the peer is present but has no fact; `unavailable` = the peer is unreachable. Neither is ever an implied "clean" state. |
| `meta.local_only` | Always `true`: the call read and wrote only local state. `peer_side_effects` is always `[]`. |

## 4. Get the re-verification worklist

`reverify` is the flagship: the worklist of entities to recheck before you claim a
change is done. Use the arguments `changed` handed back:

```bash
warpline reverify --repo /path/to/project --changed-entity-key-id 1 --json
```

```json
{
  "schema": "warpline.reverify_worklist.v1",
  "ok": true,
  "data": {
    "completeness": "NO_SNAPSHOT",
    "staleness": {"snapshot_commit": null, "commits_behind": null},
    "items": [
      {
        "entity": {"locator": "python:function:src/demo/auth.py::login", "sei": null},
        "priority": "unknown",
        "reason": "changed",
        "depth": 0,
        "why": [],
        "suggested_verification": [
          {"kind": "test", "command": "run tests touching this entity if known"},
          {"kind": "inspection", "command": "inspect callers and behavior at this boundary"}
        ],
        "enrichment": {"work": [], "risk": [], "governance": [], "requirements": []}
      }
    ],
    "next_actions": {"filigree": []}
  },
  "warnings": ["NO_SNAPSHOT: downstream traversal unavailable; changed set only"],
  "enrichment": {"edges": "absent", "sei": "absent", "work": "unavailable", "...": "..."},
  "meta": {"local_only": true, "peer_side_effects": []}
}
```

The changed entity is always in the worklist (`reason: changed`), so the answer is
useful even with no snapshot. But note `completeness: NO_SNAPSHOT` and the
matching `warnings` entry: warpline is telling you it has **no downstream graph to
traverse**, so the worklist is the changed set only. A thin answer looks thin —
this is **never** "nothing else is affected."

## 5. Capture a snapshot to get downstream impact

To get downstream entities, warpline needs a dated edge snapshot, which it captures
from loomweave. With loomweave **absent**, the capture is honest about it:

```bash
warpline capture-snapshot --repo /path/to/project --json
```

```json
{
  "schema": "warpline.edge_snapshot.v1",
  "ok": true,
  "data": {
    "commit_sha": "ea7c6f28c77a6ce7f57ae246f576c90bcb9a9c60",
    "completeness": "SKIPPED",
    "source": "loomweave", "source_version": "no_index",
    "entities": 0, "edges": 0, "failed_entities": [], "idempotency": "created"
  },
  "warnings": ["SKIPPED: graph snapshot was skipped; changed set only"],
  "enrichment": {"edges": "skipped", "sei": "unavailable", "...": "..."},
  "meta": {"local_only": true, "peer_side_effects": []}
}
```

`completeness: SKIPPED` and `source_version: no_index` mean loomweave was not
reachable, so there were no edges to capture. With loomweave **present and
indexed**, the same call returns `completeness: FULL` (or `DELTA` if some entities
failed), records the dated edges into `.weft/warpline/`, and a subsequent
`reverify` / `blast_radius` returns downstream entities with `reason: downstream`
and the `via_edges` that connect them. See [Federation](federation.md) for wiring
loomweave.

`capture_snapshot` is the **only** tool that writes anything beyond store
bookkeeping, and it writes only to `.weft/warpline/` — never to a sibling repo.

## 6. Install warpline as a federation member

To wire warpline into a project for an agent to use — MCP bindings, the ingest
hook, the agent skill, and config — run `install`, then verify with `doctor`:

```bash
warpline install --repo /path/to/project   # idempotent, atomic, symlink-safe
warpline doctor  --repo /path/to/project    # per-component report; --fix autofixes
```

`install` never clobbers a sibling member's config block. `doctor` exits non-zero
if anything is missing and prints a per-component report (`--json` emits a
`warpline.doctor.v1` summary). See the [CLI reference](reference/cli.md) for the
component list and exit codes.

## 7. The same loop from an MCP host

Everything above is available over the MCP stdio server (`warpline-mcp`). The loop
is identical:

1. `tools/list` — discover the surface (each tool's read/write posture,
   idempotency, repo requirement, touched paths, federation dependencies).
2. `warpline_change_list` (`changed`) — call first; read its `next_actions`.
3. `warpline_reverify_worklist_get` (`reverify`) — the worklist to recheck.
4. `warpline_impact_radius_get` / `warpline_entity_timeline_get` — for explanation.
5. `warpline_edge_snapshot_capture` (`capture_snapshot`) — when impact/reverify
   reports `NO_SNAPSHOT` and loomweave is available.

The [MCP tool reference](reference/mcp-tools.md) gives the exact request and
response envelope for each tool.

## Next steps

- [Concepts](concepts/index.md) — the mental model: temporal facts vs. the
  current graph, SEI consumption, blast-radius, the worklist, and the
  advisory-not-gating posture.
- [CLI reference](reference/cli.md) — every command, flag, and exit code.
- [MCP tool reference](reference/mcp-tools.md) — every tool's params and return
  shape.
- [Federation](federation.md) — how warpline composes with its siblings and how it
  degrades when one is absent.
