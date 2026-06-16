# Changelog

All notable changes to warpline are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and warpline adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The cross-member MCP seam contracts are versioned independently as
`warpline.<contract>.v1` and frozen at the federation clean-break launch; a `v2`
is a new contract URI, never a mutation of `v1`.

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
