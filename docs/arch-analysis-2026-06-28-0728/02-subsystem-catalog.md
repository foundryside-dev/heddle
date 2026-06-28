# 02 — Subsystem Catalog

> 8 layered subsystems over `src/warpline/` (30 modules). Dependency directions derived from import
> blocks + the loomweave edge graph (2667 edges). `heddle.*` tombstone edges excluded.

Layer order (foundation → surface): roughly **{S1, S2} → S3 → S4 → {S5, S6} → S7**, with **S8** as an
out-of-band lifecycle/eval band. **S1 and S2 are *parallel* foundations** (neither imports the other:
`store.py` has no module-level internal imports; S1 imports nothing from S2). There are **no
module-level circular imports** (`module_circular_import_list` = 0) — but at *subsystem* granularity
there is one **S2↔S3 back-edge** (`store` → `coupling` via deliberate function-body imports,
`store.py:1468-1469,1554`; `propagation`/`_blast` → `store`). The back-edge is real coupling; it stays
acyclic at module level only because `coupling.py` is a pure leaf and `store`'s edge is lazy. See the
dependency summary at the end.

> **Methodology caveat (from catalog validation):** loomweave's edge graph does not capture
> *function-body* (lazy) imports. Two edges — `store`→`coupling` and `cli`→`coupling` — are lazy and
> were added after `analysis-validator` cross-checked the raw `import` statements. All 30 modules
> including `__init__.py` (which exports only `__version__`) are accounted for.

---

## S1 — Contract & Envelope Foundation

**Location:** `src/warpline/{errors,envelope,_enrichment,listing,refs,locators}.py` (~931 LOC)

**Responsibility:** Define and enforce the frozen wire contract — the success envelope, the closed
error/enrichment/reason vocabularies, input-ref parsing, and the list-ergonomics pipeline — so every
tool response is shaped and degraded identically.

**Key Components:**
- `errors.py` — `WarplineError` base + **11 subclasses** pinning the **closed `warpline.error.v1`
  vocabulary** (11 `error_code`s, 3 `retryability` values; asserted in `to_error_data`).
- `envelope.py` — `build_envelope`, `enrichment_state`, `local_only_meta`; the **closed
  `ENRICHMENT_VOCAB`** (`envelope.py:12-20`) and the `meta.local_only`/`peer_side_effects: []` stamp.
- `listing.py` — the `filter → sort → overflow → page → group_by` pipeline + **`reason()`** over the
  11 weft-reason classes (G1 contract); cursor encode/decode; overflow-to-file spill.
- `refs.py` — `parse_entity_ref` / `parse_changed_refs` over the 6 frozen ref kinds
  (`auto|locator|sei|path|qualname|warpline_entity_key_id`); `entity_view` (the frozen `{locator, sei}`
  view).
- `_enrichment.py` — pure staleness/completeness → enrichment-string mapping + warning composition.
- `locators.py` — `python_entity_locators` (path → candidate Python entity locators).

**Dependencies:**
- Inbound: most subsystems (S3, S4, S5, S6, S7) — but **not** `store.py` (S2) and **not**
  `install_support` (S8), which import nothing from S1. So S1 is a foundation *alongside* S2, not
  beneath it. `listing.reason` has fan_in 16.
- Outbound: intra-S1 only (`envelope` → `_enrichment`, `listing`, `__init__`; `listing`/`refs` →
  `errors`). No outbound to S2-S8.

**Patterns Observed:** Closed vocabularies enforced by `frozenset` membership + `assert`; honesty
invariant (`absent ≠ unavailable`); contract values centralized so no surface can diverge.

**Concerns:** `listing.py` (437 LOC) carries the most behavior in this layer and mixes pure
predicates with filesystem overflow-spill (`apply_overflow` writes a file) — a small I/O leak into an
otherwise-pure contract module. Minor.

**Confidence:** **High** — read `errors.py` and `envelope.py` in full; `listing`/`refs` via docstrings
+ symbol maps + their call sites in `commands.py`.

