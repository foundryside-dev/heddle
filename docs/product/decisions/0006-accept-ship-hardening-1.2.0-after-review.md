# PDR-0006 - Accept + Ship The Hardening Bet As 1.2.0 After A Release-Grade Review

Date: 2026-06-24
Status: accepted
Author: Claude (product owner session)
Owner sign-off: the ACCEPT (accepting delivered work against criteria) is autonomous
under the `vision.md` grant; the RELEASE itself (merge to main, tag, GitHub release,
push) was **owner-directed this session** ("plan and execute 1 … merge to main and
tag and release"), so the outward-facing act is sanctioned, not an open escalation.
Supersedes: none
Related: PDR-0004 (the hardening bet, accepted + shipped to plan/spine-hardening),
`metrics.md` (2026-06-24 readings), `CHANGELOG.md` [1.2.0], the four review
follow-ups warpline-d7d04243b2 / -fc09bdeddd / -d88e223731 / -17242c627b.

## Context

PDR-0004 accepted the spine-hardening bet and shipped it to `plan/spine-hardening`,
with a final whole-branch review of "ready to merge." The prior checkpoint (78cbc25)
recorded "merge to main + 1.2.0" as an owner escalation. This session the owner
directed that merge+release, gated on a fresh **release-grade quality review** of the
branch.

## The call

Ship the hardening bet to `main` as **v1.2.0** (minor — additive `enrichment_reasons`
carrier + new honesty/conformance capability; frozen `warpline.<contract>.v1`
contracts unchanged), on the strength of the review, and **defer the review's
verified-minor findings to tracked follow-up issues** rather than expand the reviewed
release.

The review: a 14-agent workflow (8 specialized dimensions — SQLite/transaction
soundness, Python idioms, test quality, silent-failure, type design, general
correctness, federation-contract discipline, docs), every blocker/major
**adversarially verified** (refute-by-default), synthesized to **verdict: ship** —
**0 confirmed blockers, 0 confirmed majors.** All frozen-contract invariants were
independently verified to hold (closed 6-key vocab unchanged; `meta.local_only:true`
/ `peer_side_effects:[]`; `enrichment_reasons` purely additive; golden vectors
frozen), and `capture_snapshot_atomic` was confirmed correct-by-construction.

The three "confirmed" findings were each downgraded to minor on verification and
filed as follow-ups: warpline-d7d04243b2 (SKIPPED-path non-atomic — pre-existing, NOT
touched by this diff), warpline-fc09bdeddd (contract-fixture drift — the carrier IS
conformance-tested via the GV-HON vectors the hub runs), warpline-d88e223731
(`reason()` assert fragility under `-O` — latent; suite is test-pinned to
AssertionError so warpline cannot run under `-O`). A fourth, warpline-17242c627b
(atomic ROLLBACK test-coverage + precondition guard), captures the test-gap nits. One
in-scope shipping-deliverable nit was fixed in the release (the handover doc's brittle
pass-count → a durable claim).

## Rationale

Shipping a release whose frozen invariants are independently verified, with the
known minor debt explicitly tracked, beats holding a verified-good release for
quality debt that the adversarial pass already confirmed is non-blocking. The two
highest-value follow-ups (fixture drift, assert→ValueError) are routed to land
with/before the hub handover.

## Reversal trigger

Reopen if any deferred follow-up proves to be a real correctness or contract issue in
practice — specifically if warpline-d7d04243b2 (SKIPPED-path) or warpline-fc09bdeddd
(fixture drift) causes prior-snapshot data loss or a hub-consumer contract break in a
real deploy — or if a 1.2.0 consumer hits a frozen-invariant break the review missed.
Any such trip means the release-grade review's "verified-minor" calibration was
wrong and the review harness needs tightening.
