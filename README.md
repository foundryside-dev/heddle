# Heddle - temporal / change-impact authority (product candidate)

**Status: PRODUCT CANDIDATE - readiness evidence passes; owner admission still reserved.**
Name is a placeholder per federation doctrine §8.

Heddle is a candidate Weft federation member: a bounded **temporal-graph
authority** owning the one thing no existing member stores — **per-entity change
history across runs, keyed on SEI** — and the downstream-propagation query over
it. It exists to answer, mechanically, every agent's every-session question:

> *Given this diff: which entities changed, by whom, when — what is
> downstream-affected over the call graph, and what must be re-verified?*

Today that question is answered by grep-plus-hope or human blast-radius review
(= supervision load). Loomweave deliberately stores only the point-in-time
graph; its `high_churn` / `recently_changed` tools are dead no-ops because no
member keeps history. Heddle's claim: **Loomweave owns "now"; Heddle owns "over
time."**

## Governing artifacts

| What | Where |
|---|---|
| Spike ticket (go/no-go) | `weft-e4589e6570` in the weft hub tracker |
| Discovery mandate | weft `pm/product/decisions/0013-…` (Heddle = discovery slot #1) |
| Concept source | weft `roadmap-ideas.md` §3 "Heddle" |
| Federation doctrine (binding) | weft `doctrine.md` — esp. §5 enrich-only, §6 not-an-aggregator, §7 admission test (owner-reserved), §8 naming |
| Identity contract (frozen) | weft `sei-standard.md` — LOCKED 2026-06-05 |
| Product workspace | [`docs/product/`](docs/product/) — vision, roadmap, metrics, PDRs, PRDs, MCP product bar |
| Design workspace | [`solution-architecture/`](solution-architecture/) — numbered artifact set, tier M |
| Spike brief | [`spike/SPIKE-BRIEF.md`](spike/SPIKE-BRIEF.md) — the go/no-go questions and kill criteria |

## Product posture

Heddle is now treated inside this repo as a first-class product candidate. Its
primary user is the coding agent trying to finish or review a change without
guessing at blast radius. The MCP surface is therefore a product surface, not a
transport wrapper: if an agent cannot discover and use Heddle from `tools/list`
and structured responses alone, that is a P0 product defect. The minimum bar is
solo-mode parity with existing tools and better answers when federation member
enrichment is present.

The 2026-06-13 live review found the prototype below that bar. Since then,
production SEI resolution, production edge snapshot capture, MCP recovery
hardening, a real-member dogfood evaluator, and an MCP stdio smoke command have
landed. The current readiness verdict in [`spike/REPORT.md`](spike/REPORT.md)
is `ready`; admission and sibling-side tickets remain owner-gated.

Federation admission is still not claimed here. The current product decision is
recorded in [`docs/product/decisions/0001-product-candidate-ownership.md`](docs/product/decisions/0001-product-candidate-ownership.md):
Heddle may be developed and evaluated as a product candidate, while admission,
wire freeze, glossary clearance, sibling tickets, and outward-facing release
decisions remain owner-gated.

## MCP-first quick start

Run from this checkout with `uv run` during development:

```bash
uv run heddle --version
uv run heddle mcp-smoke --repo . --json
uv run heddle dogfood-eval --real-member-repo /home/john/lacuna --json
```

The smoke command starts a real stdio MCP server conversation, sends
`initialize`, lists tools, calls `changed`, verifies a structured bad-input
error, and proves the server still answers after the tool error. Treat a smoke
failure as a product regression, not a docs problem.

## Core workflow

For a local repo:

```bash
uv run heddle init --repo .
uv run heddle backfill --repo . --json
uv run heddle changed --repo . --rev-range HEAD~1..HEAD --json
uv run heddle capture-snapshot --repo . --json
uv run heddle reverify --repo . --changed-entity-key-id 1 --json
```

For MCP hosts, the same product flow is:

1. `tools/list`
2. `changed`
3. `reverify`
4. `blast_radius` or `timeline` when the agent needs explanation
5. `capture_snapshot` when edge enrichment is missing or stale

`tools/list` advertises each tool's read/local-write behavior, idempotency,
repo requirement, touched local paths, concurrency posture, and federation
dependencies. Current tool names are compatibility shims; the proposed
endorsement names and future contract shapes are in
[`docs/product/federation-value-add-and-mcp-first-audit.md`](docs/product/federation-value-add-and-mcp-first-audit.md).

| Tool | MCP role | Local state |
| --- | --- | --- |
| `changed` | List temporal change facts for a repo and rev range; returns ready-to-call reverify arguments. | Reads and may populate Heddle local state. |
| `timeline` | Return ordered history for one entity locator or key. | Reads Heddle local state. |
| `blast_radius` | Return downstream affected entities from dated snapshots. | Reads Heddle local state. |
| `reverify` | Return the agent-facing worklist for what to reverify. | Reads Heddle local state. |
| `capture_snapshot` | Capture dated Loomweave edges into Heddle state. | Writes only `.weft/heddle/`; never mutates sibling repos. |

## Evidence gates

Before calling the product candidate ready, run:

```bash
uv run ruff check .
uv run mypy
uv run pytest
scripts/check_release_candidate.sh
```

`scripts/check_release_candidate.sh` runs the spike harness, dogfood evaluator,
productization gate, static checks, tests, and member-diff guard. The current
evidence records are:

- [`spike/REPORT.md`](spike/REPORT.md) - readiness verdict and live-review
  blocker closure.
- [`docs/evidence/2026-06-13-dogfood-readiness.md`](docs/evidence/2026-06-13-dogfood-readiness.md)
  - real-member baseline parity and Loomweave uplift.
- [`docs/evidence/2026-06-13-mcp-smoke.md`](docs/evidence/2026-06-13-mcp-smoke.md)
  - MCP initialize, tool inventory, structured error, and survivability check.

## Standing constraints (read before touching anything)

1. **Zero changes to the four launch members** (filigree, wardline, legis,
   loomweave) until the clean-break cutover lands — owner directive 2026-06-10.
   Heddle is read-side only against their published surfaces. Consumer wiring
   inside members is designed here but **deferred** (see `06-` and `15-`).
2. **Enrich-only, never load-bearing** (doctrine §5). Heddle must boot, ingest,
   and answer with no sibling installed.
3. **Not an aggregator** (doctrine §6). Heddle stores only what it is
   authoritative for — temporal change data. It never mirrors a sibling's
   system of record. This is the spike's central question; see ADR-0004.
4. **Member admission is the owner's call** (doctrine §7). This workspace
   authorizes design + spike work only. A "go" result produces an admission
   recommendation, not an admission.