---

## S2 — Temporal Store (Persistence)

**Location:** `src/warpline/{store,snapshot}.py` (~2120 LOC)

**Responsibility:** Own all durable temporal state — the SQLite schema, forward-only migrations, and
the `WarplineStore` data-access layer — plus edge-snapshot capture from loomweave neighborhoods.

**Key Components:**
- `store.py` (1863 LOC) — the **foundation god-module** (fan_in 38, fan_out 0 internal):
  - **Schema** (frozen base `SCHEMA`): `meta`, `repos`, `entity_keys`, `commit_refs`,
    `change_events`, `edge_snapshots`, `snapshot_edges`, `health_log`.
  - **Migrations** v2 (anchor columns), v3 (`co_change_pairs`), v4 (`verification_events`) —
    ordered, forward-only, each under `BEGIN IMMEDIATE`/`COMMIT` with `user_version` + `meta` updated
    in the same txn; concurrent-open safe via `busy_timeout` + re-read under RESERVED lock.
  - **`_schema_presence_floor`** — verifies a version *marker* against actual on-disk objects and
    re-runs migrations from a safe floor (defends against a lying `meta.schema_version`).
  - **`read_store_binding`** — the strictly-read-only `project_status` probe (`mode=ro`, creates
    nothing); closed `STORE_STATUS_VOCAB` (`ok|store_absent|store_unreadable|schema_ahead`).
  - **`WarplineStore`** — 40 methods: entity-key upsert/merge, change-event append/query, timeline,
    churn aggregation, co-change pair upsert/rebuild, verification events, snapshot create/read,
    `capture_snapshot_atomic`. Includes the intricate `reresolve_entity_key_sei` → `_merge_into_twin`
    → `_repoint_{co_change_pairs,snapshot_edges}` identity-merge family.
- `snapshot.py` — `capture_edge_snapshot` / `edges_from_neighborhood`: turns a loomweave neighborhood
  into `snapshot_edges` rows (the bridge from S5 into S2).

**Dependencies:**
- Inbound: S3 (`_blast`, `propagation`), S4 (`commands`), S5 (`git`, `reresolve`), S8 (`dogfood`,
  `install_support`), S7 (`cli`).
- Outbound: `store.py` → **no module-level internal imports** (this is *why* it anchors the graph)
  **but one deliberate function-body edge to `coupling` (S3)** at `store.py:1469,1554` (the comment at
  `:1468` documents "store → coupling is the one-way edge"). `snapshot.py` → `loomweave` (S5),
  `store` (S2).

**Patterns Observed:** Migration-runner discipline; idempotent `INSERT OR IGNORE` writes; deterministic
UTC-normalized ordering (`COALESCE(datetime(x), x)`) to avoid mixed-tz lexical-sort bugs; "never
regress a marker to NULL" merge rules; documented, explicit data-loss on merge collisions (M5).

**Concerns:**
- **Size / cohesion.** 1863 LOC in one file holding schema DDL, the migration runner, a read-only
  binding probe, *and* a 40-method data-access class. Internally cohesive but a clear split candidate
  (see 05). The `_merge_into_twin` family alone is ~270 LOC of high-stakes referential-integrity
  surgery on FK-less tables.
