# Warpline 1.0 Readiness Plan

Required skills: product ownership, implementation planning, MCP engineering,
software engineering, quality engineering.

## Goal

Bring Warpline from disciplined prototype to a product candidate that satisfies
the minimum bar: just as good as existing tools in solo mode, and better with
federation members. Warpline is MCP-facing; a deficient MCP interface is a product
blocker and may require refactor. Warpline is not ready until this plan's evidence
gates pass.

## Current Verdict

Live review on 2026-06-13 found Warpline **not ready**:

- Standalone parity fails: production ingest does not resolve SEI, production
  queries do not capture edge snapshots, and existing flows mostly answer with
  honest `NO_SNAPSHOT`.
- Federation uplift fails: Loomweave integration is adapter/test-only and
  Filigree, Wardline, Legis, and Charter enrichment are not wired through
  published surfaces.
- MCP/runtime conformance fails: malformed input, missing output schemas, C-9
  runtime path divergence, and C-13 hostile-file handling were product blockers.

Some C-9/C-13/MCP issues have a first hardening slice in this checkpoint. Treat
them as fully retired only after the later dogfood and release gates pass.

## Operating Loop

For every slice:

1. Re-orient against current source, tests, and the relevant sibling published
   surfaces.
2. Write or update a failing test/fixture before product code where practical.
3. Implement the narrowest coherent change.
4. Run focused tests, then self-review with code-review priorities: behavioral
   bugs, MCP usability, authority-boundary drift, missing tests.
5. Fix findings before moving to the next slice.
6. Update product state, contracts, and metrics when evidence changes.

Open a design spike instead of coding when a sibling interface, SEI mapping,
snapshot freshness rule, or MCP shape is uncertain enough to risk rework.

## Architecture Direction

- Warpline owns temporal change-impact facts only.
- Loomweave owns current structure and SEI authority.
- Filigree owns work state.
- Wardline owns trust/finding authority.
- Legis owns governance/git/CI authority.
- Charter owns obligations/requirements authority.
- Warpline may enrich from published surfaces, but enrichment is never load
  bearing and never silently invented.
- Runtime state belongs under `.weft/warpline/` by default.
- MCP responses use an agent-facing envelope:
  `{schema, ok, data, warnings, meta}` with actionable next steps where useful.

## Ordered Work

### 1. Truthful Readiness Posture

Files: `README.md`, `spike/REPORT.md`, `docs/product/current-state.md`,
`docs/product/metrics.md`, `docs/product/roadmap.md`,
`docs/product/decisions/0001-product-candidate-ownership.md`,
`src/warpline/productization.py`, `tests/test_productization_gate.py`.

Acceptance:

- `Readiness verdict: not-ready` blocks `warpline productization-gate` even if
  older spike prose contains a historical `go`.
- Product docs say prototype/not member-grade until dogfood evidence passes.
- The release story no longer treats a bounded toy corpus as product proof.

### 2. MCP Live Envelope And Recoverable Errors

Files: `src/warpline/mcp.py`, `src/warpline/commands.py`, `tests/test_mcp.py`,
`tests/fixtures/contracts/warpline/*.json`.

Acceptance:

- `tools/list` advertises input and output schemas for all core tools.
- Live tool responses match the envelope contract.
- Malformed JSON and invalid tool arguments return structured JSON-RPC errors
  and the server continues reading the stream.
- `changed` returns ids and `next_actions.reverify.arguments` that feed
  `reverify` in a two-tool-call workflow.
- Outputs are bounded or explicitly paginated before large-repo acceptance.

### 3. Federation Runtime Conformance

Files: `src/warpline/store.py`, `src/warpline/git.py`, `tests/test_store.py`,
`tests/test_git_backfill.py`, `.gitignore`.

Acceptance:

- Default state path is `<repo>/.weft/warpline/warpline.db`; explicit store dirs
  still work.
- `.weft/` runtime state is ignored by git.
- Undecodable source degrades per file to a `file:<path>` locator and logs or
  reports an explicit warning; a single hostile file never kills backfill.

### 4. Production SEI Resolution

Files: `src/warpline/git.py`, `src/warpline/loomweave.py`, `src/warpline/store.py`,
`tests/test_sei_resolution.py`, `tests/test_loomweave_probe.py`.

