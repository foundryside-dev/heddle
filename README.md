# warpline — temporal change-impact authority

Version 1.1.0 · Weft federation member (5th) · local-first · enrich-only

warpline is the Weft federation's **temporal / change-impact authority**. It owns
the one thing no other member stores — **per-entity change history across runs,
keyed on SEI** — and the downstream-propagation query over it. It answers, every
session, the question an agent asks before claiming a change is done:

> *Given this diff: which entities changed, by whom, when — what is
> downstream-affected over the call graph, and what must I re-verify?*

The federation split is deliberate: **loomweave owns "now"** (the point-in-time
graph and SEI minting); **warpline owns "over time"** (dated change facts and edge
snapshots). warpline is **enrich-only** — it boots, ingests, and answers with no
sibling installed.

**warpline is advisory only. It never gates a change, never enforces a policy, and
never decides whether a change is allowed.** This is deconfliction tooling, not
security. A warpline answer is an enhancement you can act on or ignore — never a
verdict you must clear. It **consumes** Loomweave SEI (it never mints identity) and
**feeds** advisory change-impact facts to governance-style surfaces such as
Legis/Charter, which run their own policy; warpline supplies the facts and never
makes the call.

The product front door lives at
[warpline.foundryside.dev](https://warpline.foundryside.dev/); the reference docs
are under [`docs/`](docs/index.md).

## Features

- **6 MCP tools** for change lists, entity timelines, churn counts, impact
  radius, reverify worklists, and dated edge-snapshot capture — each with a
  frozen `warpline.<contract>.v1` schema.
- **Honest answers**: every response carries `completeness` + `staleness` and a
  CLOSED `enrichment` vocabulary (`present | absent | unavailable`). Sibling
  absence is explicit, never an implied "clean/allowed" state.
- **Local-first & safe**: all state lives under `.weft/warpline/` (git-ignored);
  the only mutating tool writes there and never touches a sibling repo.
- **Real SEI resolution** against the live loomweave, deployment-independent.
- **Federation member lifecycle**: `warpline install` / `warpline doctor [--fix]`
  wire and verify MCP bindings, hooks, the agent skill, and config.
- **Endorsed names + short shims**: e.g. `warpline_change_list` and `changed`
  return identical schema and data.

## Installation

Install as a [uv](https://docs.astral.sh/uv/) tool (recommended — provides the
`warpline` and `warpline-mcp` executables on your `PATH`):

```bash
uv tool install warpline
warpline --version        # warpline 1.1.0
```

Or with pip (warpline is a zero-dependency package):

```bash
pip install warpline
```

For development from a checkout:

```bash
git clone <repo-url> warpline && cd warpline
uv run warpline --version
```

**Requires Python ≥ 3.12.**

## Quick start

### 1. Install warpline into a repository

`warpline install` wires warpline as a federation member of the target repo —
idempotent, atomic, and it never clobbers a sibling's config block:

```bash
warpline install --repo /path/to/project   # MCP bindings, hooks, skill, config
warpline doctor  --repo /path/to/project   # verify; add --fix to autofix
```

`doctor` exits non-zero if anything is missing and prints a per-component
report (`--json` emits a `warpline.doctor.v1` summary).

### 2. The core loop (CLI)

```bash
warpline backfill --repo /path/to/project --json          # ingest git history
warpline changed  --repo /path/to/project --rev-range HEAD~1..HEAD --json
warpline capture-snapshot --repo /path/to/project --json  # capture loomweave edges
warpline reverify --repo /path/to/project --changed-entity-key-id 1 --json
```

The post-commit hook installed in step 1 keeps the temporal store fresh as you
commit, so `changed`/`timeline`/`churn` answer without a manual backfill.

### 3. The same flow from an MCP host

1. `tools/list` — discover the surface (read/write posture, idempotency, repo
   requirement, touched paths, federation dependencies).
2. `warpline_change_list` (`changed`) — **call first**; read its `next_actions`.
3. `warpline_reverify_worklist_get` (`reverify`) — the worklist to recheck.
4. `warpline_impact_radius_get` / `warpline_entity_timeline_get` — for explanation.
5. `warpline_edge_snapshot_capture` (`capture_snapshot`) — when impact/reverify
   reports `NO_SNAPSHOT` and loomweave is available.

## MCP tools

Endorsed name and short shim are interchangeable and return identical
schema + data.

| Endorsed name | Shim | Schema | Role |
| --- | --- | --- | --- |
| `warpline_change_list` | `changed` | `warpline.change_list.v1` | Changed entities for a rev range; hands back ready-to-call next actions. |
| `warpline_entity_timeline_get` | `timeline` | `warpline.entity_timeline.v1` | Ordered change history for one entity; reports `sei_resolution` only, never lineage. |
| `warpline_entity_churn_count_get` | `churn` | `warpline.entity_churn_count.v1` | Per-entity change-event counts; a never-observed entity is `churn_count: 0`. |
| `warpline_impact_radius_get` | `blast_radius` | `warpline.impact_radius.v1` | Downstream affected set with mandatory `completeness` + `staleness`. |
| `warpline_reverify_worklist_get` | `reverify` | `warpline.reverify_worklist.v1` | The agent worklist to recheck before claiming completion. |
| `warpline_edge_snapshot_capture` | `capture_snapshot` | `warpline.edge_snapshot.v1` | The only mutating tool; captures dated loomweave edges into `.weft/warpline/`. |

### Response contract

Every outbound tool returns the frozen success envelope:

```json
{
  "schema": "warpline.<contract>.v1",
  "ok": true,
  "query": { "repo": "...", "tool": "...", "arguments": {}, "sort": {}, "page": {} },
  "data": { },
  "warnings": [],
  "next_actions": {},
  "enrichment": {"sei": "...", "edges": "...", "work": "...",
                  "risk": "...", "governance": "...", "requirements": "..."},
  "meta": {"producer": {"tool": "warpline", "version": "1.1.0"},
            "local_only": true, "peer_side_effects": []}
}
```

- `enrichment` is a CLOSED vocab: `present` (peer present, fact attached),
  `absent` (peer present, no fact), `unavailable` (peer unreachable) — plus
  `stale | partial | skipped` for `edges`. None of these is ever a transport
  error or an implied clean state.
- Errors use `warpline.error.v1` with a CLOSED `error_code` set and `retryability`
  of `retry_safe | retry_with_changes | fatal`. Switch on `error_code`, not
  message text.
- Every entity carries both `locator` and `sei` (`loomweave:eid:...`, opaque —
  warpline never mints or parses it). `warpline_entity_key_id` is internal and **not**
  a federation key; key on `sei` (preferred) or `locator`.

Full contract: [`docs/federation/contracts.md`](docs/federation/contracts.md)
and the bundled `warpline-workflow` skill
([`src/warpline/skills/warpline-workflow/`](src/warpline/skills/warpline-workflow/)).

## Federation member lifecycle

`warpline install` installs everything by default, or a subset via flags
(`--claude-code`, `--codex`, `--claude-md`, `--agents-md`, `--gitignore`,
`--hooks`, `--session-hook`, `--skills`, `--codex-skills`, `--config`):

| Component | What it does |
| --- | --- |
| MCP bindings | Registers warpline in `.mcp.json` (Claude Code) and `~/.codex/config.toml` (Codex), stdio transport. |
| Hooks | git `post-commit` (fail-soft `warpline ingest-commit`) + Claude `SessionStart` (`warpline session-context`). |
| Skill | Copies `warpline-workflow` into `.claude/skills/` and `.agents/skills/`. |
| Instructions | Injects a `warpline:instructions` block into CLAUDE.md / AGENTS.md (foreign blocks preserved). |
| Config | Writes `.weft/warpline/config.json` + `INSTALL_VERSION`. |

`warpline doctor` checks all of the above; `warpline doctor --fix` re-applies
anything fixable.

## Configuration & runtime layout

warpline is local-first; runtime state lives under `.weft/warpline/` and is
git-ignored:

```text
.weft/warpline/
├── warpline.db          # SQLite temporal store (change events, edge snapshots)
├── config.json        # member identity {prefix, name, version}
├── INSTALL_VERSION    # schema/version marker
└── .gitignore         # keeps ephemeral runtime files out of commits
```

The loomweave command warpline uses for SEI resolution / edge capture is
server/project config — set `WARPLINE_LOOMWEAVE_COMMAND` (default `loomweave`); it
is **not** a public MCP tool argument. `git add -A` never stages a warpline DB.

Filigree work-state enrichment uses filigree's dashboard HTTP API when a reverify
request sets `include_federation=true`. Set `FILIGREE_API_URL` to point warpline
at a non-default dashboard; the default is `http://localhost:8724`. If the
dashboard is absent or unreachable, warpline reports work enrichment as
`unavailable` / member `unreachable` and still returns the local worklist.

## Development

```bash
uv run ruff check .          # lint
uv run mypy                  # strict type-check
uv run pytest                # test suite
uv run warpline mcp-smoke --repo . --json          # live stdio MCP smoke
uv run warpline dogfood-eval --real-member-repo /path/to/member-repo --json
```

`warpline dogfood-eval` exercises the real change → reverify loop (synthetic lanes
plus a real-member lane against an actual loomweave index) and gates on
`ready=True`. See [`spike/REPORT.md`](spike/REPORT.md) for the readiness verdict
and [`CHANGELOG.md`](CHANGELOG.md) for release history.

## Documentation

| Topic | Where |
| --- | --- |
| Docs site landing / table of contents | [`docs/index.md`](docs/index.md) |
| Getting started (install → first worklist) | [`docs/getting-started.md`](docs/getting-started.md) |
| Concepts (mental model, advisory-not-gating, degrade) | [`docs/concepts/`](docs/concepts/index.md) |
| CLI reference (every command, flag, exit code) | [`docs/reference/cli.md`](docs/reference/cli.md) |
| MCP tool reference (all 6 frozen tools) | [`docs/reference/mcp-tools.md`](docs/reference/mcp-tools.md) |
| Federation (seams, what it feeds/consumes, degrade) | [`docs/federation.md`](docs/federation.md) |
| Federation seam contracts (frozen, internal) | [`docs/federation/contracts.md`](docs/federation/contracts.md) |
| Agent usage (progressive-disclosure skill) | [`src/warpline/skills/warpline-workflow/`](src/warpline/skills/warpline-workflow/) |
| Solution architecture (internal) | [`solution-architecture/`](solution-architecture/) |
| Product workspace (vision, roadmap, PDRs) | [`docs/product/`](docs/product/) |
| Release history | [`CHANGELOG.md`](CHANGELOG.md) |

The authoritative interface-lock specification is hub-owned
(`2026-06-13-warpline-interface-lock.md` in the weft hub); warpline implements **to**
it and does not edit it.

## Contributing

warpline implements to a frozen cross-member contract. Changes to a tool's name,
input/output schema, the envelope, or the error/enrichment vocabularies are a
hub decision — escalate with evidence rather than diverging. Internal changes
must keep `ruff`, `mypy --strict`, and the full test suite green, and the 14
golden vectors (`tests/contracts/test_golden_vectors.py`) passing.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow and
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.

## License

MIT — see [`LICENSE`](LICENSE). Copyright (c) 2026 John Morrissey. Consistent
with the rest of the Weft federation.