- **No DB-level FKs on the `entity_key_id` references in derived tables.** `co_change_pairs` has *no*
  `FOREIGN KEY` at all; `snapshot_edges` has an FK on `snapshot_id` (→ `edge_snapshots`) but **none on
  its `source_entity_key_id`/`target_entity_key_id` columns**. So referential integrity for those
  entity references is maintained *manually* in the merge path (`_merge_into_twin` / `_repoint_*`) —
  correct today, but fragile to future edits. (This is the debt catalog's only correctness-class item.)

**Confidence:** **High** for lines 1-1342 (read in full) + the full method inventory; **Medium-High**
for lines 1343-1864 (signatures + docstrings, not line-by-line).

---

## S3 — Domain Compute (pure analytics)

**Location:** `src/warpline/{_blast,propagation,_completeness,coupling,verification,_attest,reverify}.py`
(~1043 LOC)

**Responsibility:** The pure, testable analytical core — blast-radius traversal, impact-completeness
self-assessment, temporal co-change coupling, verification freshness, attest-bundle risk, and worklist
rendering. Mostly side-effect-free functions over store-read inputs.

**Key Components:**
- `propagation.py` — `blast_radius`: BFS over `snapshot_edges` from the changed seed (the
  PURE traversal, R7 — `_commits_behind` is its only subprocess, for staleness).
- `_blast.py` — `resolve_changed_inputs`, `rev_range_commits`, `enrich_blast`: prep/post around the
  traversal (resolve refs → key ids; attach the frozen entity view).
- `_completeness.py` — `compute_impact_completeness` / `completeness_risk`: the federation-D1
  self-assessed `{as_of, graph_fresh, status, depth_capped, unresolved_count}` object.
- `coupling.py` — `derive_pairs_from_commit`, `classify_confidence`, `coupling_rate`: co-change
  derivation (Rung 2 Track A).
- `verification.py` — `compose_verification_freshness`: git-reachability freshness
  (`fresh|stale|unverified|unavailable`) via injected `covers`/`between` callbacks.
- `_attest.py` — `parse_attest_bundle`, `worklist_risk`: risk-as-verification over an untrusted
  wardline-attest-2 bundle (proven-good iff every affected entity attested clean at its current body).
- `reverify.py` — `render_reverify_worklist`: assembles per-item worklist rows (depth, verification
  block, work enrichment scaffold).

**Dependencies:**
- Inbound: S4 (`commands`) is the primary caller; `reverify` is called by `commands.reverify_worklist`.
- Outbound: mostly none (pure). Exceptions: `_blast` → `git` (S5) + `store` (S2);
  `propagation` → `store` (S2); `reverify` → `listing` (S1) + `siblings` (S6).

**Patterns Observed:** **Dependency injection via callbacks/Protocols** (`verification` takes
`covers`/`between`; `reverify` takes a `WorkClient`) keeps the core pure and unit-testable without a
DB or git. Honest degradation states are first-class return values, not exceptions.

**Concerns:** `_attest`/`verification`/`reverify` are pure but their *orchestration* (cache, ordering,
content-hash fetch) lives in `commands.reverify_worklist`, not here — so the compute layer is clean but
its assembly is concentrated in S4 (see S4 concern).

**Confidence:** **High** — docstrings + signatures + full read of every call site in `commands.py`.

---

## S4 — Command Orchestration

**Location:** `src/warpline/{commands,cop}.py` (~1914 LOC)

**Responsibility:** The 8 tool bodies. Each wires S2 (store) + S3 (compute) + S5/S6 (seams) + S1
(envelope) into one frozen response. `cop.py` composes the (non-frozen) temporal change-oriented
posture frame.

**Key Components:**
- `commands.py` (1486 LOC) — `change_list`, `entity_timeline`, `entity_churn_count`, `impact_radius`,
  **`reverify_worklist`**, `capture_snapshot`, `verify_record`, `project_status`, `session_context`;
  plus the **always-on lazy edge-snapshot capture** (`_lazy_capture_if_missing`) with a per-DB
  throttle marker, and `_attest_content_hashes` (per-SEI loomweave round trip).
- `cop.py` — `resolve_frame` (frame kinds for the COP demo verb), `compose_temporal_cop` (Rung 2
  Track D); deliberately kept out of `cli.py`'s import path so the parser builds without pulling in
  the federation consults.

**Dependencies:**
- Inbound: S7 (`cli`, `mcp`), S8 (`dogfood`).
- Outbound: **the widest in the system** — S1 (`envelope`, `listing`, `refs`, `errors`,
  `_enrichment`), S2 (`store`, `snapshot`), S3 (`_attest`, `_blast`, `_completeness`, `propagation`,
  `reverify`, `verification`), S5 (`git`, `loomweave`), S6 (`federation`, `siblings`).

**Patterns Observed:** Uniform tool-body shape (`resolve inputs → open store → compute → list
pipeline → build_envelope`); pre-page vs post-page discipline (summaries/federation/attest computed
over the FULL filtered set, pagination applied last); fail-soft advisory side effects.

**Concerns:**
- **`reverify_worklist` is the system's complexity hotspot** (276 LOC, fan_out **34**). It
  orchestrates ≥8 concerns in one function: ref resolution, lazy capture, blast, per-entity
  verification-freshness (with an inline cache + two git-reachability closures), work/risk/governance
  federation enrichment merge, attest content-hashing, impact-completeness, the list pipeline, and
  envelope assembly. High cyclomatic complexity; hard to unit-test below the integration level.
- **Orchestration glue lives in `commands.py`, not S3** — `_lazy_capture_if_missing`,
  `_attest_content_hashes`, `_merge_federation_enrichment`, `_member_scalar`, the verification cache.
  These are reusable-looking helpers stranded in the command module.

**Confidence:** **High** — `commands.py` read in full; `cop.py` via docstring + symbols + `cli.py`
call site.

---

## S5 — Resolution & Ingestion Seams

**Location:** `src/warpline/{loomweave,git,reresolve}.py` (~852 LOC)

**Responsibility:** Bring the outside world *in* — loomweave SEI/edge resolution, git history
ingestion, and the self-healing SEI re-resolution sweep. These are the **adapters** behind the S2/S3
ports.

**Key Components:**
- `loomweave.py` — `LoomweaveProbe` (availability/version), `LoomweaveMcpClient` (subprocess
  `loomweave serve` JSON-RPC client over stdio with `selectors`-based I/O), `resolve_sei_for_locator`,
  `resolve_content_hash_for_locator`, locator→qualname/entity-id candidate helpers. Defines the
  `ToolClient` **port**.
- `git.py` — `backfill` (full history → change_events), `ingest_commit` (single commit, post-commit
  hook), commit-meta/name-status parsing, `resolve_commit`/`is_ancestor`/`commits_between`
  (reachability primitives consumed by S3 verification).
- `reresolve.py` — `sweep_reresolve_sei` (Rung 1c): pages null-SEI entity keys and heals them via
  `store.reresolve_entity_key_sei`.

**Dependencies:**
- Inbound: S4 (`commands`), S3 (`_blast`, `verification` via the reachability fns), S2 (`snapshot`),
  **S6** (`federation` → `loomweave`), S7 (`cli`), S8 (`dogfood`).
- Outbound: `loomweave` → stdlib only; `git` → `locators` (S1), `loomweave` (S5), `store` (S2);
  `reresolve` → `store` (S2), `loomweave` (S5).

**Patterns Observed:** Subprocess-isolated sibling access (no in-process import of loomweave —
deployment-independent); `Protocol` ports decouple callers from the concrete subprocess client;
fail-soft probes return status objects, never raise into the read path.

**Concerns:** `loomweave.py`'s hand-rolled `selectors`-based stdio JSON-RPC client (`LoomweaveMcpClient`,
~170 LOC) is non-trivial concurrency/IO code; a deadlock/timeout bug here degrades every
graph-enriched tool. Worth focused tests (see 05).

