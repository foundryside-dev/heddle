# Current State - Warpline

Checkpoint: 2026-06-24 — `main` @ v1.2.0 (spine hardening shipped)

## The bet right now

**Rung 2 — verification-freshness** (PDR-0005): give warpline a `last_verified` axis,
sourced from its own gate result, so the reverify worklist answers *"changed since
last proven-good"* with a trust-decay signal — advisory, never gates. **Moves** the
north-star from "reverify since HEAD~1" toward "since last proven-good."

Status: design **spec written, at the review gate**
(`docs/superpowers/specs/2026-06-23-verification-freshness-design.md`, on `main` since
the 1.2.0 merge). Next step: spec sign-off → `/axiom-planning` → build (same
subagent-driven flow as the hardening bet). Not yet filed as a tracker issue.

## Branch / release state

- **`main` = v1.2.0.** Three releases shipped this session (all owner-directed):
  **v1.1.2** (post-commit hook hang fix), **v1.1.3** (version-metadata single-sourcing),
  **v1.2.0** (spine hardening — correct-by-construction capture + honesty completeness
  + 5th-producer conformance package), the last via a merge after a release-grade
  multi-agent review (PDR-0006).
- `plan/spine-hardening` and `release/1.2.0` were deleted (fully merged into `main`).
- Install hygiene: single canonical warpline (uv tool **1.2.0**); the stale pre-rename
  `heddle` editable venv was retired.

## In flight (tracker)

Four review follow-ups (open, none blocking — from the 1.2.0 review):

- `warpline-d7d04243b2` (P2 bug) — SKIPPED snapshot path (loomweave-absent) is
  non-atomic and downgrades a usable prior snapshot (pre-existing R3-class).
- `warpline-fc09bdeddd` (P2 task) — contract fixtures + ENVELOPE_KEYS stale (missing
  `enrichment_reasons`); **do with/before the hub handover**.
- `warpline-d88e223731` (P3 task) — promote `reason()` cause/fix invariant from
  assert → ValueError (survive `python -O`).
- `warpline-17242c627b` (P3 task) — cover the atomic ROLLBACK branch + enforce the
  no-open-transaction precondition.

(Plus `warpline-3deba68a62` P4 "Future" placeholder.) The verification-freshness bet
lives in the spec, not yet the tracker.

## Open questions / blocked-on-owner (escalations)

1. **Deliver the 5th-producer handover to the federation hub** — GS-7 oracle wiring +
   glossary freeze (OD-5 resolved-direction; warpline-side package done at
   `docs/integration/2026-06-22-warpline-5th-producer-handover.md`). Outward-facing /
   sibling — owner's call. The fixture-drift follow-up (`fc09bdeddd`) lands with it.
2. **(deferred)** Promoting `verification` into the frozen closed envelope vocab is a
   future glossary/contract-evolution escalation (the v1 bet keeps it as a
   reverify-item field — PDR-0005).

*(Escalation #1 from the prior checkpoint — merge to `main` + cut 1.2.0 — is RESOLVED:
owner-directed and shipped this session.)*

## What this checkpoint did

- Recorded **PDR-0006** (accept + ship the hardening bet as v1.2.0 after a 14-agent
  adversarially-verified review; verdict ship, 0 blockers/majors; defer the
  verified-minor findings to tracked follow-ups).
- Roadmap: spine hardening moved out of Now (**shipped in v1.2.0**); verification-
  freshness is the sole active Now bet.
- Metrics: 2026-06-24 reading for the 1.2.0 ship + review (all frozen invariants
  re-verified; 338 passed; release gate green); 4 follow-ups tracked; no reversal
  trigger crossed.

## Next session starts here

Pick up the **verification-freshness spec review** → `/axiom-planning` to generate the
implementation plan → build. Escalation #1 (hub handover) is waiting whenever the
owner wants to act on it.
