# Warpline Spike Report

Readiness verdict: ready

Current readiness verdict as of 2026-06-13: Warpline is product-candidate ready.
Owner admission, glossary freeze, and sibling-side tickets remain reserved, but
the Warpline-side product bar is now backed by executable evidence instead of the
earlier bounded spike alone.

Live-review blockers retired in this repo:

- Standalone parity: `dogfood-eval` now requires a real-member benchmark
  against Lacuna, with an executed `git diff --name-only` plus `rg` baseline.
  The current run matched changed paths through MCP and produced a non-empty
  `reverify` worklist.
- Federation uplift: the real-member lane captures a dated snapshot through
  actual Loomweave MCP before `changed -> reverify`; the current run captured
  522 Loomweave edges and returned 4 reverify work items. Seeded federation
  cases remain smoke coverage only.
- MCP and federation-bar defects: malformed MCP input and tool exceptions
  degrade recoverably, `initialize` returns protocol/server metadata, tools
  advertise output schemas, default state is `.weft/warpline/`, the store writes
  a nested `.gitignore`, and hostile/undecodable files degrade per file rather
  than killing the run. `warpline mcp-smoke` also proves a real stdio
  initialize/tools/list/changed/bad-input/tools-list survivability path.

## Q1: Loomweave Read Path

Status: available.

Evidence from `uv run warpline loomweave-probe --repo <loomweave-root> --json`:

```json
{
  "status": "available",
  "version": "loomweave 1.1.0-rc4",
  "required_tools_present": [
    "project_status_get",
    "entity_find",
    "entity_resolve",
    "entity_neighborhood_get",
    "entity_callers_list",
    "entity_source_get"
  ]
}
```

The live tool inventory also includes `entity_high_churn_list` and `entity_recent_change_list`, which are relevant to later pairwise integration but remain Loomweave-owned current-structure/read-surface behavior.

## Q1b: Edge Snapshot Adapter

Unit evidence confirms Warpline preserves caller/callee direction from Loomweave neighborhood payloads. Live evidence confirms `<loomweave-root>` exposes `entity_neighborhood_get`; Warpline still records dated snapshots only and does not answer current structure as its own authority.

## Q2: Snapshot Honesty and Planted-Change Results

The spike harness uses a bounded planted git repository for repeatable measurements and live member checks only for lightweight federation surface probes. An earlier unbounded live-member backfill attempt against `<filigree-root>` exceeded four minutes, so the release harness was refactored to avoid making Warpline harder to operate than current grep/manual workflows.

Current measured evidence from `spike/measurements.json`:

- `changed_latency_ms`: 48.793924
- `backfill_events_per_second`: 24.52472433106239
- `hook_ingest_exit_code`: 0
- `planted_recall`: 1.0
- `snapshot_completeness`: `NO_SNAPSHOT`

The planted-change query returned `python:function:planted.py::planted` for `HEAD~1..HEAD`, with absent SEI and edge enrichment reported explicitly rather than hidden.

## Q3: Doctrine Firewall Checklist

- Warpline imports no sibling packages.
- Warpline stores temporal change and dated snapshot facts only.
- Warpline does not own current structure, work state, trust policy, governance, or requirements.
- Member dirty state can be compared against `docs/evidence/member-dirty-baseline.txt`
  only as an explicit local opt-in (`WARPLINE_CHECK_MEMBER_DIFFS=1`); release and
  spike gates do not depend on sibling working-tree drift by default.
- Missing graph enrichment produces `NO_SNAPSHOT`, `SKIPPED`, or absent enrichment fields.

## Q4: Grep-Test Dogfood Notes

The release dogfood path now runs a real-member benchmark instead of relying on
the planted corpus for parity. It clones `<lacuna-root>`, copies the live
Loomweave index, backfills Warpline, runs MCP `capture_snapshot`, selects a
historical code change with non-empty reverify output, executes the baseline
`git diff --name-only` plus `rg` workflow, then compares MCP `changed ->
reverify` output against that baseline. The current benchmark uses
`dd7c0ff3d30a4786945d3fff851f7f175f2826ee^..dd7c0ff3d30a4786945d3fff851f7f175f2826ee`,
matches `.gitignore`, `Makefile`, `tests/test_steps.py`, and `tour/steps.py`,
captures 522 Loomweave edges, and returns 4 reverify items.

Historical bounded-spike recommendation: go

Recommendation: go
