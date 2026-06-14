# SEI: consumed, never minted

A **SEI** (stable entity identity) is Loomweave's identifier for a code entity
that survives renames and moves. It looks like `loomweave:eid:` followed by 32 hex
characters:

```text
loomweave:eid:0123456789abcdef0123456789abcdef
```

warpline keys its temporal facts on SEI whenever it can resolve one. That is what
lets a single entity's history stay coherent even as the file it lives in is
renamed or the function is moved.

## warpline consumes SEI; it never mints it

This is a hard boundary. **Loomweave is the identity authority.** warpline:

- **Resolves** a locator to a SEI by asking loomweave (`entity_resolve`).
- **Stores** the resulting `loomweave:eid:...` string opaquely — it never parses,
  interprets, or generates the value.
- **Refuses** to invent a SEI of its own when loomweave is absent.

If warpline minted its own identities, the federation would have two competing
identity authorities and no single source of truth for "is this the same entity."
warpline declines that role. When it cannot resolve a SEI, it says so honestly
rather than fabricating one.

## Every entity carries both `locator` and `sei`

In every warpline-outbound answer, an entity is reported with both keys:

```json
{"locator": "python:function:src/demo/auth.py::login", "sei": null}
```

- `locator` — warpline's local, path-and-qualname-based handle. Always present.
- `sei` — the resolved Loomweave SEI, or `null` when warpline has not resolved one.

When you key off a warpline answer in another tool, **key on `sei` (preferred), or
`locator` when no SEI is known.** Do *not* key on `warpline_entity_key_id`: that is
a warpline-internal auto-increment row id, echoed only for convenience, and is
**not** a federation key.

## The honesty signal: `sei_resolution`

The `timeline` tool reports a `sei_resolution` field on the entity:

| `sei_resolution` | Meaning |
| --- | --- |
| `resolved` | warpline resolved a real SEI for this entity. |
| `unresolved` | warpline observed the entity but could not resolve a SEI (loomweave absent, or it returned none). |
| `unknown` | warpline has no record of this entity at all. |

`sei_resolution` is warpline's **local honesty signal about its own resolution
state** — it is explicitly *not* a lineage claim. warpline never asserts "entity A
is the same as entity B across a rename" on its own authority; that is lineage, and
lineage belongs to loomweave (and, for locator renames, to the rename feed —
see [Federation](../federation.md)).
