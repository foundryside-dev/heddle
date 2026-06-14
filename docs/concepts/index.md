# Concepts

warpline is small, and its mental model is small. These pages explain the ideas
you need to read a warpline answer correctly and to understand why warpline does
*less* than you might first expect — on purpose.

- [Temporal facts vs. the current graph](temporal-vs-graph.md) — what warpline
  stores, what it deliberately does not, and why "over time" is a separate
  authority from "now."
- [SEI: consumed, never minted](sei.md) — how warpline keys entities on Loomweave
  SEI, and why it refuses to become a second identity authority.
- [Blast-radius and the re-verification worklist](blast-radius.md) — how warpline
  computes downstream impact over a dated snapshot and turns it into a worklist.
- [Advisory, never gating](advisory-not-gating.md) — the posture that defines
  warpline: it informs, it never enforces. Deconfliction tooling, not security.
- [Degrade behavior and federation absence](degrade.md) — `completeness`,
  `staleness`, and the closed `enrichment` vocabulary; how a sibling's absence is
  reported honestly rather than hidden.

If you read only one, read [Advisory, never gating](advisory-not-gating.md). It is
the single idea that most often gets warpline wrong.
