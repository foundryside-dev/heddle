# Changelog

All notable changes to warpline are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and warpline adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The cross-member MCP seam contracts are versioned independently as
`warpline.<contract>.v1` and frozen at the federation clean-break launch; a `v2`
is a new contract URI, never a mutation of `v1`.

## [Unreleased]

### Added

- **`warpline_project_status_get` / `project_status` — read-only store-binding
  probe (`warpline.project_status.v1`).** A new MCP tool that reports whether THIS
  build can read and *serve* the snapshot store for a given `repo`
  (`data.binding_ok`), reading `schema_version` **from inside** the store
  (`data.store.schema_version`) — never mere directory existence — so a
  stale-but-running warpline that cannot read its `.weft/warpline` store at a
  compatible schema is caught (the federation attachment signal Lacuna's
  MCP-attachment probe asserts on to classify warpline `live-bound`). It is the
  first **genuinely** read-only tool: `writes_local_state: false`,
  `mutates_paths: []`, and it creates/migrates **no snapshot state** — an absent
  store reports `store_status: store_absent` with a `capture_snapshot` next-action
  (no DB is created), a corrupt store `store_unreadable`, and a store written by a
  newer build `schema_ahead` (all three: `binding_ok: false`, `schema_version:
  null`); a present store's `warpline.db` is left byte-for-byte unchanged. Reads
  the store strictly read-only (`mode=ro`, no create-on-missing; opening a present
  WAL store may spawn gitignored `-wal`/`-shm` coordination sidecars, which are not
  snapshot state). The frozen six-tool federation-contract inventory
  (`mcp-tool-inventory.json`) is unchanged — this is an additive health probe, not
  a frozen data contract.
- **v4 schema migration (`verification_events`).** The store's
  `HIGHEST_KNOWN_VERSION` advances to 4 with an additive, forward-only
  `verification_events` table (`_migrate_v4_verification_events`), so this build can
  read and serve a v4 snapshot store rather than reporting it `schema_ahead`. The
  migration is `CREATE TABLE IF NOT EXISTS`-only and touches no existing rows.

## [1.2.0] - 2026-06-24

Minor release: spine hardening. Snapshot capture is now correct-by-construction and
every enrichment dimension carries an explanatory weft-reason. Frozen
`warpline.<contract>.v1` MCP contracts are unchanged; the success envelope gains one
additive top-level key (`enrichment_reasons`).

### Added

- **`enrichment_reasons`** — a new top-level success-envelope key carrying the
  `{reason_class, cause, fix}` weft-reason triple per enrichment dimension, so every
  absence reads as *explained* absence (the closed six-key `enrichment` vocab is
  unchanged). The `sei`, `governance`, and reserved `requirements` dimensions now
  carry triples (never-resolved vs Loomweave-unreachable; rename-feed present vs
  absent; reserved-but-honest), built only from the canonical reason classes.
- **Conformance** — four new golden vectors (`GV-LW-6`, `GV-HON-SEI/GOV/REQ`; 18
  total) lock the atomic-capture and honesty invariants; the golden-vector fixture is
  now portable for the GS-7 5th-producer oracle, with a hub handover package under
  `docs/integration/`.

### Changed

- **Snapshot edge-capture is now correct-by-construction** — a single `BEGIN
  IMMEDIATE` transaction (`capture_snapshot_atomic`) replaces the prior multi-step
  write. A snapshot is never visible until all its edges are committed, and a
  mid-capture failure leaves the prior good snapshot intact (fail-closed, locked by a
  regression test + `GV-LW-6`).

## [1.1.3] - 2026-06-24

Patch release fixing stale self-reported version metadata. Frozen
`warpline.<contract>.v1` MCP contracts remain unchanged.

### Fixed

- `warpline.__version__` is now derived from the installed package metadata
  (`importlib.metadata`) instead of a hand-maintained literal in
  `__init__.py`. That literal went stale at 1.1.2, so `warpline --version`,
  the MCP `serverInfo.version`, and every response envelope's
  `meta.producer.version` reported `1.1.1` on the 1.1.2 build. The version is
  now single-sourced from `pyproject` and cannot drift; the package-version
  test asserts that property rather than pinning a literal.

## [1.1.2] - 2026-06-24

Patch release fixing a post-commit hook hang. Frozen `warpline.<contract>.v1`
MCP contracts remain unchanged.

### Fixed

