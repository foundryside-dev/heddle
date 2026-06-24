# Advisory, never gating

This is the defining posture of warpline, and the one most likely to be
misread. State it plainly:

> warpline is advisory only. It never gates a change, never enforces a policy, and
> never decides whether a change is allowed.

warpline is **deconfliction tooling, not security.** It exists to help humans and
coding agents *coordinate* around change — to answer "what does this touch, and
what should I recheck" — not to *stop* anyone from changing anything. There is no
warpline verdict you must clear, no warpline check that fails your build, no
warpline gate between you and a commit.

## What "advisory" means concretely

| warpline does | warpline does not |
| --- | --- |
| Report what changed and when. | Decide whether the change was allowed. |
| Compute downstream-affected entities. | Block a change because it has a large blast-radius. |
| Render a re-verification worklist. | Require you to complete the worklist. |
| Propose candidate work items. | File, close, or claim work itself. |
| Re-derive sibling risk as an *ordering* signal. | Emit a clean/dirty or allow/deny verdict. |

Every warpline answer is something you can act on or ignore. If you ignore it,
nothing in warpline stops you. The value is in being *informed*, never in being
*permitted*.

## Why it is built this way

The Weft federation is **deconfliction-first and low-security by design.** Tools
in the suite help agents and humans avoid stepping on each other; they are not an
enforcement perimeter. Re-framing a warpline answer as a security control or a gate
breaks that model — it would turn an advisory signal into a blocking one and make
warpline load-bearing in a way it is explicitly not.

This also keeps warpline honest about its limits. A gate has to be *right* — a
false "blocked" is a broken build. An advisory signal can be incomplete and still
useful, as long as it says so. warpline leans into that: it reports
`completeness`, `staleness`, and a closed `enrichment` vocabulary so you always
know how much the advice is worth, and it never dresses up a partial answer as a
verdict. See [Degrade behavior](degrade.md).

## The corollary: absence is never "clean"

Because warpline never gates, a missing sibling fact is never a green light. If
the risk sibling (wardline) is unreachable, warpline reports `risk: unavailable` —
**never** `risk: clean` and never an implied "this is safe to change." An absent
signal is an absent signal, not an approval. Conflating the two would smuggle a
gate-like "all clear" into a tool that has no business issuing one.

## How this shapes what warpline feeds the federation

warpline feeds advisory change-impact facts to governance-style surfaces (such as
Legis or a Plainweave layer): *what changed* and *what is downstream-affected*. Those
surfaces may have their own policy and their own gates — that is their authority.
warpline supplies the facts; it never makes the call. The boundary is in
[Federation](../federation.md).