**Confidence:** **High** — docstrings + symbol maps + every call site read in `commands.py`/`store.py`.

---

## S6 — Federation Enrichment Seams

**Location:** `src/warpline/{federation,siblings}.py` (~609 LOC)

**Responsibility:** The optional cross-member consults that enrich a worklist when
`include_federation=true` — filigree work-state, wardline risk dossier, legis governance read — each
honest about its own availability.

**Key Components:**
- `federation.py` — `consult_federation` (the HARD SEAM); `WardlineDossierClient`,
  `LegisGovernanceClient` (over `legis governance-read <SEI>`), the `RiskClient`/`LegisClient`
  **ports**; `LegisGovernanceUnavailable`; `federation_transport_blockers`. Each member returns its
  own weft-reason; a member with no transport is honestly `disabled`, never silently dropped.
- `siblings.py` — filigree work seam (SEAM 2 inbound, ADR-029 entity-association reverse-lookup over
  HTTP): `FiligreeWorkClient`, `work_enrichment_for_sei`, `priority_from_work`, the `WorkClient`
  **port**, and `RenameFeed` (rename-aware timeline stitch).

**Dependencies:**
- Inbound: S4 (`commands`, `cop`), S3 (`reverify` imports `WorkClient`/`RenameFeed`), S7 (`mcp`).
- Outbound: **S1** (`federation` → `listing.reason`, `federation.py:38`), **S5** (`federation` →
  `loomweave.loomweave_resolve_qualnames`, `federation.py:39`), intra-S6 (`federation` → `siblings`,
  `:40`); plus stdlib (`urllib` for filigree HTTP, `subprocess` for legis/wardline CLIs). *(Corrected
  from "stdlib only" after validation.)*

