# 04 — Final Report

**Subject:** `warpline` v1.2.0 — Weft federation temporal / change-impact authority
**Scope:** `src/warpline/` (30 modules, ~10.4k LOC) at HEAD `def6d43`
**Date:** 2026-06-28 · **Deliverable tier:** C (Architect-Ready)
**Overall confidence:** **High** (core modules read in full; structure cross-checked against the
loomweave 2667-edge graph)

---

## Executive summary

warpline is a **small, dense, exceptionally disciplined** Python service. In ~10k lines and **zero
runtime dependencies** it implements a temporal change-impact engine over git history and a loomweave
edge graph, exposed identically through a CLI and an MCP server. Its defining quality is not size but
**rigor**: a frozen, hub-owned wire contract; closed vocabularies enforced by assertion; an "honesty
invariant" that makes the *absence* of a fact (peer down vs. peer-present-but-empty vs. true-negative)
a first-class, machine-distinguishable value everywhere; and forward-only SQLite migrations with real
concurrency and corruption-recovery handling.

The architecture is a clean **layered + ports-and-adapters** design: a pure, testable domain core
(SQLite store + side-effect-free compute) sits behind a command-orchestration layer, reaches all
external systems through `typing.Protocol` ports, and is fronted by two thin transport surfaces. The
module-import graph is **acyclic**; the one structural blemish is a **subsystem-level S2↔S3 back-edge**
(`store` reaches into the `coupling` compute module via deliberate lazy imports), kept module-acyclic
only by a documented workaround.

The two real architectural pressure points are **concentration**, not disorder: `store.py` (1863 LOC,
one 40-method class) and `commands.reverify_worklist` (276 LOC, fan-out 34) hold a disproportionate
share of the system's behavior. Neither is broken; both are the natural candidates for the next
refactor and the places where future change will be slowest and riskiest. Detailed quality findings
are in **05**; the prioritized improvement path is in **06**.

**Verdict:** a production-stable (`Development Status :: 5`), well-engineered system whose debt is
*localized and known* rather than diffuse. The risk profile is "a few load-bearing hotspots," not
"pervasive rot."

---

## What the system does (one paragraph)

Given a git diff, warpline answers: **which entities changed, by whom, when; what is downstream-affected
over the call/reference graph; and what must be re-verified before the change is called done.** It
*owns* per-entity change history keyed on loomweave SEI (the one fact no sibling stores) and the
propagation query over edge snapshots it captures from loomweave. It is **advisory only** — it enriches
and deconflicts, never gates or enforces policy — and **local-first** — it boots and answers with no
sibling installed, writing only under `.weft/warpline/`.

---

## Architecture at a glance

| Dimension | Finding |
| --- | --- |
| Style | Layered + ports-and-adapters (hexagonal); `Protocol` ports for every external system |
| Layers | S1 Contract → S2 Store → S3 Pure Compute → S4 Commands → {S5 Resolution, S6 Federation} → S7 Surfaces; S8 Lifecycle out-of-band |
| Coupling | Module-acyclic (one S2↔S3 subsystem back-edge: `store`→`coupling`, lazy); foundation hub `store.py` (fan_in 38, fan_out 0); orchestration hub `commands.py` |
| Persistence | Embedded SQLite (WAL), forward-only migrations (v1→v4), schema-presence-floor recovery |
| Interfaces | CLI (argparse) + MCP (JSON-RPC/stdio), both over one `commands.py` core → guaranteed parity |
| Contract | 8 frozen `warpline.<contract>.v1` + `warpline.error.v1` (11 closed codes); hub-owned interface-lock |
| Dependencies | **Zero** runtime deps (pure stdlib) |
| Quality gates | `mypy --strict`, ruff, pytest + 14 golden contract vectors, dogfood eval harness |

---

## Key strengths (evidence-based)

1. **Contract-first discipline.** Every tool returns one frozen envelope; error/enrichment/reason
   vocabularies are *closed* and asserted (`errors.py:52-53`, `envelope.py:12-20`). A `v2` is a new
   URI, never a `v1` mutation. This is the most defensible part of the design.
