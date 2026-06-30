# 03 — Architecture Diagrams

Mermaid diagrams for `warpline` at HEAD `def6d43`. Render in any Mermaid-aware viewer (GitHub, VS Code,
mermaid.live).

---

## C4 L1 — System Context

Where warpline sits in the Weft federation and its environment. warpline is **enrich-only** and
**local-first**: it functions with no sibling present and writes only under `.weft/warpline/`.

```mermaid
flowchart TB
    agent["AI Agent / Developer<br/>(MCP host or terminal)"]
    subgraph weft["Weft federation (sibling tools, all optional)"]
        loom["loomweave<br/>(graph + SEI authority — 'now')"]
        filigree["filigree<br/>(issue tracker / work-state)"]
        wardline["wardline<br/>(trust-boundary / attest risk)"]
        legis["legis · plainweave<br/>(governance / policy)"]
    end
    git[("git repository<br/>(history)")]
    store[(".weft/warpline/warpline.db<br/>SQLite temporal store")]

    agent -->|"CLI / MCP tools"| warpline(["warpline<br/>temporal change-impact authority"])
    warpline -->|"reads history"| git
    warpline -->|"reads/writes (only this)"| store
    warpline -.->|"SEI + edges (subprocess)"| loom
    warpline -.->|"work-state (HTTP)"| filigree
    warpline -.->|"attest risk (CLI)"| wardline
    warpline -.->|"governance read (CLI)"| legis
    warpline ==>|"advisory facts (never gates)"| agent

    classDef opt stroke-dasharray:4 3;
    class loom,filigree,wardline,legis opt;
```

*Dashed = optional sibling, consulted only when present; absence is reported explicitly
(`unavailable`), never as a clean state.*

---

## C4 L2 — Containers (process & store boundaries)

warpline ships two executables over one shared core, plus an embedded SQLite store and an isolated
loomweave subprocess.

```mermaid
flowchart TB
    subgraph host["warpline package (one wheel, zero runtime deps)"]
        cli["CLI surface<br/>warpline.cli:main<br/>(argparse)"]
        mcp["MCP server<br/>warpline.mcp:main<br/>(JSON-RPC / stdio)"]
        core["Command core<br/>commands.py<br/>(8 tool bodies)"]
        dom["Domain core<br/>store + pure compute"]
        cli --> core
        mcp --> core
        core --> dom
    end
    db[("SQLite<br/>warpline.db (WAL)<br/>.weft/warpline/")]
    loomproc["loomweave serve<br/>(subprocess, stdio JSON-RPC)"]
    gitproc["git<br/>(subprocess)"]

    dom -->|"sqlite3"| db
    dom -->|"LoomweaveMcpClient"| loomproc
    dom -->|"subprocess"| gitproc

    hook["git post-commit hook<br/>warpline ingest-commit"] --> cli
    session["Claude SessionStart hook<br/>warpline session-context"] --> cli
```

---

## C4 L3 — Components (the 8 subsystems)

Layered flow toward the foundation; **module-acyclic** (one S2↔S3 back-edge, dotted below). (See
02-subsystem-catalog.md for module membership.)

```mermaid
flowchart TD
    S7["S7 Interface Surfaces<br/>cli · mcp · mcp_smoke"]
    S8["S8 Lifecycle & Productization<br/>install · install_support · productization · dogfood"]
    S4["S4 Command Orchestration<br/>commands · cop"]
    S3["S3 Domain Compute (pure)<br/>_blast · propagation · _completeness<br/>coupling · verification · _attest · reverify"]
    S6["S6 Federation Enrichment Seams<br/>federation · siblings"]
    S5["S5 Resolution & Ingestion Seams<br/>loomweave · git · reresolve"]
    S2["S2 Temporal Store<br/>store · snapshot"]
    S1["S1 Contract & Envelope Foundation<br/>errors · envelope · _enrichment<br/>listing · refs · locators"]

    S7 --> S4
    S7 --> S8
    S7 --> S2
    S8 --> S4
    S8 --> S5
    S8 --> S2
    S4 --> S3
    S4 --> S5
    S4 --> S6
    S4 --> S2
    S3 --> S2
    S3 --> S5
    S3 --> S6
    S6 --> S5
    S5 --> S2
    S4 --> S1
    S3 --> S1
    S5 --> S1
    S6 --> S1
    S7 --> S1
    S2 -. "lazy: store→coupling" .-> S3
    S7 -. "lazy: cli→coupling" .-> S3

    S1:::foundation
    classDef foundation fill:#e8f0fe,stroke:#4264d0;
```

