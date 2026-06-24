# Warpline

warpline is the Weft federation's **temporal / change-impact authority**. It owns
the one thing no other federation member stores — **per-entity change history
across runs, keyed on Loomweave SEI** — and the downstream-propagation query over
it. It answers, every session, the question an agent should ask before claiming a
change is done:

> Given this diff: which entities changed, by whom, when — what is
> downstream-affected over the call graph, and what must I re-verify?

The product front door lives at
[warpline.foundryside.dev](https://warpline.foundryside.dev/). These pages are the
reference docs, sourced from the repository.

## What warpline is — and is not

warpline is **advisory only**. It records temporal facts and computes blast-radius
and a re-verification worklist; it **never gates a change, never enforces a
policy, and never decides whether a change is allowed**. This is deconfliction
tooling, not security. A warpline answer is an enhancement you can act on or
ignore — never a verdict you must clear.

The federation split is deliberate:

- **loomweave owns "now"** — the point-in-time structural graph and SEI minting.
- **warpline owns "over time"** — dated change facts and dated edge snapshots.

warpline **consumes SEI, it never mints it**. Loomweave is the identity authority;
warpline stores the `loomweave:eid:...` value opaquely and refuses to become a
second identity authority. It stores only the temporal facts it owns; it never
mirrors Loomweave's live graph, so it can never become a stale duplicate of it.

warpline is **enrich-only and local-first**: it boots, ingests, and answers with no
sibling installed, all state under `.weft/warpline/` (git-ignored), and every
sibling fact it attaches is an enhancement a caller can omit.

## Install

warpline is a zero-dependency Python package (≥ 3.12). Install it as a
[uv](https://docs.astral.sh/uv/) tool to get the `warpline` and `warpline-mcp`
executables on your `PATH`:

```bash
uv tool install warpline
warpline --version          # warpline 1.0.0
```

```bash
pip install warpline        # alternative
```

## 30-second example

Ingest a repository's git history, then ask what changed in the last commit:

```bash
warpline backfill --repo /path/to/project --json
warpline changed  --repo /path/to/project --rev-range HEAD~1..HEAD
```

```json
{
  "schema": "warpline.change_list.v1",
  "ok": true,
  "data": {
    "items": [
      {
        "change_id": "warpline:change:3",
        "entity": {"locator": "python:function:src/demo/auth.py::login", "sei": null,
                   "warpline_entity_key_id": 1, "path": "src/demo/auth.py"},
        "change_kind": "modified", "actor": "...", "commit": "ea7c6f28...",
        "changed_at": "2026-06-14T03:53:39+10:00"
      }
    ],
    "changed_refs": [{"kind": "locator", "value": "python:function:src/demo/auth.py::login"}]
  },
  "next_actions": {
    "warpline_reverify_worklist_get": {"tool": "warpline_reverify_worklist_get",
      "arguments": {"repo": "...", "changed_entity_key_ids": [1], "depth": 2}}
  },
  "enrichment": {"sei": "absent", "edges": "absent", "work": "unavailable",
                 "risk": "unavailable", "governance": "unavailable", "requirements": "unavailable"},
  "meta": {"producer": {"tool": "warpline", "version": "1.0.0"},
           "local_only": true, "peer_side_effects": []}
}
```

The `next_actions` block hands back ready-to-call arguments for the next tool —
follow them straight into `warpline reverify` to get the worklist. The
[Getting Started](getting-started.md) guide walks this loop end to end.

## The six MCP tools

warpline exposes six frozen federation tools over an MCP stdio server. Each has an
endorsed name and a short shim alias that return identical schema and data.

| Endorsed name | Shim | Schema | Role |
| --- | --- | --- | --- |
| `warpline_change_list` | `changed` | `warpline.change_list.v1` | Changed entities for a rev range; hands back ready-to-call next actions. **Call first.** |
| `warpline_entity_timeline_get` | `timeline` | `warpline.entity_timeline.v1` | Ordered change history for one entity; reports `sei_resolution` only, never lineage. |
| `warpline_entity_churn_count_get` | `churn` | `warpline.entity_churn_count.v1` | Per-entity change-event counts; a never-observed entity is `churn_count: 0`. |
| `warpline_impact_radius_get` | `blast_radius` | `warpline.impact_radius.v1` | Downstream affected set with mandatory `completeness` + `staleness`. |
| `warpline_reverify_worklist_get` | `reverify` | `warpline.reverify_worklist.v1` | The agent worklist to recheck before claiming completion. |
| `warpline_edge_snapshot_capture` | `capture_snapshot` | `warpline.edge_snapshot.v1` | The only mutating tool; captures dated loomweave edges into `.weft/warpline/`. |

The full request/response shape for each tool is in the
[MCP tool reference](reference/mcp-tools.md). The CLI verbs that mirror them are in
the [CLI reference](reference/cli.md).

## Where warpline sits in the federation

warpline is the **5th admitted member** of the Weft federation. It composes
pairwise with its siblings, always enrich-only:

- It **consumes** Loomweave SEI resolution and dated structural edges (the only
  proven, frozen inbound seam) and Filigree work-state links.
- It **feeds** advisory change-impact facts to governance-style surfaces
  (Legis/Plainweave): what changed and what is downstream-affected. It never decides
  whether the change is allowed.
- It **degrades honestly** when a sibling is absent — the answer reports
  `unavailable`, never an implied "clean" or "allowed" state.

See [Federation](federation.md) for the seam contracts and degrade behavior.

## Reading the docs

| If you want to… | Read |
| --- | --- |
| Get from install to your first worklist | [Getting Started](getting-started.md) |
| Understand the mental model | [Concepts](concepts/index.md) |
| Look up a CLI command, flag, or exit code | [CLI reference](reference/cli.md) |
| Look up an MCP tool's params and return shape | [MCP tool reference](reference/mcp-tools.md) |
| Wire warpline into a federation of sibling tools | [Federation](federation.md) |

## Honest status

warpline is at v1.0.0 and production-stable for its own surface, with caveats it
states in the open:

- The Loomweave inbound seam is **proven and frozen** — real SEI resolution and
  edge capture against the live sibling. The Filigree work-state read is
  **earned** (consumed by golden vectors). The wardline risk seam and the legis
  rename feed are **reserved-shape and non-binding** — present in the contract,
  not yet driven by a real sibling. warpline reports those as `unavailable`/`absent`
  rather than pretending they are wired.
- Entity extraction is Python-aware (it derives `python:function:` /
  `python:class:` locators from `.py` sources); other file types are tracked at
  `file:<path>` granularity.
- Blast-radius is only as complete as the captured snapshot. A thin answer is
  reported thin: `completeness: NO_SNAPSHOT` means "changed set only," never
  "nothing is affected."
