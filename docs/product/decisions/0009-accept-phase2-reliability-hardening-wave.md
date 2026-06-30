# PDR-0009 - Accept The Phase-2 Reliability Hardening Wave (arch-analysis U1–U8)

Date: 2026-06-29
Status: accepted
Author: Claude (product owner session)
Owner sign-off: autonomous under the `vision.md` grant — "accept or reject delivered
work against `metrics.md` and PRD criteria" and reversible, repo-local work. The owner
directed the wave this session ("plan, implement and review phase 2"; "finish them now").
No outward-facing act: nothing released, pushed, or merged to `main`.
Supersedes: none
Related: `docs/arch-analysis-2026-06-28-0728/07-improvement-roadmap.md` (the basis),
`05-quality-assessment.md` / `06-architect-handover.md`, PDR-0006 (the 1.2.0 review that
filed some of these as follow-ups), commits `69d081c` + `62f2c4c`, `metrics.md`.

## Context

The 2026-06-28 architecture analysis rated warpline **4/5, healthy, zero shipping
defects** — every finding a *future-edit hazard*, not a live bug. `07-improvement-roadmap.md`
phased the debt risk-first: security came back **clean** (Phase 1 empty — verified, not
unexamined), so the highest present risk class, **Phase 2 — Reliability & Correctness**, led:

- **U1** — referential-integrity invariant on the FK-less derived tables (the only High).
- **U2** — the unenforced positional `_blast`↔`commands` invariant (the only *silent-wrong-
  answer* item).
- **U3** — read-path observability (health_log breadcrumbs on the silent swallows).
- **U4** — the lazy-capture throttle gap (capture-time failures bypassed the marker).
- **U8** — hardening the hand-rolled loomweave stdio client (a hang degrades every graph tool).

## The call

Implement and **accept** the Phase-2 wave (U1, U2, U3, U4, U8), behavior-preserving,
frozen contracts untouched, gated by the test suite. Delivered across two adversarially-
reviewed multi-agent workflows:

- `69d081c` — U1 (`_assert_no_orphans` invariant + positive/negative tests, test/CI-invoked
  only — zero added queries on the production merge path), U4 (throttle marker on the
  capture-RAISE path), U8 (bounded frame cap + read deadline + 5 fd/selector tests); U2/U3
  landed **partial** here.
- `62f2c4c` — U2 finished: a per-row **locator identity echo** (independent provenance via a
  key-id lookup, not the changed row) that raises `ValueError` on equal-length order-drift —
  the real silent-wrong-answer defense, not just the length guard; adversarially verified to
  fail-if-reverted. U3 finished: the six inert `# noqa: BLE001` dropped (BLE not in ruff
  select; they suppressed nothing) with breadcrumbs intact.

Gate (independently re-verified): ruff + `mypy src/warpline` clean; pytest **572 passed /
1 skipped**; reverify smoke ok; frozen golden vectors intact; diffs scoped to the named files.

Phase 3 (the god-unit splits `store.py`/`reverify_worklist`) stays **deferred-until-touched**
per the roadmap; Phase 4 perf (U9) and Phase 5 hygiene are opportunistic.

## Rationale

This is **guardrail** hardening — data-integrity, observability, and silent-correctness —
**not** north-star movement, stated plainly. Its value is that it de-risks the exact
chokepoints (`store.py`, `reverify_worklist`) every future capability bet must edit, so the
ladder advances on a foundation where a future-edit regression fails a test loudly instead of
silently corrupting a join or misattributing verification state. The wave was cheap (~the
roadmap's Phase 2 estimate) and is fully reversible.

## Reversal trigger

Reopen if the new guards prove to fire on *valid* input in practice — specifically if
`_assert_no_orphans` flags a legitimate merge state, or the `reverify identity echo failed`
`ValueError` raises on a correctly-ordered worklist (a false positive would surface as a
reverify crash on a real repo). Tie to `metrics.md`: any CI/test failure or field crash
traced to the U1 invariant or the U2 identity echo on correctly-ordered data means the guard
is mis-calibrated and the wave's "behavior-preserving" claim was wrong. Also reopen if the
deferred Phase 3 structural debt (`store.py` / `reverify_worklist` god-units) begins causing
real regressions, promoting it from opportunistic to scheduled.
