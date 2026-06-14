# Temporal facts vs. the current graph

warpline owns exactly one thing, and it is defined by contrast with its sibling
loomweave:

- **loomweave owns "now."** It holds the current structural graph of your code —
  what calls what, what references what, right now — and it mints stable entity
  identity (SEI).
- **warpline owns "over time."** It holds *temporal facts*: which entity changed,
  in which commit, by whom, when. And it holds *dated edge snapshots* — a copy of
  loomweave's edges as they stood at a particular commit, stamped with that
  commit.

That split is the whole design. warpline never tries to answer "what does the code
look like now" — that is loomweave's job, and loomweave's answer is always more
current. warpline answers "what has happened to this code, and what does a change
to it touch."

## What warpline stores

warpline's local store (`.weft/warpline/warpline.db`, a SQLite database) holds:

| Stored fact | What it is |
| --- | --- |
| Entity keys | One row per entity warpline has observed, carrying both its `locator` and its resolved `sei` (when known). |
| Change events | One row per `(entity, commit, path, change_kind)` — the append-only history of what changed. `change_kind` is `added`, `modified`, `removed`, or `moved`. |
| Commit refs | The commit metadata (author, parents, authored/committed timestamps) behind each change. |
| Edge snapshots | A dated capture of loomweave's edges at a given commit, stamped with `completeness` and `source_version`. |
| Snapshot edges | The individual `(source, target, edge_kind, confidence)` edges within a snapshot. |

Entities are extracted per commit. For a `.py` file, warpline derives
function/class locators (`python:function:<path>::<qualname>`,
`python:class:<path>::<qualname>`); for any other file, it tracks the file as
`file:<path>`.

## What warpline deliberately does not store

> warpline stores only the temporal facts it owns; it never mirrors the current
> graph.

This is a load-bearing rule, not an omission. If warpline cached "the current
graph," it would immediately begin to drift from loomweave's live truth and become
a stale duplicate that two tools now disagree about. warpline avoids that by
storing only **dated** edge snapshots — every edge warpline holds is explicitly
stamped with the commit it was true at, and the `staleness` field on every
impact/reverify answer tells you how far that snapshot now lags `HEAD`.

So warpline's edges are never claimed to be "current." They are a historical
record: "as of commit `abc1234`, these edges held." When you want "now," you ask
loomweave.

## Why this matters when you read an answer

Because warpline's graph is dated, a blast-radius answer is only as fresh as its
snapshot. warpline never hides this:

- `completeness` tells you whether a usable snapshot exists at all.
- `staleness.commits_behind` tells you how many commits have landed since the
  snapshot was captured.

A snapshot that is 40 commits behind can still be useful, but warpline makes you
see that it is 40 commits behind rather than presenting it as current truth. See
[Degrade behavior](degrade.md) for how to read these fields.