- The Loomweave MCP client (`LoomweaveMcpClient`) now enforces a single
  per-request **deadline** instead of a per-`select()` timeout. Previously the
  10s timeout was reset on every read, so a `loomweave serve` that emitted any
  output within each window (notifications, log lines, partial frames, or
  unmatched envelopes) while never completing the matching response made
  `call_tool` loop forever — hanging the post-commit hook (the fail-soft
  `try/except` never fired because nothing raised). The read loop now bounds the
  whole request: `select()` is given the *remaining* time and the deadline is
  checked each iteration, so a stalled Loomweave surfaces as a `TimeoutError`
  that the hook's fail-soft path catches.

### Changed

- The installed post-commit hook now wraps each Warpline command in a portable
  `timeout` guard (when `timeout` is on `PATH`) as defense-in-depth, so no
  client can ever wedge a commit workflow.

## [1.1.1] - 2026-06-22

Patch release for snapshot-capture correctness and release hygiene. Frozen
`warpline.<contract>.v1` MCP contracts remain unchanged.

### Changed

- The member-diff release guard is now opt-in, so Warpline-owned gates do not
  fail because sibling repositories have unrelated dirty work.
- Full edge-snapshot capture now reuses one Loomweave stdio MCP session per
  client and batches snapshot-edge writes in a single insert transaction.

### Fixed

- `capture_snapshot` resolves symbolic commit refs like `HEAD` before storing the
  snapshot commit, so later staleness checks compare against a real SHA.
- Snapshot capture no longer publishes `FULL` until edge capture has finished,
  preventing readers from observing a complete snapshot with partial edges.
- `changed_only` snapshot capture now resolves `path`, `qualname`, and `sei`
  scopes to stored entity keys and reports unresolved scoped refs as `DELTA`
  failures instead of a false `FULL`.
- The managed post-commit hook no longer runs synchronous full snapshot capture;
  `warpline doctor --fix` detects and repairs older managed hooks that still do.
- Public docs and evidence no longer expose developer-local absolute paths, and
  `FILIGREE_API_URL` is documented for live Filigree work-state enrichment.

## [1.1.0] - 2026-06-17

Capability-ladder release (Rung 0/1/2). All frozen `warpline.<contract>.v1` MCP
contracts are unchanged — this release is strictly additive.

### Added

- **Temporal co-change graph (schema v3).** Git-history-derived co-change
  coupling between entities, surfaced through the impact/reverify reads (Rung 2
  Track A).
- **Risk/governance enrichment** lit up on the reverify worklist, following the
  closed enrichment vocabulary (`present | absent | unavailable`) (Rung 2 Track C).
- **`include_federation` cross-member consult** re-added and wired as a
  hub-blessed read: reverify consults filigree, wardline, and legis through their
  read-only surfaces, each member carrying its own weft-reason (a member with no
  transport is honestly `disabled`, never silently dropped).
- **Always-on lazy edge-snapshot capture** with git-hook and `doctor` wiring
  (Rung 1d).
- **Self-healing SEI re-resolution sweep** — stale `loomweave:eid:` SEIs are
  re-resolved automatically against live loomweave (Rung 1c).
- **Working-context anchor columns + `detected_context` (schema v2)** (Rung 1b).
- **Temporal COP internals + non-frozen demo CLI**, including a squash-merge
  reconstruction demo (Rung 2 Track D). The demo surface is explicitly non-frozen.
- **Read-surface list-ergonomics microaffordances** (filters/sort/paging) across
  the read tools (G2).

### Changed

- **Ordered migration runner + PRAGMA hardening** — deterministic, gap-safe
  schema migrations (v1→v2→v3) with `user_version` tracking (Rung 1a).
- Internal refactor: extracted `_enrichment` / `_blast` command helpers (Rung 0).
- **Federation contract clarified (no behavior change):** the wardline
  `affected_scope` and legis `preflight_impact` "payloads" are documented as
  consumer-lens names for the single `warpline.impact_radius.v1` wire shape
  `warpline_impact_radius_get` already emits — not separately-emitted schemas
  (matches interface-lock §3A/§4A; pinned by GV-WL-1 / GV-LG-1).

### Fixed

- **filigree work-state seam now consumes filigree's live HTTP surface.** The
  inbound entity-association read previously called a non-existent `filigree`
  CLI verb and never worked against real filigree (only a test fixture proved
  it). It now reads `GET /api/entity-associations?entity_id=<sei>` and
  `GET /api/issue/<id>` (base URL via `FILIGREE_API_URL`, default
  `http://localhost:8724`), degrading honestly to `unreachable` when filigree is
  not running — never a fabricated link or a confident-empty.
