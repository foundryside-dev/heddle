# Current State - Warpline

Checkpoint: 2026-06-24 — post spine-hardening (accepted) + two patch releases (v1.1.2, v1.1.3)

## The bet right now

**Rung 2 — verification-freshness** (PDR-0005): give warpline a `last_verified` axis,
sourced from its own gate result, so the reverify worklist answers *"changed since
last proven-good"* with a trust-decay signal — advisory, never gates. **Moves** the
north-star from "reverify since HEAD~1" toward "reverify since last proven-good."

Status: design **spec written and approved-pending-review**
(`docs/superpowers/specs/2026-06-23-verification-freshness-design.md`, on
`plan/spine-hardening`). Next step is the spec review gate → `/axiom-planning` →
build. Not yet filed as a tracker issue.

## Branch topology (load-bearing — read before acting)

- **`main`** = `v1.1.3`. Two patch releases shipped this session (owner-directed):
  v1.1.2 (post-commit hook hang fix) and v1.1.3 (version-metadata single-sourcing).
- **`plan/spine-hardening`** holds the **accepted spine-hardening bet** (PDR-0004,
  22 commits, all gates green, final review = ready-to-merge) **and** the
  verification-freshness spec. It is **behind `main`** by the two patch releases
  (independent files; merges clean). Merge `main` into it before the hardening
  itself releases.

## In flight (tracker)

- **Nothing active.** Tracker holds only `warpline-3deba68a62` (P4, release
  placeholder "Future"). The snapshot-capture bug cluster and the loomweave hang
  (`warpline-949bd78421`) are **closed**. The hardening bet and the
  verification-freshness spec live in the workspace/plans, not the tracker.

## Open questions / blocked-on-owner (escalations)

1. **Merge `plan/spine-hardening` → `main` and cut a 1.2.0 minor** for the hardening
   bet (capture correctness + honesty completion + conformance package). Outward-facing
   release — owner's call.
2. **Deliver the 5th-producer handover to the federation hub** — GS-7 oracle wiring +
   glossary freeze (OD-5 is resolved-direction; the warpline-side package is done at
   `docs/integration/2026-06-22-warpline-5th-producer-handover.md`). Sibling/hub +
   outward-facing — owner's call.
3. **(deferred)** Promoting `verification` into the frozen closed envelope vocab is a
   future glossary/contract-evolution escalation (the v1 bet keeps it as a
   reverify-item field — see PDR-0005).

## What this checkpoint did

- Recorded **PDR-0004** (harden-the-spine-to-earn-admission — accepted + shipped) and
  **PDR-0005** (Rung 2 verification-freshness as the next bet, sourced from warpline's
  own gate).
- Moved the roadmap: spine hardening accepted/shipped (out of Now), **verification-
  freshness is the active Now bet**; conformance-oracle inclusion reframed as
  owner-escalation-pending (warpline-side done).
- Added 2026-06-24 metric readings (north-star still passing; honesty coverage
  strengthened; the hook-hang guardrail breach found + fixed). No reversal trigger
  crossed.

## Next session starts here

Resume the **verification-freshness spec review** (it is at the user's review gate) →
`/axiom-planning` to generate the implementation plan → build (same subagent-driven
flow as the hardening bet). The two owner escalations above (merge+1.2.0, hub
handover) are waiting whenever the owner wants to act on them.
