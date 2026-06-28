# 01 — Discovery Findings (Holistic Assessment)

> Scope: `src/warpline/` at HEAD `def6d43`. Evidence-based; confidence noted per claim.

## 1. What warpline is

warpline is the **temporal / change-impact authority** of the **Weft federation** — a family of
local-first developer tools (loomweave, filigree, wardline, legis/plainweave, warpline). It owns the
one fact no sibling stores: **per-entity change history across git history, keyed on SEI**, plus the
downstream-propagation query over it. It answers the question an agent asks before claiming a change
is done:

> *Given this diff: which entities changed, by whom, when — what is downstream-affected over the
> call graph, and what must I re-verify?*

Two design commitments shape every line of the codebase (confidence: **High** — stated in README and
enforced structurally throughout `commands.py` / `envelope.py`):

1. **Advisory, never gating** ("deconfliction-first"). warpline enriches; it never enforces policy
   or decides whether a change is allowed. It *feeds* facts to governance siblings (legis/plainweave)
   that run their own policy.
2. **Enrich-only, local-first.** It boots, ingests, and answers with **no sibling installed**. All
   state lives under `.weft/warpline/` (git-ignored); the only mutating tools write there and never
   touch a sibling repo. Every response carries `meta.local_only: true`, `peer_side_effects: []`.

## 2. Technology stack

| Concern | Choice | Evidence |
| --- | --- | --- |
| Language | Python ≥ 3.12 (uses 3.12+ generics, `X | Y` unions, `match`-era stdlib) | `pyproject.toml` |
| Runtime deps | **None** — pure stdlib (`sqlite3`, `subprocess`, `urllib`, `argparse`, `json`, `hashlib`, `selectors`) | `pyproject.toml:24` |
| Persistence | Embedded **SQLite** (WAL, `RETURNING` → floor 3.35.0), forward-only migrations | `store.py:14-17,35-107` |
| Interfaces | **CLI** (`argparse`) + **MCP server** (hand-rolled JSON-RPC over stdio) | `cli.py`, `mcp.py` |
| Identity | Consumes **loomweave SEI** (`loomweave:eid:…`); never mints/parses it | `loomweave.py`, README |
| Packaging | hatchling; ships `skills/` payload as wheel artifact; uv-tool install | `pyproject.toml:42-61` |
| Quality gates | `mypy --strict`, `ruff`, `pytest` + 14 golden contract vectors | `pyproject.toml:63-77`, README |

The **zero-runtime-dependency** posture is the single most distinctive stack fact: warpline is
installable as a self-contained uv tool / pip package with no transitive supply chain, consistent
with the rest of the federation.

## 3. Directory & module organization

`src/` is a **flat package** — `src/warpline/*.py` (no nested sub-packages) plus a non-code
`skills/warpline-workflow/` payload (the injectable agent skill). The 30 modules organize by
**architectural layer**, not by directory. Module sizes (LOC):

```
store.py 1863 · commands.py 1486 · mcp.py 777 · cli.py 601 · dogfood.py 575 · install_support.py 513
listing.py 437 · loomweave.py 433 · cop.py 428 · federation.py 418 · git.py 324 · snapshot.py 257
_attest.py 250 · mcp_smoke.py 245 · _completeness.py 225 · siblings.py 191 · verification.py 180
_blast.py 159 · _enrichment.py 146 · errors.py 139 · productization.py 123 · reverify.py 117
propagation.py 105 · envelope.py 105 · reresolve.py 95 · refs.py 78 · coupling.py 77
install.py 27 · locators.py 26 · __init__.py 11
```

## 4. Entry points & runtime flows

Two real entry points (loomweave `entity_entry_point_list`, filtered of `heddle.*` tombstones):

- **`warpline.cli:main`** (`cli.py:381`, fan_out 31) — argparse dispatcher for `install`, `doctor`,
  `backfill`, `ingest-commit`, `changed`, `timeline`, `churn`, `capture-snapshot`, `reverify`,
  `verify-record`, `project-status`, `reresolve`, `co-change`, `cop`, `mcp-smoke`, `dogfood-eval`.
- **`warpline.mcp:main`** (`mcp.py:758`) — JSON-RPC stdio loop exposing **8 tools** (6 frozen
  federation contracts + 2 additive: `verify_record`, `project_status`), each with endorsed name +
  short shim returning identical schema+data.

**The core loop** (both surfaces converge on `commands.py`):
`backfill`/`ingest-commit` (git → store) → `changed` → `capture-snapshot` (loomweave edges → store)
→ `impact_radius` / `reverify` (store + edges → worklist). A post-commit git hook keeps the store
fresh; a SessionStart hook emits `commands.session_context`.

## 5. Subsystem identification (8 layered subsystems)

Derived from imports, the loomweave edge graph, and module docstrings. Confidence **High**
(decomposition cross-checked against `commands.py` import block and coupling hotspots).