Design spike first if Loomweave's stable published SEI lookup contract is
unclear.

Acceptance:

- Backfill/ingest optionally resolve SEI through a published Loomweave read
  surface when available.
- Missing Loomweave produces `sei: absent`, not failure.
- Stored `entity_keys.sei` is populated only when the upstream surface returns
  an authoritative value.
- No sibling package imports are introduced.

### 5. Production Edge Snapshot Capture

Files: `src/warpline/snapshot.py`, `src/warpline/loomweave.py`,
`src/warpline/store.py`, `src/warpline/cli.py`, `src/warpline/mcp.py`,
`tests/test_snapshots.py`, `tests/test_loomweave_snapshot_adapter.py`.

Acceptance:

- Warpline has a production command/tool path to capture dated edge snapshots for
  a commit or bounded rev range.
- Snapshot source/version/completeness/staleness are stored and surfaced.
- Missing or stale snapshots produce explicit `NO_SNAPSHOT`, `SKIPPED`, or
  stale warnings.
- Warpline does not claim current graph authority.

### 6. Changed, Blast Radius, And Reverify Product Flow

Files: `src/warpline/commands.py`, `src/warpline/propagation.py`,
`src/warpline/reverify.py`, `tests/test_propagation.py`,
`tests/test_reverify.py`, `tests/test_commands.py`.

Acceptance:

- A fresh repo can run: backfill/ingest -> changed -> reverify without raw DB
  inspection.
- `changed` output contains the ids and next-step instructions required by
  `blast_radius`/`reverify`.
- Reverify explains what to test, why it is included, and what evidence is
  missing when enrichment is absent.
- Empty, stale, or partial graph results are still useful solo-mode answers.

### 7. Federation Uplift Paths

Files: `src/warpline/loomweave.py`, new federation adapter modules as needed,
`docs/federation/contracts.md`, `docs/integration/post-admission-consumer-tickets.md`,
`tests/integration/*`, `tests/contracts/*`.

Design spike first for each sibling where the published surface is not clear.

Acceptance:

- Loomweave enrichment is live, optional, and tested.
- Filigree, Wardline, Legis, and Charter integrations are represented as
  published-surface contracts or explicit deferred tickets; no hidden direct DB
  or package coupling.
- Federation-enriched dogfood answers are measurably more actionable than solo
  answers in at least 8 of 10 cases.

### 8. Dogfood Evaluator And Readiness Gate

Files: `scripts/`, `tests/spike/`, `docs/evidence/`,
`src/warpline/productization.py`, `src/warpline/cli.py`.

Acceptance:

- Add a machine-readable evaluator output at
  `/tmp/warpline-dogfood-results.json`.
- Solo lane: 10 synthetic git diff cases, MCP only, <=2 core tool calls, no raw
  SQLite or manual grep.
- Federation lane: same cases with dated snapshots and mocked/published
  sibling enrichment.
- Each case records `case_id`, `lane`, `tool_calls`, `baseline_answer`,
  `warpline_answer`, `parity`, `uplift`, `failure_reason`,
  `manual_escape_required`, and `enrichment_state`.
- Productization remains blocked until solo parity and federation uplift both
  reach 8 of 10.

### 9. Contract And Release Hygiene

Files: `tests/fixtures/contracts/warpline/*.json`,
`tests/contracts/test_warpline_contract_fixtures.py`,
`scripts/check_release_candidate.sh`, `scripts/check_no_member_diffs.sh`.

Acceptance:

- Contract fixtures are generated from, or asserted against, live MCP shapes.
- Member-diff guard remains zero-diff except recorded baselines.
- `ruff`, `mypy`, tests, spike harness, dogfood gate, and productization gate
  all tell the same story: either ready by evidence or blocked by a named gap.

## Final Acceptance

Warpline may be called 1.0-ready only when:

- `uv run pytest tests -v`, `uv run ruff check .`, `uv run mypy src/warpline`,
  and member-diff guard pass.
- The dogfood evaluator proves 8/10 solo parity and 8/10 federation uplift.
- `warpline productization-gate --report spike/REPORT.md` returns allowed.
- Product docs, spike report, contract fixtures, and metrics all agree with the
  evidence.
- No sibling repo is modified without explicit owner authorization.
