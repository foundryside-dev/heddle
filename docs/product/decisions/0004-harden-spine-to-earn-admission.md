# PDR-0004 - Harden The Spine To Earn Admission (Before Enhancement)

Date: 2026-06-22
Status: accepted
Author: Claude (product owner session)
Owner sign-off: autonomous within the `vision.md` grant — reversible, repo-local
work (capture re-architecture, honesty plumbing, conformance tests + a draft
handover package). No vision/strategy/admission/sibling change is decided here.
Supersedes: none
Related: `roadmap.md` (capability ladder Now/Next), `metrics.md` (north-star +
honesty guardrails), PDR-0002 (capability ladder), PDR-0003 (PDR-0025 relay),
`docs/superpowers/specs/2026-06-22-spine-hardening-design.md`,
`docs/integration/2026-06-22-warpline-5th-producer-handover.md`.

## Context

Warpline was admitted (PDR-0022, 2026-06-14) and shipped v1.1 as a fast-follow.
The snapshot edge-capture spine — the mechanism `blast_radius` / `reverify` read —
shipped with a correctness cluster (tracked bugs `warpline-4db9c30b3b`,
`-2a4ff441b6`, `-afc5fa71c7`, `-479c710389`). Codex closed those point-fixes, but
the *structural* failure class survived (capture held its invariant only by an
emergent property; fail-closed-to-prior-snapshot was still violated). Three
directions were on the table: **harden** (make the spine trustworthy), **optimize**
(latency — already 48 ms vs a 250 ms target, no pain), **enhance** (climb to Rung
2/3). A member that emits wrong-but-confident facts is worse than one that emits
honest absence, and warpline is now a member others *read*.

## The call

**Harden the spine to earn the admission, before enhancement.** Specifically:

- **Re-architect capture correct-by-construction** (not patch-on-top): one atomic
  `BEGIN IMMEDIATE` transaction so no snapshot is visible until its edges are
  committed, and a mid-capture failure preserves the prior good snapshot.
- **Complete the honesty triple** (`cause + reason_class + fix`) on every
  enrichment dimension via a new top-level `enrichment_reasons` carrier (the frozen
  closed envelope vocab left untouched).
- **Lock both behind conformance** (golden vectors) and produce a **portable
  5th-producer hub handover package** — the *autonomous half*; actual GS-7 wiring +
  glossary freeze are the owner's escalation (the *escalation package*).

Optimization was subsumed (the one real perf issue was a correctness bug already in
the cluster). Enhancement was sequenced *after* a trustworthy spine.

## Rationale

The product's entire value is trustworthy temporal facts; enhancement built on a
spine that mis-reports staleness inherits the lie. Hardening was bounded by a
falsifiable exit criterion (below) so it could not become an open-ended polish.

## Outcome (this session)

Accepted and shipped to `plan/spine-hardening` (22 commits, subagent-driven, every
task reviewed). Capture fail-closed locked by a unit test + `GV-LW-6`; honesty
locked by `GV-HON-SEI/GOV/REQ`; conformance suite now 18 vectors + a portable
fixture + the handover doc. Full gates green; final whole-branch review = ready to
merge. **Not yet merged to `main`** (owner-gated — see escalations).

## Reversal trigger

- **Pivot to enhancement** once the federation hub accepts the conformance package,
  or sooner if the owner judges the spine trustworthy enough. *(This trigger fired
  this session — the spine is trustworthy-by-construction; Rung 2 is the next bet,
  PDR-0005.)*
- Reopen if a conformance vector proves the invariant is not actually held in
  practice, or if `dogfood-eval` north-star regresses to needing manual grep / raw
  store inspection (PDR-0001 trigger).