| # | Subsystem | Modules | Role |
| --- | --- | --- | --- |
| **S1** | Contract & Envelope Foundation | `errors`, `envelope`, `_enrichment`, `listing`, `refs`, `locators` | Frozen output envelope, closed error/enrichment/reason vocabularies, input-ref parsing, list ergonomics (filter/sort/page/overflow) |
| **S2** | Temporal Store (persistence) | `store`, `snapshot` | SQLite schema + forward-only migrations + `WarplineStore` data-access (40 methods); edge-snapshot capture orchestration |
| **S3** | Domain Compute (pure analytics) | `_blast`, `propagation`, `_completeness`, `coupling`, `verification`, `_attest`, `reverify` | Pure functions: blast-radius traversal, impact-completeness, co-change coupling, verification-freshness, attest risk, worklist render |
| **S4** | Command Orchestration | `commands`, `cop` | The 8 tool bodies; wires store + compute + seams + envelope; COP posture composition |
| **S5** | Resolution & Ingestion Seams | `loomweave`, `git`, `reresolve` | loomweave SEI/edge resolution (subprocess MCP client); git history ingestion; self-healing SEI re-resolution |
| **S6** | Federation Enrichment Seams | `federation`, `siblings` | Cross-member consults: filigree work-state, wardline risk dossier, legis governance read |
| **S7** | Interface Surfaces | `cli`, `mcp`, `mcp_smoke` | argparse CLI; JSON-RPC MCP server; live stdio smoke test |
| **S8** | Lifecycle & Productization | `install`, `install_support`, `productization`, `dogfood` | Federation member install/doctor; release-readiness decision; dogfood evaluation harness |

## 6. Architecture style (first read)

**Layered + ports-and-adapters (hexagonal).** A pure domain core (S2 store + S3 compute) sits behind
the S4 command layer; external systems are reached only through **`typing.Protocol` ports**
(`ToolClient`, `NeighborhoodClient`, `WorkClient`, `RiskClient`, `LegisClient`, `RenameFeed`) whose
concrete adapters live in S5/S6. Two thin surfaces (S7) translate transport (argparse / JSON-RPC) to
the same `commands.py` functions — confirmed by `cli.py` and `mcp.py` both importing `commands` and
delegating. This is a deliberate, consistently-applied pattern, not incidental.

## 7. Cross-cutting design invariants (the "house style")

These recur across subsystems and are the spine of the system's correctness story (confidence
**High** — observed directly in code):

- **Honesty invariant.** Absence is explicit: a **closed enrichment vocabulary**
  (`present | absent | unavailable`, plus `stale|partial|skipped` for edges; `envelope.py:12-20`).
  `absent` (peer present, no fact) is never conflated with `unavailable` (peer unreachable), and
  neither is ever a transport error or an implied "clean/allowed" state.
- **weft-reason (G1).** A degraded/empty result carries `{reason_class, cause, fix}` over **11 closed
  reason classes** so an empty is never byte-indistinguishable from an earned true-negative
  (`listing.py:14-33`).
- **Frozen contracts.** 8 `warpline.<contract>.v1` schema URIs + `warpline.error.v1` (11 closed
  error codes × 3 retryability values, `errors.py:8-23`). A `v2` is a **new URI**, never a mutation
  of `v1`. The authoritative interface-lock is **hub-owned**; warpline implements *to* it.
- **SEI-orthogonality.** warpline keys on loomweave SEI but mints/parses no identity; the SEI is an
  opaque external string joined at read time, never stored in derived tables (`store.py:177-179`).
- **Additive, forward-only schema.** Base `SCHEMA` frozen after Rung 1a; all change via ordered
  `MIGRATIONS` (v2/v3/v4) under `BEGIN IMMEDIATE` atomicity with a **schema-presence floor** that
  re-runs migrations when a version marker isn't backed by on-disk objects (`store.py:469-630`).
- **Fail-soft advisory side effects.** The pure traversal (`blast_radius`) never does I/O; side
  effects (lazy snapshot capture, attest hashing) live in tool bodies wrapped in `except Exception`
  so an unreachable loomweave degrades to `NO_SNAPSHOT`, never an error or a fake-clean graph
  (`commands.py:529-560, 674-675`).

## 8. Evolution narrative ("Rungs")

The code is annotated with an incremental build ladder (confidence **High** — pervasive in
docstrings + CHANGELOG):

- **Rung 1a** froze the base `SCHEMA`; **1b** added working-context anchor columns (v2); **1c** added
  self-healing SEI re-resolution (`reresolve`); **1d** added always-on lazy edge-snapshot capture.
- **Rung 2** added Track **A** co-change coupling (v3), Track **B** verification freshness (v4),
  Track **C** per-item risk/governance enrichment, Track **D** the COP posture frame.

Decisions are PDR-governed (e.g. PDR-0023 "no advertise-and-ignore dead input"; GV-LG-1 "governance
is an echo, never a warpline verdict"). This is a **disciplined, contract-first, incrementally-built
system**, not an organically-grown one.

## 9. Open questions carried into the catalog

- Does `store.py`'s size (1863 LOC, one class with 40 methods) cross from "cohesive" into
  "god-module"? → Quality assessment.
- Is `reverify_worklist` (276 LOC, fan_out 34, orchestrating ≥8 concerns) the system's complexity
  hotspot? → Quality assessment.
- Are the 3 `test_attest.py` HighEntropyHex findings synthetic fixtures (waivable) or real? → Quality
  assessment (`.env` is confirmed git-ignored).
