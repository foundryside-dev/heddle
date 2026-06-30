# 00 — Coordination Plan

## Analysis Configuration

- **Subject**: `warpline` — Weft federation temporal / change-impact authority (v1.2.0)
- **Scope**: `src/warpline/` only — 30 `.py` files, ~10,411 LOC, flat package + `skills/` payload
- **Deliverables**: **Option C (Architect-Ready)** — discovery, catalog, diagrams, final report, quality assessment, architect handover
- **Strategy**: **HYBRID** (see Orchestration Decision)
- **Time constraint**: none stated
- **Complexity estimate**: **Medium** — small file count, but high per-module conceptual density (contract-first, honesty-invariant design); one god-module (`store.py`) and one god-function (`reverify_worklist`)

## Subject Snapshot (evidence)

| Signal | Value | Source |
| --- | --- | --- |
| Language / runtime | Python ≥ 3.12, `mypy --strict`, ruff (E,F,I,UP,B) | `pyproject.toml` |
| Runtime dependencies | **0** (stdlib only) | `pyproject.toml:24` |
| Entry points | `warpline.cli:main`, `warpline.mcp:main` | `pyproject.toml:34-36` |
| LOC (src) | 10,411 across 30 files | `find/wc` |
| Largest modules | `store.py` 1863, `commands.py` 1486, `mcp.py` 777, `cli.py` 601 | `wc -l` |
| Loomweave index | **fresh** at HEAD `def6d43` (112 files, 1076 entities, 2667 edges) | `index_diff_get` (authoritative oracle) |
| Circular imports | **0** | `module_circular_import_list` |
| Foundation hub | `warpline.store` — fan_in **38**, fan_out **0** (internal) | `entity_coupling_hotspot_list` |
| Orchestration hub | `commands.reverify_worklist` — fan_out **34**, 276 LOC | `entity_coupling_hotspot_list` |
| Prior name | `heddle` (renamed to warpline; loomweave carries `heddle.*` tombstones) | `index_diff_get.missing_files` |

## Orchestration Decision

The command's PARALLEL trigger requires **≥5 subsystems AND ~20K+ LOC AND loosely coupled**. This
codebase meets only one of three: it is **10.4k LOC** (half the threshold) and a **tightly-coupled
flat package** (`store.py` is a god-module everything imports; `cli`/`mcp` are thin surfaces over
`commands.py`). The command's SEQUENTIAL trigger ("tight interdependencies") fits better.

Decisive factor: the loomweave graph (2667 edges + coupling hotspots) **already holds** the
inbound/outbound dependency backbone — the most valuable and most error-prone field in every catalog
entry. Fanning out blind explorers would reconstruct that *worse* and cost more. So:

- **Catalog (02), diagrams (03), discovery (01), report (04), handover (06)** — self-authored from
  the loomweave graph + targeted full reads of the behavior-critical modules (`store.py`,
  `commands.py`) and symbol-level reads of the rest.
- **Quality (05)** — independent critique genuinely beats self-assessment, so dispatch the
  `architecture-critic` and `debt-cataloger` subagents, fed the coupling hotspots + loomweave
  findings. Synthesize their output.
- **Validation gates (mandatory)** — `analysis-validator` after the catalog and after the final set.

## Execution Log

- `2026-06-28 07:28` Created workspace `docs/arch-analysis-2026-06-28-0728/`.
- `2026-06-28 07:28` Orientation: confirmed Python (not Rust), flat `src/warpline/` package, zero deps.
- `2026-06-28 07:29` Resolved freshness conflict — `index_diff_get` authoritative = **fresh** at HEAD; no re-analyze.
- `2026-06-28 07:30` Advisor checkpoint #1: right-sized orchestration to HYBRID; locked decomposition.
- `2026-06-28 07:32` Verified guessed modules (cop/listing/productization/_attest/verification); decomposition = 8 layered subsystems.
- `2026-06-28 07:34` Deep-read `commands.py` (full) + `store.py` (schema, migrations, binding, reresolve) + `errors.py`; pulled coupling hotspots, findings, store API inventory.
- `2026-06-28 07:36` Wrote 00 / 01 / 02 / 03 / 04.
- `2026-06-28 07:36` Dispatched 3 parallel background agents: `analysis-validator` (catalog gate),
  `architecture-critic`, `debt-cataloger`. Independently cross-checked TODO/FIXME (zero) + the
  `test_attest` secret findings (false positives — content hashes, not credentials).
- `2026-06-28 07:55` `debt-cataloger` → `temp/debt-catalog.md` (12 items, 1 High = D2 FK-less tables;
  caught the inert `# noqa: BLE001`).
- `2026-06-28 07:59` `analysis-validator` → `temp/validation-catalog.md`: **PASS-WITH-FIXES**. Caught an
  S2↔S3 back-edge (`store`→`coupling`, lazy) + 4 missed cross-edges (function-body imports loomweave's
  graph omits) + minor count fixes. **All fixes applied** to 02 / 03 / 04.
- `2026-06-28 08:01` `architecture-critic` → `05-quality-assessment.md`: **4/5**, F1-F11; added F5
  (silent-correctness positional invariant) + F4 (throttle gap) beyond the debt pass. Reconciled the
  "single-direction" claim in 05 against the corrected catalog.
- `2026-06-28 08:0x` Wrote `06-architect-handover.md` (unified F↔D backlog U1-U17, 3-wave sequence).
- `2026-06-28 08:0x` Final validation gate: `analysis-validator` over the full set for cross-document
  consistency → `temp/validation-final.md`.

## Limitations

- Scope is `src/` only: `tests/`, `contracts/`, `site/`, `solution-architecture/`, `spike/`,
  `scripts/` are referenced for context (testing posture, frozen schemas) but **not catalogued**.
- `store.py` was deep-read through line 1342 + full method inventory of the remainder (lines
  1343-1864 cover `churn_for_entity`, `update_co_change_pairs`, `co_change_partners`,
  snapshot-write methods, `capture_snapshot_atomic`); their behavior is inferred from signatures +
  docstrings, not line-by-line for the second half. Confidence: High (the read half establishes the
  module's patterns conclusively).