*S1 (Contract Foundation, highlighted) and S2 (Store) are **parallel** foundations — neither imports
the other; S2 has no module-level internal imports (fan_in 38, fan_out 0), which anchors the graph.
The **dotted edges are the S2↔S3 back-edge**: `store`/`cli` reach into `coupling` (S3) via deferred
function-body imports, so the module graph stays acyclic (`coupling` is a pure leaf) while the
subsystem graph has a real `store`↔`compute` cycle. Verified by `analysis-validator` against the raw
import statements (loomweave's graph omits function-body imports). For readability two real edges are
elided: S7 (Surfaces) also reaches S5/S6 directly, and S8→S7 (`dogfood.py:20` drives `mcp.dispatch`).*

---

## Data model — SQLite schema

8 base tables (`store.py:35-107`) + **2 migration-added tables** (`co_change_pairs` v3,
`verification_events` v4) + v2 anchor *columns* on `change_events`. Note: `co_change_pairs` and
`snapshot_edges` reference `entity_key_id` **without a `FOREIGN KEY`** — integrity is maintained in
application code.

```mermaid
erDiagram
    repos ||--o{ entity_keys : "repo_id"
    repos ||--o{ commit_refs : "repo_id"
    repos ||--o{ change_events : "repo_id"
    repos ||--o{ edge_snapshots : "repo_id"
    entity_keys ||--o{ change_events : "entity_key_id (FK)"
    edge_snapshots ||--o{ snapshot_edges : "snapshot_id (FK)"
    entity_keys ||..o{ snapshot_edges : "src/tgt id (no FK)"
    entity_keys ||..o{ co_change_pairs : "a/b id (no FK)"

    repos { TEXT id PK }
    entity_keys { INT id PK "locator, sei(nullable), first/last_seen_commit" }
    commit_refs { TEXT sha PK "parents_json, author, authored_at, committed_at" }
    change_events { INT id PK "commit_sha, path, change_kind, actor, changed_at; v2: detected_*" }
    edge_snapshots { INT id PK "commit_sha, source, source_version, completeness" }
    snapshot_edges { INT snapshot_id "source/target_entity_key_id, edge_kind, confidence" }
    co_change_pairs { TEXT repo_id "entity_key_id_a/b, co_change_count, last_co_change" }
    verification_events { INT id PK "commit_sha, kind, verified_at, actor, source" }
    meta { TEXT key PK "value (schema_version, throttle markers)" }
    health_log { INT id PK "code, message, created_at" }
```

---

## Sequence — the core change → reverify loop

The flow an agent runs before claiming a change is done. Shows the always-on lazy snapshot capture and
the fail-soft sibling consults.

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant C as commands.py (S4)
    participant ST as WarplineStore (S2)
    participant G as git (S5)
    participant L as loomweave (S5)
    participant F as siblings/federation (S6)

    A->>C: change_list(rev_range)
    C->>G: rev_range_commits
    C->>ST: list_change_events
    ST-->>C: changed entities (+ next_actions)
    C-->>A: warpline.change_list.v1

    A->>C: reverify_worklist(changed_refs, depth, include_federation?)
    C->>ST: resolve_changed_inputs → key_ids
    alt no usable snapshot AND loomweave reachable
        C->>L: probe + capture_edge_snapshot (lazy, fail-soft)
        L-->>ST: snapshot_edges
    else loomweave absent
        Note over C: throttle marker set, fall through to NO_SNAPSHOT (honest)
    end
    C->>ST: blast_radius (pure BFS over edges)
    C->>ST: verification freshness (git reachability)
    opt include_federation
        C->>F: consult filigree / wardline / legis (read-only)
        F-->>C: per-member facts + weft_reason (or disabled/unreachable)
    end
    C-->>A: warpline.reverify_worklist.v1<br/>(items + verification_summary + risk + completeness)
```

---

## Diagram notes & caveats

- Diagrams reflect `src/` at HEAD `def6d43`; the L3 component graph is derived from import blocks +
  the loomweave edge graph (tombstone `heddle.*` edges excluded).
- The ER diagram simplifies column lists; authoritative DDL is `store.py:35-107` + the `_migrate_v*`
  functions. The `||..o{` (dotted) relations denote integer references **without** a DB-level foreign
  key (a noted fragility — see 02/05).
- The sequence diagram omits the list-ergonomics pipeline (filter/sort/overflow/page) applied to every
  list result and the `build_envelope` step common to all tools.