**Patterns Observed:** Capability-gated wiring (the legis client is wired only when the installed
legis advertises `governance-read`; until then `disabled`, not forced `unreachable`);
**governance-as-echo** (legis `content_hash` echoed verbatim, never re-derived — GV-LG-1);
schema-mirrored contracts (`contracts/governance_read.v1.schema.json` mirrored byte-for-byte from
legis as the owner).

**Concerns:** Three distinct sibling transports (filigree HTTP, legis CLI, wardline CLI) each with
their own failure surface and parsing; the consult fan-out is the second-most-complex flow after
`reverify_worklist`. Contract drift risk is managed by mirrored schemas + consumer rejection tests
(good), but the seam is inherently brittle to sibling CLI/HTTP changes.

**Confidence:** **High** — docstrings + symbols + CHANGELOG (legis/wardline consumer entries) +
`commands.py`/`mcp.py` call sites.

---

## S7 — Interface Surfaces

**Location:** `src/warpline/{cli,mcp,mcp_smoke}.py` (~1623 LOC)

**Responsibility:** Translate a transport (argparse CLI / JSON-RPC stdio) into `commands.py` calls and
back; verify the live MCP surface.

**Key Components:**
- `cli.py` (601 LOC) — `build_parser` (every subcommand/flag/exit code), `main`; thin payload
  builders for the `cop`/`co-change` demo verbs; constructs the optional loomweave/sei clients.
- `mcp.py` (777 LOC) — JSON-RPC `dispatch`, `_build_tools` (the 8 tool specs with endorsed name +
  shim + metadata: read/write posture, idempotency, repo requirement, touched paths, federation
  deps), per-tool handlers `_h_*`, `WarplineError` → `warpline.error.v1` mapping.
- `mcp_smoke.py` — `run_mcp_smoke`: live stdio round-trip smoke test.

**Dependencies:**
- Inbound: process entry points (`pyproject.toml` scripts), S8 (`dogfood` drives `mcp.dispatch`).
- Outbound: `cli` → S8 (`dogfood`, `productization`, `install`, `install_support`), S5 (`git`,
  `loomweave`, `reresolve`), S2 (`store`), S1 (`envelope`), S4 (`commands`, `cop` local), **S3**
  (`coupling.classify_confidence` via a function-body import, `cli.py:136`), `mcp_smoke`. `mcp` → S4
  (`commands`), S1 (`errors`), S6 (`federation`, `siblings`).

**Patterns Observed:** **Two surfaces, one core** — both delegate to `commands.py`, guaranteeing
CLI/MCP parity. Tool metadata is declarative (posture/idempotency/paths advertised, not inferred).
Endorsed-name + shim aliasing returns identical schema+data.

**Concerns:** `cli.py`'s `main` (fan_out 31) is a large dispatch switch; the two surfaces duplicate
some argument-coercion logic (`mcp._*_arg` vs `cli` argparse types) — minor, inherent to dual
surfaces.

**Confidence:** **High** — symbol maps + docstrings + the `commands.py` contract they call.

