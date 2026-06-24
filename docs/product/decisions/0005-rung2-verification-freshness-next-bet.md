# PDR-0005 - Rung 2 Verification-Freshness, Sourced From Warpline's Own Gate

Date: 2026-06-23
Status: accepted
Author: Claude (product owner session)
Owner sign-off: autonomous within the `vision.md` grant — reversible, repo-local
design + (forthcoming) implementation. The one piece that is NOT autonomous —
promoting `verification` into the frozen closed envelope vocab — is explicitly
deferred as an owner/glossary escalation.
Supersedes: none
Related: PDR-0004 (its reversal trigger names this bet), `roadmap.md` (Rung 2),
`metrics.md` (north-star), `docs/superpowers/specs/2026-06-23-verification-freshness-design.md`.

## Context

PDR-0004's reversal trigger fired: the spine is trustworthy-by-construction, so the
post-hardening pivot is enhancement. Rung 2's diagnostic tier is mostly landed
(co-change graph, risk/governance enrichment, temporal COP). The one un-landed
capability is **verification-freshness** — a `last_verified` axis so the reverify
worklist answers *"changed since last proven-good"* (not just "since HEAD~1") with a
trust-decay signal. Investigation found warpline has **no** verification concept
today, and the roadmap's listed sources differ sharply in availability: wardline
"resolved", filigree "closed", and legis "attested" all need *sibling-side surfaces
that do not exist*; only warpline's **own gate result** is fully within authority.

## The call

Build verification-freshness as the next bet, **sourced from warpline's own gate
result**:

- A new verb (`verify-record`, CLI + MCP) an external gate (CI / test-runner / the
  human) calls after a gate passes.
- **Data model A** — per-commit `verification_events` (one row per gate-run,
  mirroring `change_events`); freshness computed by git reachability into
  `fresh / stale / unverified / unavailable`, never by stamping every entity.
- **Advisory, never gates** — the worklist annotates + re-sorts (stale-of-trust
  first) but never removes an affected item (filtering = gating = a hard anti-goal).
- **Rides as a reverify-item field**, NOT the frozen envelope vocab (keeps the
  just-hardened contract untouched).
- Sibling-sourced verification stays **honest-absent RESERVED** extension points.

## Rationale

Smallest real bet that tests the riskiest assumption — does a local-gate
`last_verified` axis produce useful signal? — entirely within the authority grant
(no sibling dependency). Outcome-leaning: if nobody records gate passes the axis
adds noise, and the reversal trigger catches that.

## Status this session

Spec written and committed
(`docs/superpowers/specs/2026-06-23-verification-freshness-design.md` on
`plan/spine-hardening`), at the user's review gate; `writing-plans` not yet invoked.

## Reversal trigger

Reopen if, on a real repo, the local-gate signal proves not useful — e.g. nobody
records gate passes, so every reverify item reads `unverified` and the axis adds
noise, not signal — or if a sibling ships a richer verification surface
(wardline-resolved, legis-attested) that should supersede the local source.