- Made impact-radius failure modes **loud** — explicit staleness, miss-set, and
  dead-input signalling instead of a quiet segfault.
- Resolved 10 verified review findings on the capability-ladder branch.

## [1.0.0] - 2026-06-13

First stable release. warpline joins the Weft federation as its 5th member — the
temporal / change-impact authority ("if I touch X, what breaks, and what must I
re-verify?"), implemented to the hub-frozen interface-lock
(`2026-06-13-warpline-interface-lock.md`).

### Added

- **6 frozen outbound MCP tools**, each with an endorsed name and a short shim
  returning identical schema+data:
  - `warpline_change_list` / `changed` — `warpline.change_list.v1`
  - `warpline_entity_timeline_get` / `timeline` — `warpline.entity_timeline.v1`
  - `warpline_entity_churn_count_get` / `churn` — `warpline.entity_churn_count.v1`
    (new: per-entity change-event aggregation; the no-dead-by-design read that
    lights up loomweave's `entity_high_churn_list`)
  - `warpline_impact_radius_get` / `blast_radius` — `warpline.impact_radius.v1`
    (carries the wardline `affected_scope` and legis `preflight_impact` payloads)
  - `warpline_reverify_worklist_get` / `reverify` — `warpline.reverify_worklist.v1`
  - `warpline_edge_snapshot_capture` / `capture_snapshot` — `warpline.edge_snapshot.v1`
    (the only mutating tool; writes `.weft/warpline/` only)
- **Canonical success envelope** (`query`, `data`, `warnings`, `next_actions`,
  `enrichment`, `meta`) with `meta.local_only: true`, `meta.peer_side_effects: []`,
  and a CLOSED `enrichment` vocabulary (`present | absent | unavailable`, plus
  `stale | partial | skipped` for edges). Sibling absence is explicit, never an
  implied clean/allowed state (enrich-only, deconfliction-first).
- **`warpline.error.v1`** with CLOSED `error_code` and `retryability`
  (`retry_safe | retry_with_changes | fatal`) vocabularies.
- **SEI keying**: every entity carries both `locator` and `sei`
  (`loomweave:eid:...`, opaque — warpline never mints or parses it).
- **Federation member lifecycle** (`warpline install` / `warpline doctor`):
  - `install` wires MCP bindings (`.mcp.json` + `~/.codex/config.toml`), the git
    `post-commit` ingest hook, the Claude `SessionStart` hook, the
    `warpline-workflow` skill (into `.claude/skills/` and `.agents/skills/`), the
    CLAUDE.md/AGENTS.md instruction blocks, and `.weft/warpline/` config —
    idempotent, atomic, symlink-safe, and never clobbering a foreign member's
    block.
  - `doctor` verifies every component; `doctor --fix` re-applies anything
    autofixable. JSON via `--json` (`warpline.doctor.v1`).
- **`warpline-workflow` skill** with progressive-disclosure references
  (`contract.md`, `tools.md`, `degrade-and-federation.md`) and a worked example.
- **14 golden vectors** (executable `tests/contracts/test_golden_vectors.py` plus
  a manifest for the GS-7 conformance oracle).

### Fixed

- **HX1 — real SEI resolution.** warpline now sends bare, src-layout-stripped
  dotted qualnames to loomweave `entity_resolve` (which resolves the import path,
  not the filesystem path), keeping prefixed entity ids only for
  `entity_neighborhood_get`. Resolution now returns real `loomweave:eid:` SEIs
  against the live loomweave and is **deployment-independent** (works against
  stock loomweave). Ingest resolves SEIs by default.
- **HX2 — portable executed baseline.** The dogfood baseline uses `git grep`
  instead of a hardcoded `ripgrep` dependency, so it reaches `ready=True` on a
  host without `rg`.

### Notes

- Reserved-shape inbound seams: loomweave is PROVEN and frozen; filigree,
  wardline, and the legis rename feed remain reserved-shape / non-binding until a
  golden vector demonstrates real consumption.

## [0.1.0] - pre-admission

Pre-admission spike: local-first temporal store, git backfill/ingest, the initial
draft MCP surface, and the dogfood readiness gate. Superseded by 1.0.0.