---

## S8 — Lifecycle & Productization

**Location:** `src/warpline/{install,install_support,productization,dogfood}.py` (~1238 LOC)

**Responsibility:** Out-of-band concerns: federation member install/doctor, git-hook installation,
release-readiness decisioning, and the dogfood evaluation harness.

**Key Components:**
- `install_support.py` (513 LOC) — `install`/`doctor` components: `.mcp.json` (Claude Code) + Codex
  config bindings, CLAUDE.md/AGENTS.md instruction-block injection (foreign blocks preserved),
  skill copy, gitignore, atomic writes, symlink rejection. `CheckResult`/`Component` model.
- `install.py` (27 LOC) — `install_hook` (the git post-commit hook body).
- `productization.py` — reads `spike/REPORT.md` → `ProductizationDecision` (solo vs federation
  readiness thresholds).
- `dogfood.py` (575 LOC) — `run_dogfood_evaluator`: synthetic lanes + a real-member lane that drives
  the full change → reverify loop against an actual loomweave index; gates on `ready=True`.

**Dependencies:**
- Inbound: S7 (`cli`).
- Outbound: `dogfood` → S4 (`commands`), **S2** (`store`, `snapshot`, `dogfood.py:22-23`), S5
  (`git`, `loomweave`), S7 (`mcp.dispatch`); `install_support` → **S2** (`store.WARPLINE_GITIGNORE_CONTENTS`,
  `install_support.py:25`) + intra-S8 (`install`); `install`/`productization` → stdlib. *(Corrected
  from "stdlib only" after validation.)*

**Patterns Observed:** Idempotent, atomic, foreign-block-preserving installer (never clobbers a
sibling's config); dogfood exercises the *real* loop end-to-end as an executable readiness gate.

**Concerns:** `dogfood.py` (575 LOC) re-implements some git/tool-call plumbing locally
(`_git`, `_call_tool_stdio`) that overlaps S5/S7 — acceptable for a test harness but a drift risk.
`productization.py` reads a hard-coded `spike/REPORT.md` / `/tmp` default path — fine for an internal
release tool, not a general API.

**Confidence:** **High** — docstrings + symbols + README/CHANGELOG context.

---

## Dependency summary (subsystem level)

```
S1 Contract  ◄── S3,S4,S5,S6,S7          ──► (intra-S1 only; no outbound to S2-S8)
S2 Store     ◄── S3,S4,S5,S7,S8          ──► S3 (store→coupling, lazy) / snapshot→S5
S3 Compute   ◄── S2,S4,S7                ──► S1,S2,S5,S6
S4 Commands  ◄── S7,S8                   ──► S1,S2,S3,S5,S6   (widest fan-out)
S5 Seams     ◄── S2,S3,S4,S6,S7,S8       ──► S1,S2 (subprocess to loomweave/git)
S6 Federation◄── S3,S4,S7                ──► S1,S5,intra-S6  (+ HTTP/CLI to siblings)
S7 Surfaces  ◄── entry points,S8         ──► S1,S2,S3,S4,S5,S6,S8
S8 Lifecycle ◄── S7                      ──► S2,S4,S5,S7
```

Layering is **mostly** clean and **module-level acyclic** (loomweave `module_circular_import_list` = 0),
but it is *not* a strict single-direction stack:

- **S2↔S3 back-edge (the one real coupling smell).** `propagation`/`_blast` (S3) → `store` (S2), and
  `store` (S2) → `coupling` (S3) via lazy function-body imports. The code keeps the *module* graph
  acyclic only because `coupling.py` is a pure leaf and `store`'s import is deferred — an explicit
  workaround (`store.py:1468`) for what is, at the subsystem level, a cycle. This is the coupling the
  quality assessment (05) examines.
- **Intentional acyclic "upward" reaches:** S8→S7 (`dogfood` drives `mcp.dispatch`), S3→S6
  (`reverify` imports seam *ports*), S7→S3 / S2→S3 (lazy `coupling` imports).
