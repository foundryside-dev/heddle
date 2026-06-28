# PDR-0007 - Accept Verification-Freshness After Real-Repo Validation Against PDR-0005's Reversal Trigger

Date: 2026-06-28
Status: accepted
Author: Claude (product owner session)
Owner sign-off: autonomous under the `vision.md` grant — "accept or reject
delivered work against `metrics.md` and PRD criteria" and "append Product Decision
Records." This PDR records ACCEPTANCE of an already-built, repo-local capability; it
does **not** release it. The merge+release to `main` (a public-release-status change)
remains an **open owner escalation** — see `current-state.md`.
Supersedes: none
Related: PDR-0005 (the bet + its reversal trigger), the design spec
(`docs/superpowers/specs/2026-06-23-verification-freshness-design.md`), `roadmap.md`
(Rung 2), `metrics.md` (north-star), `CHANGELOG.md` [Unreleased].

## Context

PDR-0005 committed verification-freshness as the Rung 2 bet — a `last_verified` axis
sourced from warpline's own gate result so the reverify worklist answers *"changed
since last proven-good"* with a per-item trust-decay signal; advisory, never gates.
The capability was BUILT across 2026-06-25 (Track B: store v4 `verification_events`,
the `verify-record` verb, pure `compose_verification_freshness`, the reverify
`verification` block + `verification_summary` + stale-first sort, golden vector
`GV-VF-1`) and **merged into `release/1.2.0`** on 2026-06-28 (4b94705) — but landed
**without an interim checkpoint or acceptance record** (the reconciliation debt the
2026-06-26 brief flagged).

PDR-0005's exit was gated on a falsifiable **reversal trigger**: reopen if the
local-gate signal *"proves not useful in practice on a real repo (e.g. nobody records
gate passes, so everything reads `unverified` and the axis adds noise not signal)."*
This session validated the merged capability against that trigger before banking it as
accepted — validate-then-accept, not accept-because-it-shipped.

## The call

**ACCEPT the verification-freshness bet (PDR-0005).** The reversal trigger is **NOT
tripped**: on a real repo the axis differentiates into a meaningful `fresh / stale /
unverified` distribution with correct per-entity trust-decay, an honest empty floor,
and a working never-filtering advisory sort. The bet delivered the question it
promised. The known structural/maintainability debt around the reverify path is routed
to the hardening backlog (arch-analysis U5/U7), not held against this acceptance.

## Validation evidence (warpline's own dogfood repo, HEAD `e2b8ccc`, schema v4)

Procedure: reverify the same changed entity (`--changed-entity-key-id 110 --depth 3`,
53-item radius) before and after recording a single gate pass at the last real release
(`v1.2.0`), so "changed since last proven-good" maps to "changed since 1.2.0."

| signal | baseline (0 verification events) | after 1 `ci_pass` @ `v1.2.0` |
| --- | --- | --- |
| `local_source_configured` | `false` (honest: no source) | `true` |
| fresh | 0 | **5** (untouched since 1.2.0; `commits_behind: 0`) |
| stale | 0 | **39** (changed in the post-1.2.0 stack; `commits_behind` 21–37) |
| unverified | **53** (all) | **9** (no recorded change to verify) |
| items returned | 53 | 53 — **never filtered** |

Findings:

- **Signal, not noise.** Recording ONE gate pass converted an all-`unverified`
  worklist into a three-bucket distribution. The trigger's degenerate case (everything
  `unverified`) is the *honest empty floor*, not the steady state once a gate is
  recorded.
- **Trust-decay is real per-entity granularity.** Stale items carry `commits_behind`
  21–37 — distinct distances reflecting where in the post-1.2.0 stack each entity last
  changed, not a flat flag.
- **Stale-first advisory sort confirmed.** Within each depth band the order is stale →
  unverified → fresh; the existing depth ordering is preserved; 53 affected entities in
  → 53 out (the never-filter / never-gate invariant holds).
- **Honesty invariants held.** Every non-`fresh` state carries a `cause + reason_class
  + fix` triple; `unverified` reads as "not an earned-clean," never silently fresh;
  `local_source_configured` flips `false → true` honestly.
- **Robustness bonus.** `verify-record --commit v1.2.0` correctly dereferenced the
  annotated tag to its **commit** (`6024fed1`), not the tag object (`1bba409e`) — the
  "never store a symbolic ref" discipline extends to annotated tags.

Raw captures: `reverify-baseline.json` / `reverify-after.json` in the session
scratchpad (transient). The validation wrote one real verification event to the dogfood
store (`verification_events.id=1`, `ci_pass` @ `v1.2.0`, actor
`validation-2026-06-28-pdr0005`) — a *true* statement (1.2.0 was proven good via the
PDR-0006 release-grade review), self-documenting via its actor, and **kept** so the
dogfood store's reverify now answers the real "changed since 1.2.0" question. `.weft/`
is gitignored, so the write is tree-clean; the row is reversible by id if a clean store
is preferred.

## Rationale

Smallest real bet, validated within the authority grant on the one source fully within
warpline's authority (its own gate). The empirical result is unambiguous: the axis
answers "changed since last proven-good" with honest decay, and degrades to an honest
`unverified` floor rather than a silent clean. Accepting now — with the next-watch
condition recorded below — beats either rubber-stamping the merge unvalidated or
holding a demonstrably-working capability.

## What this acceptance does NOT cover (still owner-reserved)

- **Release to `main`.** `release/1.2.0` now carries v1.2.0 + 37 commits — a *new
  minor's* worth of capability (`verify-record`, the wardline-attest-2 + legis
  `governance_read.v1` consumers, the `project_status` probe). The version cut (1.3.0
  vs 1.2.x) and the public-release-status change are an open owner escalation.
- **Sibling-sourced verification** (wardline-resolved / filigree-closed /
  legis-attested as `last_verified` sources) stays honest-absent RESERVED — a separate
  bet (and the attest-2 / governance consumers that landed since are a *different* axis:
  risk/governance enrichment, not `last_verified`).
- **Promoting `verification` into the frozen closed envelope vocab** — deferred
  contract/glossary escalation (PDR-0005).

## Reversal trigger

Reopen if, over real workflow use, gate passes are **never recorded** in practice
(verify-record stays un-wired into CI/test runners), so every reverify item perpetually
reads `unverified` and the axis adds noise — i.e. the capability works but goes unused.
The standing mitigation to watch: whether `verify-record` gets wired into a real gate
(CI hook / test-runner wrapper) so the signal is populated by normal use, not a manual
poke. Also reopen if a sibling ships a richer verification surface
(wardline-resolved / legis-attested) that should supersede the local-gate source.