2. **The honesty invariant.** `absent` (peer present, no fact) ≠ `unavailable` (peer unreachable) ≠
   transport error ≠ clean state — encoded structurally, not by convention. Degraded results carry
   `{reason_class, cause, fix}` over 11 closed classes (`listing.py:14-33`). An empty answer is never
   byte-indistinguishable from an earned true-negative. This is rare and valuable.
3. **A genuinely pure domain core.** `blast_radius` does no I/O; `verification`/`reverify` take
   injected callbacks/ports. The compute layer (S3) is unit-testable without a DB or git — the kind of
   seam most systems claim and few achieve.
4. **Serious persistence engineering.** Forward-only migrations under `BEGIN IMMEDIATE`, concurrent-open
   safety (`busy_timeout` + re-read under RESERVED lock), a schema-presence floor that re-runs
   migrations when a version marker isn't backed by on-disk objects, UTC-normalized ordering to dodge
   mixed-tz lexical-sort bugs (`store.py:1140-1191`), and a strictly-read-only binding probe. This is
   not toy SQLite usage.
5. **Operational honesty under degradation.** Fail-soft advisory side effects (lazy snapshot capture,
   attest hashing) never block or fake a read; an unreachable loomweave degrades to `NO_SNAPSHOT`, a
   throttle marker prevents repeated spin-up cost, and recovery is retried automatically.
6. **Zero supply chain.** No runtime dependency means no transitive CVE surface — a real, deliberate
   security/operability win for a tool meant to be installed broadly.

---

## Key risks (summary — detail in 05)

1. **`store.py` god-module** (1863 LOC: DDL + migration runner + binding probe + 40-method class).
   Cohesive but oversized; the locus of slowest future change. **Med.**
2. **`reverify_worklist` god-function** (276 LOC, fan-out 34, ≥8 orchestrated concerns). The system's
   complexity peak; hard to test below the integration level. **Med-High.**
3. **Manual referential integrity on FK-less tables** (`co_change_pairs`, `snapshot_edges`) in the
   ~270-LOC `_merge_into_twin` family — correct today, fragile to future edits. **Med.**
4. **Read-path `except Exception` swallows** (lazy capture, attest, session_context) — robust by
   intent, but they can hide genuine bugs; observability covers the store path (`health_log`) but not
   these read swallows. **Low-Med.**
5. **Orchestration glue stranded in `commands.py`** rather than the S3 compute layer (lazy-capture
   throttle, attest hashing, federation enrichment merge, verification cache). **Low-Med.**
6. **Sibling-seam brittleness** (S6): three transports (filigree HTTP, legis/wardline CLI) each with
   their own parsing/failure surface — mitigated by mirrored schemas + consumer rejection tests. **Low.**

> The independent `architecture-critic` and `debt-cataloger` passes (see 05 and `temp/`) refine
> severity and add specifics; this list is the synthesized view.

---

## Notable archaeology

- **Renamed from `heddle`.** The loomweave index still carries `heddle.*` tombstone entities; the DB
  was migrated across the rename. Cosmetic, but explains the dual names in graph queries.
- **Built in "Rungs."** The code documents an explicit incremental ladder (Rung 1a frozen schema → 1b
  anchor columns → 1c SEI self-heal → 1d lazy capture; Rung 2 Track A co-change → B verification
  freshness → C risk/governance enrichment → D COP frame), governed by numbered PDRs. This is a
  deliberately, traceably evolved system.

---

## How to read this analysis

| If you want… | Read |
| --- | --- |
| The holistic lay of the land | `01-discovery-findings.md` |
| Per-subsystem detail + dependencies | `02-subsystem-catalog.md` |
| Visual context / container / component / data model / flow | `03-diagrams.md` |
| Code-quality assessment + debt inventory | `05-quality-assessment.md` |
| What to do next (prioritized) | `06-architect-handover.md` |
| Validation evidence | `temp/validation-*.md`, `temp/debt-catalog.md` |
