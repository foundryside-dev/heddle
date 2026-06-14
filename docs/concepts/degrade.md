# Degrade behavior and federation absence

warpline is enrich-only and local-first: it works with no sibling installed, and
every sibling fact it can attach is an enhancement, never a dependency. The flip
side of that is a discipline about **how absence is reported.** warpline never lets
a missing peer look like a clean or empty result.

## The closed `enrichment` vocabulary

Every outbound tool returns an `enrichment` object with a fixed set of keys, each
drawn from a **closed** vocabulary. The keys and their allowed values are frozen:

| Key | Source authority | Allowed values |
| --- | --- | --- |
| `sei` | loomweave (identity) | `present`, `absent`, `unavailable` |
| `edges` | loomweave (structure) | `present`, `absent`, `stale`, `partial`, `skipped`, `unavailable` |
| `work` | filigree (work state) | `present`, `absent`, `unavailable` |
| `risk` | wardline (trust policy) | `present`, `absent`, `unavailable` |
| `governance` | legis (governance / rename feed) | `present`, `absent`, `unavailable` |
| `requirements` | (reserved) | `present`, `absent`, `unavailable` |

The three core values mean distinct things, and the distinction is the whole point:

- **`present`** — the peer is present and a fact is attached for this entity.
- **`absent`** — the peer is present, but it has no fact for this entity. This is
  a real, informative answer: "I asked, and there is nothing." It is **not** an
  error.
- **`unavailable`** — the peer is unreachable (not installed, not running, no
  index). warpline could not ask. Also **not** an error — and never an implied
  clean/allowed/governed state.

> `absent` ≠ `unavailable`, and neither is ever a transport error or an implied
> "clean."

If warpline did not draw this distinction, "the wardline peer is down" and "wardline
checked and found no risk" would look identical — and a caller could read a peer
outage as a safety signal. warpline refuses that conflation by design.

## `completeness` and `staleness` (impact / reverify)

The two graph-traversal tools (`impact_radius`, `reverify`) carry two extra
mandatory fields. They report how much of the answer warpline could actually
compute:

| `completeness` | What happened |
| --- | --- |
| `FULL` | A snapshot exists and the neighborhood captured fully. |
| `DELTA` | A snapshot exists but some entities failed (`failed_entities` lists them). Treat the affected set as a floor. |
| `NO_SNAPSHOT` | No usable snapshot — changed set only. Run `capture_snapshot`, then retry. |
| `SKIPPED` | A capture ran but loomweave was absent; no edges recorded. Same as `NO_SNAPSHOT` for traversal. |

`staleness.commits_behind` is how far the snapshot lags `HEAD`; `staleness.snapshot_commit`
is the commit it was captured at. When there is no snapshot, both are `null`.

A `warnings[]` entry restates any non-`FULL` completeness in prose, so the
limitation is visible even if a caller ignores the structured field.

## What "degrade" looks like in practice

| Sibling | Present and indexed | Absent / unreachable |
| --- | --- | --- |
| loomweave | SEIs resolve (`sei: present`); snapshots capture (`edges: present`, `completeness: FULL`). | `sei: unavailable` / `absent`; `capture_snapshot` returns `completeness: SKIPPED`; impact/reverify return `NO_SNAPSHOT`. |
| filigree | Work links enrich the worklist (`work: present`); items gain a `priority`. | `work: unavailable`; `priority: unknown`; `next_actions.filigree` empty. |
| wardline | Risk enriches ordering (`risk: present`). | `risk: unavailable` — never `clean`. |
| legis / rename feed | Timeline stitched across renames (`governance: present`). | `governance: unavailable`; warpline falls back to raw git. |

In every absent case the answer is still well-formed and still useful — it simply
says, in machine-readable form, exactly how much it is missing. That is what
"degrade honestly" means: the answer gets thinner, never wronger, and it tells you
it got thinner.

## Local-only and side-effect-free

Every outbound answer also carries, in `meta`:

- `local_only: true` — the call read and wrote only warpline's own local state.
- `peer_side_effects: []` — warpline caused no change in any sibling.

Even `capture_snapshot`, the one mutating tool, only ever writes to
`.weft/warpline/`. warpline never mutates a sibling repo.
