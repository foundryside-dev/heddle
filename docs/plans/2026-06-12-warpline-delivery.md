# Warpline Delivery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver Warpline as an agent-first, local-first temporal change-impact product that answers what changed, who/when, what is downstream-affected, and what must be re-verified without becoming a sibling-state aggregator, then prepare the post-admission federation integration work.

**Architecture:** Build a Python 3.12 package with a shared core library, SQLite temporal store, CLI, and first-class MCP stdio server over the same command handlers. Warpline consumes git as the hard dependency, consumes Loomweave/Legis/Filigree/Wardline/Charter only through their current published surfaces, and treats every sibling absence or mismatch as explicit degraded enrichment rather than a failure. Productization is gated by the spike evidence: without `spike/REPORT.md` and a `go` recommendation, implementation may produce a prototype but must not freeze federation contracts or patch sibling consumers. Warpline must never report a dated snapshot as current unless it has compared that snapshot commit to the current repo HEAD.

**Tech Stack:** Python 3.12, uv, stdlib `sqlite3`, stdlib `argparse`, dependency-free JSON-RPC MCP over stdio, pytest, ruff, mypy. SQLite is embedded and one DB per analyzed repo under a Warpline user-data directory.

**Prerequisites:**
- Work in a dedicated Warpline worktree or branch, with no new changes in `<filigree-root>`, `<wardline-root>`, `<legis-root>`, `<loomweave-root>`, or `<charter-root>`.
- Before executing implementation tasks, record the current sibling dirty state in `docs/evidence/2026-06-13-source-grounding.md`. If any sibling repo is already dirty, treat it as a pre-existing condition and require `scripts/check_no_member_diffs.sh` to fail on any additional unexpected dirty state; do not clean or revert sibling repos from this plan.
- Install `uv`, `git`, and `sqlite3`.
- Confirm sibling interfaces from source before coding against them; do not patch sibling repos during Phase 0.
- Treat MCP as a primary surface: every read query that exists in the CLI must have an MCP tool with structured JSON output before the slice is considered done.
- Treat `spike/REPORT.md` as the authority for spike findings. If it does not exist, run Task 12 before any product-release or federation-integration task.
- Owner admission is still out of scope for this repo. The plan can prepare integration tickets and fixtures; it cannot declare Warpline admitted.

---

## Source-Grounded Interface Facts

These facts were checked against local source and override Warpline prose where they differ.

- **Weft product doctrine:** `<weft-root>/doctrine.md` says Weft is a federation, not a shared runtime/store/broker, and doctrine §7 reserves the future-product go/no-go test: one bounded authority, solo-useful, pairwise-sensible, suite-additive. `<weft-root>/pm/product/decisions/0013-post-launch-priority-stack-and-discovery-pipeline.md` names Warpline as the next discovery slot and sets the standing admission bar: dogfood pain evidence, grep-test preference, enrich-only composition, doctrine fit, and hook-fed operation. `<weft-root>/federation-sdk.md` requires SEI opacity, enrich-only behavior, and honest degradation when sibling capabilities are absent.
- **Weft Warpline status:** `<weft-root>/members/warpline.md` says Warpline has no package, CLI, MCP server, or source implementation yet, and describes it as a design spike whose proposed authority is temporal/change-impact. `<weft-root>/roadmap-ideas.md` says the Warpline idea survives only if it is bounded as temporal graph authority rather than a forbidden aggregator.
- **Loomweave:** `<loomweave-root>/README.md` says `loomweave analyze` persists entities and edges to `.weft/loomweave/loomweave.db`, `loomweave serve` exposes about 42 MCP tools, and the core read tools include `entity_find`, `entity_callers_list`, `entity_neighborhood_get`, `entity_source_get`, `entity_resolve`, and `project_status_get`. `<loomweave-root>/crates/loomweave-mcp/src/lib.rs` defines the live tool list and marks write tools gated. `<loomweave-root>/crates/loomweave-cli/src/cli.rs` shows `loomweave analyze [path]`, `loomweave serve --path`, `--legis-url`, `--no-sei`, and `--no-incremental`. `<loomweave-root>/crates/loomweave-storage/src/sei.rs` makes SEI opaque and stored in `sei_bindings`, with `loomweave:eid:*` reserved.
- **Legis:** `<legis-root>/README.md` says Legis is the git/CI and governance member; Loomweave remains identity authority, Legis consumes SEI, and its git rename feed is contract-locked. `<legis-root>/src/legis/api/app.py` exposes `/git/rename-feed`, `/git/renames`, `/git/commits/{sha}`, and governance surfaces. `<legis-root>/tests/git/test_rename_feed.py` pins committed and worktree rename-feed shapes.
- **Filigree:** `<filigree-root>/README.md` says Filigree is the issue/work-state authority with agent-native MCP and CLI. `<filigree-root>/tests/fixtures/contracts/weft/scan-results.json` pins `POST /api/weft/scan-results` and shows fingerprints and `scan_source` are the durable scanner lifecycle surface. Warpline must not file work by default during Phase 0; post-admission filing is optional enrichment.
- **Wardline:** `<wardline-root>/README.md` says Wardline is trust/finding authority; `wardline mcp` exposes `scan`, `explain_taint`, `file_finding`, `assure`, and `attest`. `<wardline-root>/src/wardline/core/agent_summary.py` makes agent handoff and next-tool-call structure first-class. Warpline must output scoped reverify sets that Wardline can consume later, but Warpline must not re-derive Wardline policy.
- **Charter:** `<charter-root>/README.md` says the local core and `charter-mcp` read surface exist, but mutation, live federation calls, impact analysis, durable gaps, import/export, and release-readiness verdicts remain deferred. `<charter-root>/src/charter/mcp_surface.py` exposes ten read-only, local-only MCP tools and explicitly declares no peer side effects. `<charter-root>/docs/agentic-doors-replacement-roadmap.md` lists impact analysis as P1 and gives the future `charter impact diff BASE..HEAD --json` shape. Warpline must therefore treat Charter as a post-admission consumer of reverify/impact facts, not as a live impact API.

## Delivery Shape

Deliver three gated slices:

1. **Evidence gate:** collect and record spike findings in `spike/REPORT.md`. If the recommendation is `no-go` or `park-until-cutover`, stop productization and produce only the evidence/report.
2. **Prototype slice:** Tasks 1-11 may build the standalone local-first Warpline prototype needed to generate spike evidence: package, store, git ingest, CLI, MCP, Loomweave probe/snapshots, blast radius, and reverify worklist. These tasks do not freeze federation contracts.
3. **Product slice:** after a `go` recommendation, run the productization gate and add release-candidate checks.
4. **Federation-integration preparation:** after a `go` recommendation, prepare Warpline-owned draft contract fixtures and sibling-owned consumer tickets. After owner admission, sibling repos can implement their consumers on their own trackers.

The product slice is:

1. A new Python package with CLI and MCP surfaces.
2. A SQLite temporal store outside the analyzed repo.
3. Git backfill for commit/entity change events, with `path + qualname` locators where cheap and file locators only as an honest fallback.
4. Locator-keyed changed-set and timeline queries.
5. A source-grounded Loomweave probe that proves whether graph edges can be read safely.
6. Blast-radius and reverify worklist queries that are honest about `NO_SNAPSHOT`, staleness, and completeness.
7. A spike report with measured go/no-go evidence.

If any step requires a diff in Filigree, Wardline, Legis, Loomweave, or Charter, stop that step and record a constraint conflict in `spike/REPORT.md`.

---

### Task 0: Freeze Source-Grounded Evidence Before Coding

**Files:**
- Create: `docs/evidence/2026-06-13-source-grounding.md`
- Create: `docs/evidence/member-dirty-baseline.txt`
- Create: `scripts/check_source_grounding.py`
- Later test mirror: `tests/test_source_grounding.py` after Task 1 creates the Python project

**Step 1: Write the dependency-free failing evidence check**

```python
# scripts/check_source_grounding.py
from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_SOURCES = [
    "<weft-root>/doctrine.md",
    "<weft-root>/pm/product/decisions/0013-post-launch-priority-stack-and-discovery-pipeline.md",
    "<weft-root>/federation-sdk.md",
    "<weft-root>/members/warpline.md",
    "<loomweave-root>/README.md",
    "<loomweave-root>/crates/loomweave-mcp/src/lib.rs",
    "<loomweave-root>/crates/loomweave-cli/src/cli.rs",
    "<loomweave-root>/crates/loomweave-storage/src/sei.rs",
    "<legis-root>/src/legis/api/app.py",
    "<legis-root>/tests/git/test_rename_feed.py",
    "<filigree-root>/docs/federation/contracts.md",
    "<filigree-root>/tests/fixtures/contracts/weft/scan-results.json",
    "<wardline-root>/src/wardline/core/agent_summary.py",
    "<wardline-root>/src/wardline/core/filigree_emit.py",
    "<charter-root>/src/charter/mcp_surface.py",
    "<charter-root>/docs/agentic-doors-replacement-roadmap.md",
]


def main() -> int:
    manifest = Path("docs/evidence/2026-06-13-source-grounding.md")
    if not manifest.exists():
        print("missing docs/evidence/2026-06-13-source-grounding.md", file=sys.stderr)
        return 1
    baseline = Path("docs/evidence/member-dirty-baseline.txt")
    if not baseline.exists():
        print("missing docs/evidence/member-dirty-baseline.txt", file=sys.stderr)
        return 1
    text = manifest.read_text(encoding="utf-8")
    missing = [path for path in REQUIRED_SOURCES if path not in text]
    missing_tokens = [
        token
        for token in (
            "spike/REPORT.md",
            "owner admission",
            "no sibling repo patches",
            "pre-existing sibling dirty state",
        )
        if token not in text
    ]
    if missing or missing_tokens:
        print({"missing_sources": missing, "missing_tokens": missing_tokens}, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Why this test:** The productization plan must be traceable to the live sibling and Weft sources, not only to Warpline's local design prose.

**Step 2: Run test to verify it fails**

Run: `python scripts/check_source_grounding.py`

Expected output:

```text
missing docs/evidence/2026-06-13-source-grounding.md
```

**Step 3: Write the evidence manifest**

```markdown
# Warpline Source Grounding Evidence

## Productization Gate
- `spike/REPORT.md` is the required authority for design-spike findings.
- Product release work proceeds only on `Recommendation: go`.
- Owner admission is required before member-side consumer wiring.
- Phase 0 rule: no sibling repo patches in `<filigree-root>`, `<wardline-root>`, `<loomweave-root>`, `<legis-root>`, or `<charter-root>`.
- Pre-existing sibling dirty state must be recorded before implementation starts. This plan does not authorize cleaning, reverting, or patching sibling repos.

## Sources Checked
- `<weft-root>/doctrine.md` — federation doctrine, enrich-only, no shared runtime/store/broker, owner admission test.
- `<weft-root>/pm/product/decisions/0013-post-launch-priority-stack-and-discovery-pipeline.md` — Warpline discovery slot and agentic-first bar.
- `<weft-root>/federation-sdk.md` — member obligations, SEI opacity, honest degradation.
- `<weft-root>/members/warpline.md` — Warpline is design spike; no implementation yet.
- `<loomweave-root>/README.md` — graph/identity authority and live MCP families.
- `<loomweave-root>/crates/loomweave-mcp/src/lib.rs` — live MCP tool names.
- `<loomweave-root>/crates/loomweave-cli/src/cli.rs` — `analyze`, `serve`, `--legis-url`, `--no-sei`, `--no-incremental`.
- `<loomweave-root>/crates/loomweave-storage/src/sei.rs` — SEI prefix, opacity, lineage storage.
- `<legis-root>/src/legis/api/app.py` — git and governance HTTP routes.
- `<legis-root>/tests/git/test_rename_feed.py` — rename-feed shape and worktree flag semantics.
- `<filigree-root>/docs/federation/contracts.md` — named HTTP generations and `weft` envelope discipline.
- `<filigree-root>/tests/fixtures/contracts/weft/scan-results.json` — scan-results contract fixture.
- `<wardline-root>/src/wardline/core/agent_summary.py` — agent summary schema and next-action discipline.
- `<wardline-root>/src/wardline/core/filigree_emit.py` — native Filigree emit shape and fail-soft enrichment.
- `<charter-root>/src/charter/mcp_surface.py` — local-only read MCP tools and contract resources.
- `<charter-root>/docs/agentic-doors-replacement-roadmap.md` — impact analysis is P1/deferred and Charter integration is planned.
```

Create `docs/evidence/member-dirty-baseline.txt` with the exact output of:

```bash
for repo in <filigree-root> <wardline-root> <legis-root> <loomweave-root> <charter-root>; do
  printf '## %s\n' "$repo"
  git -C "$repo" status --short || true
done
```

This is not permission to modify sibling repos. It records pre-existing sibling dirty state so later gates can detect newly introduced drift.

**Why minimal:** This creates a small, auditable source inventory. It does not copy sibling schemas into Warpline.

**Step 4: Run check to verify it passes**

Run: `python scripts/check_source_grounding.py`

Expected output:

```text
<no output, exit 0>
```

**Step 5: After Task 1, mirror this as a pytest test**

```python
# tests/test_source_grounding.py
from __future__ import annotations

from scripts.check_source_grounding import main


def test_source_grounding_manifest_is_current() -> None:
    assert main() == 0
```

Run: `uv run pytest tests/test_source_grounding.py -v`

Expected output:

```text
1 passed
```

**Step 6: Commit**

```bash
git add docs/evidence/2026-06-13-source-grounding.md scripts/check_source_grounding.py tests/test_source_grounding.py
git commit -m "docs: record warpline source grounding"
```

**Definition of Done:**
- [ ] Evidence manifest exists and names every live source used for productization.
- [ ] Manifest records `spike/REPORT.md` as the spike-finding authority.
- [ ] Manifest states owner admission and no sibling repo patches.

---

### Task 1: Scaffold Warpline as a Python Package

**Files:**
- Create: `pyproject.toml`
- Create: `src/warpline/__init__.py`
- Create: `src/warpline/cli.py`
- Create: `src/warpline/mcp.py`
- Create: `src/warpline/errors.py`
- Create: `tests/test_package.py`

**Step 1: Write the failing tests**

```python
# tests/test_package.py
from __future__ import annotations

import subprocess
import sys

import warpline


def test_package_has_version() -> None:
    assert warpline.__version__ == "0.1.0"


def test_cli_version() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "warpline.cli", "--version"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert completed.stdout.strip() == "warpline 0.1.0"
```

**Why this test:** It proves the package imports and has a runnable human CLI before any product behavior is added.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline'
```

**Step 3: Write minimal implementation**

```toml
# pyproject.toml
[project]
name = "warpline"
version = "0.1.0"
description = "Temporal change-impact authority for agentic code work"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
warpline = "warpline.cli:main"
warpline-mcp = "warpline.mcp:main"

[dependency-groups]
dev = [
  "pytest>=8.0",
  "ruff>=0.11",
  "mypy>=1.10",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "S"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["warpline"]
```

```python
# src/warpline/__init__.py
__version__ = "0.1.0"
```

```python
# src/warpline/errors.py
from __future__ import annotations


class WarplineError(Exception):
    code = "WARPLINE_ERROR"


class BadRevisionError(WarplineError):
    code = "BAD_REVISION"


class NotIngestedError(WarplineError):
    code = "NOT_INGESTED"


class UnknownEntityError(WarplineError):
    code = "UNKNOWN_ENTITY"
```

```python
# src/warpline/cli.py
from __future__ import annotations

import argparse

from warpline import __version__, commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="warpline")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"warpline {__version__}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# src/warpline/mcp.py
from __future__ import annotations


def main() -> int:
    return 0
```

**Why minimal:** This creates the package and entrypoints only; no behavior is hidden in scaffold code.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_package.py -v`

Expected output:

```text
2 passed
```

**Step 5: Commit**

```bash
git add pyproject.toml src/warpline tests/test_package.py
git commit -m "feat: scaffold warpline package"
```

**Definition of Done:**
- [ ] Tests fail before package exists.
- [ ] `warpline --version` and `python -m warpline.cli --version` work.
- [ ] `uv run ruff check .` passes.
- [ ] Changes are committed.

---

### Task 2: Create Temporal Store Outside the Analyzed Repo

**Files:**
- Create: `src/warpline/store.py`
- Create: `tests/test_store.py`

**Step 1: Write the failing tests**

```python
# tests/test_store.py
from __future__ import annotations

from pathlib import Path

from warpline.store import WarplineStore, default_store_path


def test_default_store_path_is_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = default_store_path(repo, base_dir=tmp_path / "state")
    assert path.parent == tmp_path / "state"
    assert repo not in path.parents


def test_store_initializes_schema(tmp_path: Path) -> None:
    db = tmp_path / "warpline.db"
    with WarplineStore.open(db) as store:
        assert store.schema_version() == 1
```

**Why this test:** It pins NFR-05 before any ingest code can accidentally write state into an analyzed repo.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.store'
```

**Step 3: Write minimal implementation**

```python
# src/warpline/store.py
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path
from types import TracebackType


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', '1');
CREATE TABLE IF NOT EXISTS repos (
  id TEXT PRIMARY KEY,
  root TEXT NOT NULL,
  remote_fingerprint TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS entity_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  locator TEXT NOT NULL,
  sei TEXT,
  first_seen_commit TEXT,
  last_seen_commit TEXT,
  FOREIGN KEY(repo_id) REFERENCES repos(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS entity_keys_unique
  ON entity_keys(repo_id, locator, COALESCE(sei, ''));
CREATE TABLE IF NOT EXISTS commit_refs (
  repo_id TEXT NOT NULL,
  sha TEXT NOT NULL,
  parents_json TEXT NOT NULL,
  author TEXT NOT NULL,
  authored_at TEXT NOT NULL,
  committed_at TEXT NOT NULL,
  PRIMARY KEY(repo_id, sha)
);
CREATE TABLE IF NOT EXISTS change_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  entity_key_id INTEGER NOT NULL,
  commit_sha TEXT NOT NULL,
  path TEXT NOT NULL,
  change_kind TEXT NOT NULL,
  actor TEXT NOT NULL,
  changed_at TEXT NOT NULL,
  hunk_summary TEXT NOT NULL DEFAULT '',
  UNIQUE(repo_id, entity_key_id, commit_sha, path, change_kind),
  FOREIGN KEY(entity_key_id) REFERENCES entity_keys(id)
);
CREATE TABLE IF NOT EXISTS edge_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  commit_sha TEXT NOT NULL,
  source TEXT NOT NULL,
  source_version TEXT NOT NULL,
  captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completeness TEXT NOT NULL,
  UNIQUE(repo_id, commit_sha, source)
);
CREATE TABLE IF NOT EXISTS snapshot_edges (
  snapshot_id INTEGER NOT NULL,
  source_entity_key_id INTEGER NOT NULL,
  target_entity_key_id INTEGER NOT NULL,
  edge_kind TEXT NOT NULL,
  confidence TEXT NOT NULL,
  PRIMARY KEY(snapshot_id, source_entity_key_id, target_entity_key_id, edge_kind),
  FOREIGN KEY(snapshot_id) REFERENCES edge_snapshots(id)
);
CREATE TABLE IF NOT EXISTS health_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id TEXT NOT NULL,
  code TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def default_store_path(repo: Path, base_dir: Path | None = None) -> Path:
    root = repo.resolve()
    state_root = Path(os.environ["XDG_STATE_HOME"]) if "XDG_STATE_HOME" in os.environ else Path.home() / ".local/state"
    state = base_dir or state_root / "warpline"
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return state / f"warpline-{digest}.db"


class WarplineStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @classmethod
    def open(cls, path: Path) -> "WarplineStore":
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        return cls(conn)

    def __enter__(self) -> "WarplineStore":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.conn.close()

    def schema_version(self) -> int:
        row = self.conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        if row is None:
            raise RuntimeError("missing schema_version")
        return int(row["value"])
```

**Why minimal:** Schema includes only requirement-owned facts: temporal events, dated snapshots, key lineage, and health logs.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -v`

Expected output:

```text
2 passed
```

**Step 5: Commit**

```bash
git add src/warpline/store.py tests/test_store.py
git commit -m "feat: add warpline temporal store"
```

**Definition of Done:**
- [ ] Store path is outside analyzed repo.
- [ ] Schema initializes idempotently.
- [ ] Store has no tables for Filigree lifecycle, Wardline policy, Legis attestations, or current Loomweave catalog.

---

### Task 3: Implement Git Backfill and Commit-Level Change Events

**Files:**
- Create: `src/warpline/git.py`
- Modify: `src/warpline/store.py`
- Create: `tests/test_git_backfill.py`

**Step 1: Write the failing test**

```python
# tests/test_git_backfill.py
from __future__ import annotations

import subprocess
from pathlib import Path

from warpline.git import backfill
from warpline.store import WarplineStore


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE).stdout


def test_backfill_records_file_change(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    run(["git", "config", "user.email", "agent@example.test"], repo)
    run(["git", "config", "user.name", "Agent"], repo)
    (repo / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    run(["git", "add", "app.py"], repo)
    run(["git", "commit", "-m", "add app"], repo)

    with WarplineStore.open(tmp_path / "warpline.db") as store:
        report = backfill(store, repo)
        events = store.list_change_events(repo)

    assert report["commits"] == 1
    assert len(events) == 1
    assert events[0]["path"] == "app.py"
    assert events[0]["change_kind"] == "added"
    assert events[0]["actor"] == "Agent <agent@example.test>"
```

**Why this test:** It proves FR-05 and the base of FR-01 using only git, before Loomweave is involved.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_git_backfill.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.git'
```

**Step 3: Implement minimal backfill**

Use git porcelain only at the boundary and store normalized rows. The first slice keys file changes by locator `file:<path>`; later tasks upgrade to symbol locators.

```python
# src/warpline/git.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from warpline.store import WarplineStore


def _git(repo: Path, args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _change_kind(status: str) -> str:
    return {"A": "added", "M": "modified", "D": "removed", "R": "moved"}.get(status[0], "modified")


def _commits(repo: Path, since: str | None = None) -> list[str]:
    args = ["log", "--reverse", "--format=%H"]
    if since:
        args.append(f"{since}..HEAD")
    return [line for line in _git(repo, args).splitlines() if line]


def _commit_meta(repo: Path, sha: str) -> dict[str, str]:
    fmt = "%H%x00%P%x00%an <%ae>%x00%aI%x00%cI"
    raw = _git(repo, ["show", "-s", f"--format={fmt}", sha]).strip()
    commit, parents, author, authored_at, committed_at = raw.split("\x00")
    return {
        "sha": commit,
        "parents_json": json.dumps([p for p in parents.split() if p]),
        "author": author,
        "authored_at": authored_at,
        "committed_at": committed_at,
    }


def _name_status(repo: Path, sha: str) -> list[tuple[str, str]]:
    raw = _git(repo, ["diff-tree", "--root", "--no-commit-id", "--name-status", "-r", sha])
    rows: list[tuple[str, str]] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        path = parts[-1]
        rows.append((status, path))
    return rows


def backfill(store: WarplineStore, repo: Path, since: str | None = None) -> dict[str, Any]:
    repo_id = store.ensure_repo(repo)
    count = 0
    for sha in _commits(repo, since=since):
        meta = _commit_meta(repo, sha)
        store.upsert_commit(repo_id, meta)
        for status, path in _name_status(repo, sha):
            locator = f"file:{path}"
            key_id = store.ensure_entity_key(repo_id, locator=locator, sei=None, commit_sha=sha)
            store.append_change_event(
                repo_id=repo_id,
                entity_key_id=key_id,
                commit_sha=sha,
                path=path,
                change_kind=_change_kind(status),
                actor=meta["author"],
                changed_at=meta["authored_at"],
            )
        count += 1
    return {"commits": count}
```

Add these concrete methods to `src/warpline/store.py`:

```python
    def _repo_id(self, repo: Path) -> str:
        return hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()

    def ensure_repo(self, repo: Path) -> str:
        repo_id = self._repo_id(repo)
        root = str(repo.resolve())
        self.conn.execute(
            "INSERT OR IGNORE INTO repos(id, root, remote_fingerprint) VALUES (?, ?, ?)",
            (repo_id, root, None),
        )
        self.conn.commit()
        return repo_id

    def upsert_commit(self, repo_id: str, meta: dict[str, str]) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO commit_refs(
              repo_id, sha, parents_json, author, authored_at, committed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                repo_id,
                meta["sha"],
                meta["parents_json"],
                meta["author"],
                meta["authored_at"],
                meta["committed_at"],
            ),
        )
        self.conn.commit()

    def ensure_entity_key(
        self,
        repo_id: str,
        locator: str,
        sei: str | None,
        commit_sha: str,
    ) -> int:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO entity_keys(
              repo_id, locator, sei, first_seen_commit, last_seen_commit
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (repo_id, locator, sei, commit_sha, commit_sha),
        )
        self.conn.execute(
            """
            UPDATE entity_keys
               SET last_seen_commit = ?
             WHERE repo_id = ?
               AND locator = ?
               AND COALESCE(sei, '') = COALESCE(?, '')
            """,
            (commit_sha, repo_id, locator, sei),
        )
        row = self.conn.execute(
            """
            SELECT id FROM entity_keys
             WHERE repo_id = ?
               AND locator = ?
               AND COALESCE(sei, '') = COALESCE(?, '')
            """,
            (repo_id, locator, sei),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"failed to create entity key for {locator}")
        self.conn.commit()
        return int(row["id"])

    def append_change_event(
        self,
        *,
        repo_id: str,
        entity_key_id: int,
        commit_sha: str,
        path: str,
        change_kind: str,
        actor: str,
        changed_at: str,
        hunk_summary: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO change_events(
              repo_id, entity_key_id, commit_sha, path, change_kind,
              actor, changed_at, hunk_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo_id,
                entity_key_id,
                commit_sha,
                path,
                change_kind,
                actor,
                changed_at,
                hunk_summary,
            ),
        )
        self.conn.commit()

    def list_change_events(self, repo: Path, commit_shas: set[str] | None = None) -> list[dict[str, object]]:
        repo_id = self._repo_id(repo)
        params: list[object] = [repo_id]
        commit_filter = ""
        if commit_shas is not None:
            if not commit_shas:
                return []
            placeholders = ",".join("?" for _ in commit_shas)
            commit_filter = f" AND ce.commit_sha IN ({placeholders})"
            params.extend(sorted(commit_shas))
        rows = self.conn.execute(
            f"""
            SELECT ce.commit_sha, ce.path, ce.change_kind, ce.actor, ce.changed_at,
                   ek.locator, ek.sei
              FROM change_events ce
              JOIN entity_keys ek ON ek.id = ce.entity_key_id
             WHERE ce.repo_id = ?
             {commit_filter}
             ORDER BY ce.changed_at, ce.id
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]
```

Add the idempotence test to `tests/test_git_backfill.py` before implementation:

```python
def test_backfill_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], repo)
    run(["git", "config", "user.email", "agent@example.test"], repo)
    run(["git", "config", "user.name", "Agent"], repo)
    (repo / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    run(["git", "add", "app.py"], repo)
    run(["git", "commit", "-m", "add app"], repo)

    with WarplineStore.open(tmp_path / "warpline.db") as store:
        backfill(store, repo)
        backfill(store, repo)
        assert len(store.list_change_events(repo)) == 1
```

**Why minimal:** File-level events make the cold-start path useful and testable immediately; symbol-level keying is a separate step.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_git_backfill.py tests/test_store.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/git.py src/warpline/store.py tests/test_git_backfill.py
git commit -m "feat: backfill commit change events from git"
```

**Definition of Done:**
- [ ] Backfill works in a repo with only git installed.
- [ ] Re-running backfill does not duplicate rows.
- [ ] No sibling product is imported or required.

---

### Task 3A: Resolve Python Entity Locators in Solo Mode

**Files:**
- Create: `src/warpline/locators.py`
- Modify: `src/warpline/git.py`
- Create: `tests/test_locators.py`

**Step 1: Write the failing tests**

```python
# tests/test_locators.py
from __future__ import annotations

from warpline.locators import python_entity_locators


def test_python_entity_locators_include_path_and_qualname() -> None:
    source = """
class Service:
    def handle(self):
        return 1

def helper():
    return 2
"""
    assert python_entity_locators("pkg/app.py", source) == [
        "python:class:pkg/app.py::Service",
        "python:function:pkg/app.py::Service.handle",
        "python:function:pkg/app.py::helper",
    ]


def test_python_entity_locators_fall_back_to_file_for_syntax_error() -> None:
    assert python_entity_locators("pkg/bad.py", "def nope(:\n") == ["file:pkg/bad.py"]
```

**Why this test:** FR-01 and FR-07 require durable entity locators in solo mode, not only file paths.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_locators.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.locators'
```

**Step 3: Implement locator extraction**

```python
# src/warpline/locators.py
from __future__ import annotations

import ast


def python_entity_locators(path: str, source: str) -> list[str]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return [f"file:{path}"]

    locators: list[str] = []

    def visit_body(body: list[ast.stmt], parents: list[str]) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qualname = ".".join([*parents, node.name])
                locators.append(f"python:class:{path}::{qualname}")
                visit_body(node.body, [*parents, node.name])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = ".".join([*parents, node.name])
                locators.append(f"python:function:{path}::{qualname}")
                visit_body(node.body, [*parents, node.name])

    visit_body(tree.body, [])
    return locators or [f"file:{path}"]
```

Update `src/warpline/git.py` so `_name_status` rows for `.py` files at a commit read the file contents from that commit and emit one change event per locator:

```python
from warpline.locators import python_entity_locators


def _file_at_commit(repo: Path, sha: str, path: str) -> str | None:
    try:
        return _git(repo, ["show", f"{sha}:{path}"])
    except subprocess.CalledProcessError:
        return None


def _locators_for_path(repo: Path, sha: str, path: str) -> list[str]:
    if not path.endswith(".py"):
        return [f"file:{path}"]
    source = _file_at_commit(repo, sha, path)
    if source is None:
        return [f"file:{path}"]
    return python_entity_locators(path, source)
```

Replace the single `locator = f"file:{path}"` branch in `backfill()` and `ingest_commit()` with:

```python
for locator in _locators_for_path(repo, sha, path):
    key_id = store.ensure_entity_key(repo_id, locator=locator, sei=None, commit_sha=sha)
    store.append_change_event(
        repo_id=repo_id,
        entity_key_id=key_id,
        commit_sha=sha,
        path=path,
        change_kind=_change_kind(status),
        actor=meta["author"],
        changed_at=meta["authored_at"],
    )
```

**Why minimal:** This covers the suite's currently documented Python-first Loomweave posture and keeps unsupported languages honest through file locators instead of pretending to resolve symbols.

**Step 4: Run tests**

Run: `uv run pytest tests/test_locators.py tests/test_git_backfill.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/locators.py src/warpline/git.py tests/test_locators.py tests/test_git_backfill.py
git commit -m "feat: derive solo-mode python entity locators"
```

**Definition of Done:**
- [ ] Python classes and functions become `path + qualname` locators.
- [ ] Syntax errors and unsupported file types fall back to `file:<path>`.
- [ ] Warpline still imports no sibling package.

---

### Task 4: Expose Changed-Set and Timeline Through CLI and MCP Together

**Files:**
- Create: `src/warpline/commands.py`
- Modify: `src/warpline/cli.py`
- Modify: `src/warpline/mcp.py`
- Create: `tests/test_commands.py`
- Create: `tests/test_mcp.py`

**Step 1: Write failing CLI and MCP tests**

```python
# tests/test_mcp.py
from __future__ import annotations

from warpline.mcp import dispatch


def test_tools_list_contains_changed_and_timeline() -> None:
    response = dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert {"changed", "timeline"} <= names


def test_unknown_tool_is_structured_error() -> None:
    response = dispatch(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "missing", "arguments": {}},
        }
    )
    assert response["error"]["code"] == -32601
    assert "missing" in response["error"]["message"]
```

```python
# tests/test_commands.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from warpline import cli


def test_cli_changed_outputs_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert cli.main(["changed", "--repo", str(repo), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "changed"
    assert "changed" in payload


def test_cli_timeline_outputs_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert cli.main(["timeline", "--repo", str(repo), "--entity", "file:a.py", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "timeline"
    assert payload["entity"] == "file:a.py"
```

**Why this test:** Agent-first means MCP tool inventory is contract, not a wrapper added later.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mcp.py -v`

Expected output:

```text
ImportError: cannot import name 'dispatch'
```

**Step 3: Implement shared command handlers**

Keep command logic out of CLI and MCP. `src/warpline/commands.py` owns JSON-shaped responses and both surfaces call it.

```python
# src/warpline/commands.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from warpline.store import WarplineStore, default_store_path


def _rev_range_commits(repo: Path, rev_range: str | None) -> set[str] | None:
    if rev_range is None:
        return None
    proc = subprocess.run(
        ["git", "rev-list", rev_range],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {line for line in proc.stdout.splitlines() if line}


def changed(repo: Path, rev_range: str | None = None) -> dict[str, Any]:
    commit_shas = _rev_range_commits(repo, rev_range)
    with WarplineStore.open(default_store_path(repo)) as store:
        return {
            "warpline_schema_version": store.schema_version(),
            "query": "changed",
            "rev_range": rev_range,
            "changed": store.list_change_events(repo, commit_shas=commit_shas),
            "enrichment": {"sei": "absent", "edges": "absent"},
        }


def timeline(repo: Path, entity: str) -> dict[str, Any]:
    with WarplineStore.open(default_store_path(repo)) as store:
        return {
            "warpline_schema_version": store.schema_version(),
            "query": "timeline",
            "entity": entity,
            "events": store.timeline(repo, entity),
            "enrichment": {"sei": "absent", "edges": "absent"},
        }
```

Update `src/warpline/cli.py` in the same task so the CLI and MCP share the same handlers:

```python
import json
from pathlib import Path

from warpline import commands


def _add_query_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    changed_parser = sub.add_parser("changed")
    changed_parser.add_argument("--repo", type=Path, default=Path.cwd())
    changed_parser.add_argument("--rev-range")
    changed_parser.add_argument("--json", action="store_true")
    changed_parser.set_defaults(func=_changed)

    timeline_parser = sub.add_parser("timeline")
    timeline_parser.add_argument("--repo", type=Path, default=Path.cwd())
    timeline_parser.add_argument("--entity", required=True)
    timeline_parser.add_argument("--json", action="store_true")
    timeline_parser.set_defaults(func=_timeline)


def _print_payload(payload: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))


def _changed(args: argparse.Namespace) -> int:
    _print_payload(commands.changed(args.repo, args.rev_range), args.json)
    return 0


def _timeline(args: argparse.Namespace) -> int:
    _print_payload(commands.timeline(args.repo, args.entity), args.json)
    return 0
```

```python
# src/warpline/mcp.py
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from warpline import commands


TOOLS = [
    {
        "name": "changed",
        "description": "List changed entities for an ingested repo. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {"repo": {"type": "string"}, "rev_range": {"type": "string"}},
            "required": ["repo"],
            "additionalProperties": False,
        },
    },
    {
        "name": "timeline",
        "description": "List recorded changes for one entity locator or SEI. Read-only.",
        "inputSchema": {
            "type": "object",
            "properties": {"repo": {"type": "string"}, "entity": {"type": "string"}},
            "required": ["repo", "entity"],
            "additionalProperties": False,
        },
    },
]


def _tool_result(id_value: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": id_value,
        "result": {"content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}]},
    }


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    id_value = request.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": id_value, "result": {"capabilities": {"tools": {}}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": id_value, "result": {"tools": TOOLS}}
    if method != "tools/call":
        return {"jsonrpc": "2.0", "id": id_value, "error": {"code": -32601, "message": str(method)}}
    params = request.get("params") or {}
    name = params.get("name")
    args = params.get("arguments") or {}
    if name == "changed":
        return _tool_result(id_value, commands.changed(Path(args["repo"]), args.get("rev_range")))
    if name == "timeline":
        return _tool_result(id_value, commands.timeline(Path(args["repo"]), args["entity"]))
    return {"jsonrpc": "2.0", "id": id_value, "error": {"code": -32601, "message": str(name)}}


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        print(json.dumps(dispatch(json.loads(line))), flush=True)
    return 0
```

**Why minimal:** This is the smallest useful MCP surface; it is dependency-free and strict enough to be tested.

**Step 4: Run tests**

Run: `uv run pytest tests/test_mcp.py tests/test_commands.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/commands.py src/warpline/cli.py src/warpline/mcp.py tests/test_commands.py tests/test_mcp.py
git commit -m "feat: expose changed and timeline through cli and mcp"
```

**Definition of Done:**
- [ ] `changed` and `timeline` are available through CLI and MCP.
- [ ] MCP `tools/list` is tested.
- [ ] CLI and MCP call the same command functions.

---

### Task 5: Add Hook Install and Fail-Soft Commit Ingest

**Files:**
- Create: `src/warpline/install.py`
- Modify: `src/warpline/cli.py`
- Modify: `src/warpline/git.py`
- Create: `tests/test_hooks.py`

**Step 1: Write the failing tests**

```python
# tests/test_hooks.py
from __future__ import annotations

from pathlib import Path

import pytest

from warpline.install import hook_body, install_hook


def test_hook_body_exits_zero_and_invokes_ingest() -> None:
    body = hook_body("/usr/bin/warpline")
    assert "warpline ingest-commit HEAD" in body
    assert "exit 0" in body


def test_install_hook_writes_post_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
    install_hook(repo, executable="warpline")
    hook = hooks / "post-commit"
    assert hook.exists()
    assert "warpline ingest-commit HEAD" in hook.read_text(encoding="utf-8")


def test_install_hook_refuses_to_clobber_unmanaged_hook(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "post-commit"
    hook.write_text("#!/bin/sh\necho existing\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        install_hook(repo, executable="warpline")
```

**Why this test:** FR-06 and CON-ORG-04 depend on a hook that never blocks a commit.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_hooks.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.install'
```

**Step 3: Implement fail-soft hook installer**

```python
# src/warpline/install.py
from __future__ import annotations

from pathlib import Path


def hook_body(executable: str) -> str:
    return f"""#!/bin/sh
# BEGIN WARPLINE MANAGED BLOCK
# Managed by Warpline. Fail-soft by design: Warpline must never block commits.
{executable} ingest-commit HEAD >/dev/null 2>&1 || true
# END WARPLINE MANAGED BLOCK
exit 0
"""


def install_hook(repo: Path, executable: str = "warpline") -> Path:
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    if hook.exists():
        existing = hook.read_text(encoding="utf-8")
        if "BEGIN WARPLINE MANAGED BLOCK" not in existing:
            raise FileExistsError(f"refusing to overwrite unmanaged hook: {hook}")
    hook.write_text(hook_body(executable), encoding="utf-8")
    hook.chmod(0o755)
    return hook
```

Add these tests to `tests/test_hooks.py` before implementation:

```python
def test_ingest_commit_returns_zero_on_internal_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from warpline import cli

    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "ingest_commit", fail)
    assert cli.main(["ingest-commit", "HEAD", "--repo", str(tmp_path)]) == 0
```

Add the missing import in that test file:

```python
import pytest
```

Add a single-commit ingest function to `src/warpline/git.py`:

```python
def ingest_commit(store: WarplineStore, repo: Path, sha: str) -> dict[str, Any]:
    repo_id = store.ensure_repo(repo)
    resolved = _git(repo, ["rev-parse", sha]).strip()
    meta = _commit_meta(repo, resolved)
    store.upsert_commit(repo_id, meta)
    changed = 0
    for status, path in _name_status(repo, resolved):
        contents = _file_at_commit(repo, resolved, path) if status[0] != "D" else None
        locators = python_entity_locators(path, contents) if contents is not None else [f"file:{path}"]
        for locator in locators:
            key_id = store.ensure_entity_key(repo_id, locator=locator, sei=None, commit_sha=resolved)
            store.append_change_event(
                repo_id=repo_id,
                entity_key_id=key_id,
                commit_sha=resolved,
                path=path,
                change_kind=_change_kind(status),
                actor=meta["author"],
                changed_at=meta["authored_at"],
            )
            changed += 1
    return {"commit": resolved, "changes": changed}
```

Add a health-log method to `src/warpline/store.py`:

```python
    def log_health(self, repo: Path, code: str, message: str) -> None:
        repo_id = self.ensure_repo(repo)
        self.conn.execute(
            "INSERT INTO health_log(repo_id, code, message) VALUES (?, ?, ?)",
            (repo_id, code, message),
        )
        self.conn.commit()
```

Replace `src/warpline/cli.py` with this command parser in the same task:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from warpline import __version__
from warpline.git import backfill, ingest_commit
from warpline.install import install_hook
from warpline.store import WarplineStore, default_store_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="warpline")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init")
    init.add_argument("--repo", type=Path, default=Path("."))

    backfill_parser = sub.add_parser("backfill")
    backfill_parser.add_argument("--repo", type=Path, default=Path("."))
    backfill_parser.add_argument("--json", action="store_true")

    ingest = sub.add_parser("ingest-commit")
    ingest.add_argument("sha")
    ingest.add_argument("--repo", type=Path, default=Path("."))

    changed_parser = sub.add_parser("changed")
    changed_parser.add_argument("--repo", type=Path, default=Path("."))
    changed_parser.add_argument("--rev-range")
    changed_parser.add_argument("--json", action="store_true")

    timeline_parser = sub.add_parser("timeline")
    timeline_parser.add_argument("--repo", type=Path, default=Path("."))
    timeline_parser.add_argument("--entity", required=True)
    timeline_parser.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"warpline {__version__}")
        return 0
    if args.command == "init":
        hook = install_hook(args.repo)
        print(str(hook))
        return 0
    if args.command == "backfill":
        with WarplineStore.open(default_store_path(args.repo)) as store:
            report = backfill(store, args.repo)
        print(json.dumps(report, sort_keys=True) if args.json else report)
        return 0
    if args.command == "ingest-commit":
        try:
            with WarplineStore.open(default_store_path(args.repo)) as store:
                ingest_commit(store, args.repo, args.sha)
        except Exception as exc:  # fail-soft hook contract
            with WarplineStore.open(default_store_path(args.repo)) as store:
                store.log_health(args.repo, "HOOK_INGEST_FAILED", str(exc))
        return 0
    if args.command == "changed":
        payload = commands.changed(args.repo, args.rev_range)
        print(json.dumps(payload, sort_keys=True) if args.json else json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "timeline":
        payload = commands.timeline(args.repo, args.entity)
        print(json.dumps(payload, sort_keys=True) if args.json else json.dumps(payload, indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 0
```

**Why minimal:** The hook can be replaced later, but fail-soft behavior is locked from the first implementation.

**Step 4: Run tests**

Run: `uv run pytest tests/test_hooks.py tests/test_git_backfill.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/install.py src/warpline/cli.py src/warpline/git.py tests/test_hooks.py
git commit -m "feat: add fail-soft post-commit ingest hook"
```

**Definition of Done:**
- [ ] Hook always exits `0`.
- [ ] Hook writes only under the analyzed repo's `.git/hooks`.
- [ ] Warpline durable state still lives outside the working tree.

---

### Task 6: Prove Loomweave Read Path Before Building Snapshot Logic

**Files:**
- Create: `src/warpline/loomweave.py`
- Create: `tests/test_loomweave_probe.py`
- Create: `spike/REPORT.md`

**Step 1: Write the failing tests**

```python
# tests/test_loomweave_probe.py
from __future__ import annotations

from pathlib import Path

from warpline.loomweave import LoomweaveProbe


def test_missing_loomweave_degrades_cleanly(tmp_path: Path) -> None:
    probe = LoomweaveProbe(repo=tmp_path, command="/no/such/loomweave")
    result = probe.probe()
    assert result["status"] == "skipped"
    assert result["reason"] == "command_unavailable"


def test_probe_reports_expected_read_tools(tmp_path: Path) -> None:
    probe = LoomweaveProbe(repo=tmp_path)
    assert {"entity_find", "entity_resolve", "entity_callers_list"} <= probe.expected_tools()
```

**Why this test:** The first live integration step must distinguish "no Loomweave" from "Warpline broken" and must encode the tool names Warpline actually needs.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_loomweave_probe.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.loomweave'
```

**Step 3: Implement the probe**

Implement `src/warpline/loomweave.py` with this probe:

```python
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LoomweaveProbe:
    repo: Path
    command: str = "loomweave"

    def expected_tools(self) -> set[str]:
        return {
            "project_status_get",
            "entity_find",
            "entity_resolve",
            "entity_neighborhood_get",
            "entity_callers_list",
            "entity_source_get",
        }

    def probe(self) -> dict[str, Any]:
        executable = shutil.which(self.command) if "/" not in self.command else self.command
        if executable is None or not Path(executable).exists():
            return {"status": "skipped", "reason": "command_unavailable"}
        db_path = self.repo / ".weft" / "loomweave" / "loomweave.db"
        if not db_path.exists():
            return {"status": "skipped", "reason": "no_index"}
        version = subprocess.run(
            [executable, "--version"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        proc = subprocess.run(
            [executable, "serve", "--path", str(self.repo)],
            input=json.dumps(request) + "\n",
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return {
                "status": "skipped",
                "reason": "serve_failed",
                "detail": proc.stderr[-1000:],
                "version": version,
            }
        response = json.loads(proc.stdout.splitlines()[-1])
        tools = [tool["name"] for tool in response["result"]["tools"]]
        missing = sorted(self.expected_tools() - set(tools))
        if missing:
            return {
                "status": "skipped",
                "reason": "missing_tools",
                "missing": missing,
                "version": version,
            }
        return {"status": "available", "version": version, "tools": tools}
```

It must return one of:

- `{"status": "available", "version": "...", "tools": [...]}`
- `{"status": "skipped", "reason": "command_unavailable"}`
- `{"status": "skipped", "reason": "no_index"}`
- `{"status": "skipped", "reason": "serve_failed", "detail": "..."}`
- `{"status": "skipped", "reason": "missing_tools", "missing": [...]}`

Do not attempt to patch Loomweave if the probe fails. Append the outcome to `spike/REPORT.md`.

**Why minimal:** This task answers spike Q1's first half without writing any graph data.

**Step 4: Run test and a live probe**

Run: `uv run pytest tests/test_loomweave_probe.py -v`

Expected output:

```text
passed
```

Run: `uv run warpline loomweave-probe --repo <loomweave-root> --json`

Expected output shape:

```json
{"status":"available","tools":["entity_find","entity_callers_list"]}
```

`status: "skipped"` is acceptable only if the reason is explicit and recorded in `spike/REPORT.md`.

**Step 5: Commit**

```bash
git add src/warpline/loomweave.py tests/test_loomweave_probe.py spike/REPORT.md
git commit -m "feat: probe loomweave read surface"
```

**Definition of Done:**
- [ ] Probe distinguishes absent command, missing index, and serve failure.
- [ ] Probe names the exact Loomweave tools Warpline depends on.
- [ ] No sibling repo changed.

---

### Task 7: Store Dated Edge Snapshots With Mandatory Completeness

**Files:**
- Modify: `src/warpline/store.py`
- Create: `src/warpline/snapshot.py`
- Create: `tests/test_snapshots.py`

**Step 1: Write the failing tests**

```python
# tests/test_snapshots.py
from __future__ import annotations

from pathlib import Path

from warpline.snapshot import record_skipped_snapshot
from warpline.store import WarplineStore


def test_skipped_snapshot_is_queryable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        record_skipped_snapshot(store, repo_id, "abc123", reason="no_index")
        snap = store.latest_snapshot(repo)

    assert snap["completeness"] == "SKIPPED"
    assert snap["source"] == "loomweave"
    assert snap["source_version"] == "no_index"
```

**Why this test:** NFR-06 requires thin answers to look thin; even a skipped snapshot is durable evidence.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_snapshots.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.snapshot'
```

**Step 3: Implement snapshot recording**

```python
# src/warpline/snapshot.py
from __future__ import annotations

from warpline.store import WarplineStore


def record_skipped_snapshot(
    store: WarplineStore,
    repo_id: str,
    commit_sha: str,
    reason: str,
) -> int:
    return store.create_edge_snapshot(
        repo_id=repo_id,
        commit_sha=commit_sha,
        source="loomweave",
        source_version=reason,
        completeness="SKIPPED",
    )
```

Add these methods to `src/warpline/store.py`:

```python
    def create_edge_snapshot(
        self,
        repo_id: str,
        commit_sha: str,
        source: str,
        source_version: str,
        completeness: str,
    ) -> int:
        if completeness not in {"FULL", "DELTA", "SKIPPED"}:
            raise ValueError(f"invalid snapshot completeness: {completeness}")
        cur = self.conn.execute(
            """
            INSERT INTO edge_snapshots(repo_id, commit_sha, source, source_version, completeness)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, commit_sha, source) DO UPDATE SET
              source_version = excluded.source_version,
              completeness = excluded.completeness,
              captured_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (repo_id, commit_sha, source, source_version, completeness),
        )
        row = cur.fetchone()
        self.conn.commit()
        if row is None:
            raise RuntimeError("failed to create edge snapshot")
        return int(row["id"])

    def append_snapshot_edge(
        self,
        snapshot_id: int,
        *,
        source_entity_key_id: int,
        target_entity_key_id: int,
        edge_kind: str,
        confidence: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO snapshot_edges(
              snapshot_id, source_entity_key_id, target_entity_key_id, edge_kind, confidence
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (snapshot_id, source_entity_key_id, target_entity_key_id, edge_kind, confidence),
        )
        self.conn.commit()

    def latest_snapshot(self, repo: Path) -> dict[str, object] | None:
        repo_id = self._repo_id(repo)
        row = self.conn.execute(
            """
            SELECT id, commit_sha, source, source_version, captured_at, completeness
              FROM edge_snapshots
             WHERE repo_id = ?
             ORDER BY id DESC
             LIMIT 1
            """,
            (repo_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def snapshot_edges(self, snapshot_id: int) -> list[dict[str, object]]:
        rows = self.conn.execute(
            """
            SELECT source_entity_key_id, target_entity_key_id, edge_kind, confidence
              FROM snapshot_edges
             WHERE snapshot_id = ?
            """,
            (snapshot_id,),
        ).fetchall()
        return [dict(row) for row in rows]
```

**Why minimal:** This locks the honesty path before adding successful edge import.

**Step 4: Run tests**

Run: `uv run pytest tests/test_snapshots.py tests/test_store.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/store.py src/warpline/snapshot.py tests/test_snapshots.py
git commit -m "feat: record dated edge snapshot state"
```

**Definition of Done:**
- [ ] Skipped snapshots are persisted.
- [ ] Snapshot completeness is mandatory.
- [ ] No query can silently act as if skipped edges are complete.

---

### Task 8: Implement Loomweave Edge Snapshot Adapter

**Files:**
- Modify: `src/warpline/loomweave.py`
- Modify: `src/warpline/snapshot.py`
- Create: `tests/test_loomweave_snapshot_adapter.py`

**Step 1: Write the failing adapter tests**

Use a fake Loomweave response shape, not a live process, for unit tests. Add the optional live test shown below in the same task so availability skips are explicit in the executable test suite.

```python
# tests/test_loomweave_snapshot_adapter.py
from __future__ import annotations

from warpline.snapshot import edges_from_neighborhood


def test_edges_from_neighborhood_reads_callers_and_callees() -> None:
    neighborhood = {
        "entity": {"id": "python:function:pkg.target", "sei": "loomweave:eid:t"},
        "callers": [{"id": "python:function:pkg.caller", "sei": "loomweave:eid:c"}],
        "callees": [{"id": "python:function:pkg.child", "sei": "loomweave:eid:x"}],
        "truncated": {"callers": False, "callees": False},
    }
    edges = edges_from_neighborhood(neighborhood)
    assert ("python:function:pkg.caller", "python:function:pkg.target", "calls") in edges
    assert ("python:function:pkg.target", "python:function:pkg.child", "calls") in edges
```

**Why this test:** The adapter must preserve direction because blast radius depends on downstream traversal semantics.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_loomweave_snapshot_adapter.py -v`

Expected output:

```text
ImportError: cannot import name 'edges_from_neighborhood'
```

**Step 3: Implement adapter**

Add this pure parser to `src/warpline/snapshot.py`:

```python
from typing import Any


def _entity_id(row: dict[str, Any]) -> str | None:
    raw = row.get("id") or row.get("entity", {}).get("id")
    return raw if isinstance(raw, str) and raw else None


def edges_from_neighborhood(neighborhood: dict[str, Any]) -> set[tuple[str, str, str]]:
    center = _entity_id(neighborhood.get("entity", {}))
    if center is None:
        raise ValueError("neighborhood missing entity.id")
    if any(neighborhood.get("truncated", {}).get(bucket) is True for bucket in ("callers", "callees")):
        raise ValueError("truncated neighborhood cannot be snapshotted as complete")
    edges: set[tuple[str, str, str]] = set()
    for caller in neighborhood.get("callers", []):
        caller_id = _entity_id(caller)
        if caller_id:
            edges.add((caller_id, center, "calls"))
    for callee in neighborhood.get("callees", []):
        callee_id = _entity_id(callee)
        if callee_id:
            edges.add((center, callee_id, "calls"))
    for ref_in in neighborhood.get("references_in", []):
        ref_id = _entity_id(ref_in)
        if ref_id:
            edges.add((ref_id, center, "references"))
    for ref_out in neighborhood.get("references_out", []):
        ref_id = _entity_id(ref_out)
        if ref_id:
            edges.add((center, ref_id, "references"))
    return edges
```

Add this MCP client wrapper to `src/warpline/loomweave.py`:

```python
class LoomweaveMcpClient:
    def __init__(self, repo: Path, command: str = "loomweave") -> None:
        self.repo = repo
        self.command = command

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        proc = subprocess.run(
            [self.command, "serve", "--path", str(self.repo)],
            input=json.dumps(request) + "\n",
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-1000:])
        envelope = json.loads(proc.stdout.splitlines()[-1])
        if "error" in envelope:
            raise RuntimeError(str(envelope["error"]))
        text = envelope["result"]["content"][0]["text"]
        return json.loads(text)

    def neighborhood(self, entity: str) -> dict[str, Any]:
        return self.call_tool("entity_neighborhood_get", {"id": entity, "limit": 100})
```

If the live surface cannot enumerate all entities safely, record `SKIPPED(insufficient_export_surface)` and document that in `spike/REPORT.md`; do not invent an unsupported API. The adapter accepts locator ids and SEIs because Loomweave tests show id-taking tools accept SEI and resolve to the same entity.

Add this optional live test:

```python
# tests/integration/test_loomweave_live.py
from __future__ import annotations

from pathlib import Path

import pytest

from warpline.loomweave import LoomweaveProbe


def test_live_loomweave_probe_reports_surface() -> None:
    repo = Path("<loomweave-root>")
    result = LoomweaveProbe(repo=repo).probe()
    if result["status"] == "skipped":
        pytest.skip(f"loomweave unavailable for live probe: {result}")
    assert "entity_neighborhood_get" in result["tools"]
```

**Why minimal:** Warpline only needs dated edge snapshots. It must not read or expose "current structure" as its own answer.

**Step 4: Run unit and optional live tests**

Run: `uv run pytest tests/test_loomweave_snapshot_adapter.py -v`

Expected output:

```text
passed
```

Run: `uv run pytest tests/integration/test_loomweave_live.py -v`

Expected output:

```text
skipped: loomweave index unavailable
```

or:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/loomweave.py src/warpline/snapshot.py tests/test_loomweave_snapshot_adapter.py tests/integration/test_loomweave_live.py spike/REPORT.md
git commit -m "feat: snapshot loomweave graph edges when available"
```

**Definition of Done:**
- [ ] Adapter is source-grounded in Loomweave's live tool names.
- [ ] Adapter records `SKIPPED` instead of guessing.
- [ ] Snapshot rows include staleness and completeness.
- [ ] No query answers "who calls X right now" from Warpline.

---

### Task 8A: Resolve SEI Opaquely When Loomweave Can Provide It

**Files:**
- Modify: `src/warpline/loomweave.py`
- Modify: `src/warpline/store.py`
- Create: `tests/test_sei_resolution.py`

**Step 1: Write failing SEI tests**

```python
# tests/test_sei_resolution.py
from __future__ import annotations

from pathlib import Path

from warpline.loomweave import resolve_sei_for_locator
from warpline.store import WarplineStore


class FakeClient:
    def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        assert name == "entity_resolve"
        assert arguments == {"id": "python:function:pkg.mod::fn"}
        return {"entity": {"id": "python:function:pkg.mod::fn", "sei": "loomweave:eid:opaque-value"}}


def test_resolve_sei_for_locator_returns_opaque_value() -> None:
    assert resolve_sei_for_locator(FakeClient(), "python:function:pkg.mod::fn") == "loomweave:eid:opaque-value"


def test_resolve_sei_for_locator_degrades_when_absent() -> None:
    class MissingClient:
        def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
            return {"entity": {"id": "python:function:pkg.mod::fn"}}

    assert resolve_sei_for_locator(MissingClient(), "python:function:pkg.mod::fn") is None


def test_store_persists_sei_without_parsing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        key_id = store.ensure_entity_key(
            repo_id,
            locator="python:function:pkg.mod::fn",
            sei="loomweave:eid:opaque-value",
            commit_sha="c1",
        )
        events = store.list_entity_keys(repo)
    assert events[0]["id"] == key_id
    assert events[0]["sei"] == "loomweave:eid:opaque-value"
```

**Why this test:** FR-01 and FR-07 require SEI when resolvable, while Weft requires consumers to treat SEIs as opaque and Loomweave-owned.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sei_resolution.py -v`

Expected output:

```text
ImportError: cannot import name 'resolve_sei_for_locator'
```

**Step 3: Implement opaque SEI resolution**

Add this helper to `src/warpline/loomweave.py`:

```python
from typing import Protocol


class ToolClient(Protocol):
    def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        ...


def resolve_sei_for_locator(client: ToolClient, locator: str) -> str | None:
    try:
        payload = client.call_tool("entity_resolve", {"id": locator})
    except Exception:
        return None
    entity = payload.get("entity") if isinstance(payload, dict) else None
    if not isinstance(entity, dict):
        return None
    sei = entity.get("sei")
    return sei if isinstance(sei, str) and sei else None
```

Add a query helper to `src/warpline/store.py`:

```python
    def list_entity_keys(self, repo: Path) -> list[dict[str, object]]:
        repo_id = self._repo_id(repo)
        rows = self.conn.execute(
            """
            SELECT id, locator, sei, first_seen_commit, last_seen_commit
              FROM entity_keys
             WHERE repo_id = ?
             ORDER BY id
            """,
            (repo_id,),
        ).fetchall()
        return [dict(row) for row in rows]
```

When backfill or snapshot import can create a `LoomweaveMcpClient`, attempt `resolve_sei_for_locator()` for each locator and pass the returned opaque string into `ensure_entity_key()`. If the call fails, pass `None` and set enrichment state to `{"sei": "absent"}`; do not parse, mint, normalize, or validate SEI strings inside Warpline.

**Step 4: Run tests**

Run: `uv run pytest tests/test_sei_resolution.py tests/test_git_backfill.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/loomweave.py src/warpline/store.py tests/test_sei_resolution.py
git commit -m "feat: resolve loomweave sei opaquely"
```

**Definition of Done:**
- [ ] Warpline stores SEIs only when Loomweave resolves them.
- [ ] Warpline treats SEI strings as opaque.
- [ ] Capability absence degrades to `sei: absent`.
- [ ] No Warpline code mints `loomweave:eid:*`.

---

### Task 9: Implement Blast Radius Traversal

**Files:**
- Create: `src/warpline/propagation.py`
- Modify: `src/warpline/commands.py`
- Modify: `src/warpline/mcp.py`
- Create: `tests/test_propagation.py`

**Step 1: Write the failing tests**

```python
# tests/test_propagation.py
from __future__ import annotations

import subprocess
from pathlib import Path

from warpline.propagation import blast_radius
from warpline.store import WarplineStore


def test_blast_radius_returns_no_snapshot_honestly(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        key = store.ensure_entity_key(repo_id, locator="file:a.py", sei=None, commit_sha="c1")
        result = blast_radius(store, repo, [key], depth=2)
    assert result["completeness"] == "NO_SNAPSHOT"
    assert result["affected"] == []


def test_blast_radius_walks_downstream(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(repo_id, locator="python:function:a", sei=None, commit_sha="c1")
        b = store.ensure_entity_key(repo_id, locator="python:function:b", sei=None, commit_sha="c1")
        snap = store.create_edge_snapshot(repo_id, "c1", "loomweave", "test", "FULL")
        store.append_snapshot_edge(snap, source_entity_key_id=a, target_entity_key_id=b, edge_kind="calls", confidence="resolved")
        result = blast_radius(store, repo, [a], depth=2)
    assert result["completeness"] == "FULL"
    assert result["affected"][0]["entity_key_id"] == b
    assert result["affected"][0]["depth"] == 1


def test_blast_radius_reports_snapshot_staleness(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=repo, check=True)
    (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "one"], cwd=repo, check=True)
    first = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    (repo / "a.py").write_text("a = 2\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "two"], cwd=repo, check=True)

    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        key = store.ensure_entity_key(repo_id, locator="file:a.py", sei=None, commit_sha=first)
        store.create_edge_snapshot(repo_id, first, "loomweave", "test", "FULL")
        result = blast_radius(store, repo, [key], depth=2)
    assert result["staleness"]["snapshot_commit"] == first
    assert result["staleness"]["commits_behind"] == 1
```

**Why this test:** It pins the dangerous case: no snapshot is not a crash and not a fake green answer.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_propagation.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.propagation'
```

**Step 3: Implement traversal**

Use an in-memory adjacency list from the latest snapshot and keep a strict `depth <= 5` input guard. Add `src/warpline/propagation.py`:

```python
from __future__ import annotations

from collections import deque
import subprocess
from pathlib import Path
from typing import Any

from warpline.store import WarplineStore


def _commits_behind(repo: Path, snapshot_commit: str) -> int | None:
    proc = subprocess.run(
        ["git", "rev-list", "--count", f"{snapshot_commit}..HEAD"],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return None


def blast_radius(
    store: WarplineStore,
    repo: Path,
    changed_entity_key_ids: list[int],
    depth: int,
) -> dict[str, Any]:
    if depth < 0 or depth > 5:
        raise ValueError("depth must be between 0 and 5")
    snapshot = store.latest_snapshot(repo)
    changed = [{"entity_key_id": key_id} for key_id in changed_entity_key_ids]
    if snapshot is None or snapshot["completeness"] == "SKIPPED":
        return {
            "changed": changed,
            "affected": [],
            "staleness": {"snapshot_commit": None, "commits_behind": None},
            "completeness": "NO_SNAPSHOT",
        }

    adjacency: dict[int, list[dict[str, Any]]] = {}
    for edge in store.snapshot_edges(int(snapshot["id"])):
        source = int(edge["source_entity_key_id"])
        adjacency.setdefault(source, []).append(edge)

    seen = set(changed_entity_key_ids)
    affected: list[dict[str, Any]] = []
    queue: deque[tuple[int, int, list[dict[str, Any]]]] = deque(
        (key_id, 0, []) for key_id in changed_entity_key_ids
    )
    while queue:
        current, current_depth, path = queue.popleft()
        if current_depth >= depth:
            continue
        for edge in adjacency.get(current, []):
            target = int(edge["target_entity_key_id"])
            if target in seen:
                continue
            seen.add(target)
            edge_view = {
                "from": current,
                "to": target,
                "kind": edge["edge_kind"],
                "confidence": edge["confidence"],
            }
            via_edges = [*path, edge_view]
            affected.append(
                {"entity_key_id": target, "depth": current_depth + 1, "via_edges": via_edges}
            )
            queue.append((target, current_depth + 1, via_edges))

    return {
        "changed": changed,
        "affected": affected,
        "staleness": {
            "snapshot_commit": snapshot["commit_sha"],
            "commits_behind": _commits_behind(repo, str(snapshot["commit_sha"])),
        },
        "completeness": snapshot["completeness"],
    }
```

Add the command wrapper to `src/warpline/commands.py`:

```python
from warpline.propagation import blast_radius as compute_blast_radius


def blast_radius(repo: Path, changed_entity_key_ids: list[int], depth: int = 2) -> dict[str, Any]:
    with WarplineStore.open(default_store_path(repo)) as store:
        return {
            "warpline_schema_version": store.schema_version(),
            "query": "blast_radius",
            **compute_blast_radius(store, repo, changed_entity_key_ids, depth),
        }
```

Extend `src/warpline/mcp.py` in the same task by adding this tool definition:

```python
{
    "name": "blast_radius",
    "description": "Return downstream affected entities from stored dated snapshots. Read-only.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "changed_entity_key_ids": {"type": "array", "items": {"type": "integer"}},
            "depth": {"type": "integer", "minimum": 0, "maximum": 5},
        },
        "required": ["repo", "changed_entity_key_ids"],
        "additionalProperties": False,
    },
}
```

And add this dispatch branch:

```python
    if name == "blast_radius":
        return _tool_result(
            id_value,
            commands.blast_radius(
                Path(args["repo"]),
                [int(value) for value in args["changed_entity_key_ids"]],
                int(args.get("depth", 2)),
            ),
        )
```

Response shape:

```json
{
  "changed": [{"entity_key_id": 1}],
  "affected": [{"entity_key_id": 2, "depth": 1, "via_edges": [{"from": 1, "to": 2, "kind": "calls"}]}],
  "staleness": {"snapshot_commit": "c1", "commits_behind": null},
  "completeness": "FULL"
}
```

**Why minimal:** The in-memory implementation is easier to validate against planted corpora. Recursive SQL is intentionally deferred until NFR-01 measurements show the in-memory slice is too slow.

**Step 4: Run tests**

Run: `uv run pytest tests/test_propagation.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/propagation.py src/warpline/commands.py src/warpline/mcp.py tests/test_propagation.py
git commit -m "feat: compute honest blast radius from edge snapshots"
```

**Definition of Done:**
- [ ] `NO_SNAPSHOT` is a normal result shape.
- [ ] Depth is bounded.
- [ ] MCP exposes `blast_radius`.
- [ ] Every blast-radius result includes `staleness` and `completeness`.

---

### Task 10: Implement Agent-Consumable Reverify Worklist

**Files:**
- Create: `src/warpline/reverify.py`
- Modify: `src/warpline/commands.py`
- Modify: `src/warpline/cli.py`
- Modify: `src/warpline/mcp.py`
- Create: `tests/test_reverify.py`

**Step 1: Write the failing tests**

```python
# tests/test_reverify.py
from __future__ import annotations

from warpline.reverify import render_reverify_worklist


def test_reverify_worklist_is_machine_first() -> None:
    blast = {
        "changed": [{"locator": "python:function:a"}],
        "affected": [{"locator": "python:function:b", "depth": 1, "via_edges": [{"from": "a", "to": "b", "kind": "calls"}]}],
        "staleness": {"snapshot_commit": "c1", "commits_behind": null},
        "completeness": "FULL",
    }
    out = render_reverify_worklist(blast)
    assert out["format"] == "warpline.reverify.v1"
    assert out["items"][0]["entity"]["locator"] == "python:function:b"
    assert out["items"][0]["why"][0]["kind"] == "calls"
```

**Why this test:** The primary output is what an agent acts on, not prose.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_reverify.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.reverify'
```

**Step 3: Implement worklist renderer**

```python
# src/warpline/reverify.py
from __future__ import annotations

from typing import Any


def render_reverify_worklist(blast_radius: dict[str, Any]) -> dict[str, Any]:
    items = []
    for affected in blast_radius.get("affected", []):
        locator = affected.get("locator") or str(affected.get("entity_key_id"))
        items.append(
            {
                "entity": {"locator": locator},
                "reason": "downstream of changed entity",
                "depth": affected["depth"],
                "why": affected.get("via_edges", []),
                "suggested_verification": [
                    {"kind": "test", "command": "run tests touching this entity if known"},
                    {"kind": "inspection", "command": "inspect callers and behavior at this boundary"},
                ],
            }
        )
    return {
        "format": "warpline.reverify.v1",
        "completeness": blast_radius["completeness"],
        "staleness": blast_radius["staleness"],
        "items": items,
    }
```

Add the command wrapper to `src/warpline/commands.py`:

```python
from warpline.reverify import render_reverify_worklist


def reverify(repo: Path, changed_entity_key_ids: list[int], depth: int = 2) -> dict[str, Any]:
    result = blast_radius(repo, changed_entity_key_ids, depth)
    return {
        "warpline_schema_version": result["warpline_schema_version"],
        "query": "reverify",
        **render_reverify_worklist(result),
    }
```

Extend `src/warpline/mcp.py` with this tool definition:

```python
{
    "name": "reverify",
    "description": "Render an agent-first re-verification worklist from blast-radius output.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "changed_entity_key_ids": {"type": "array", "items": {"type": "integer"}},
            "depth": {"type": "integer", "minimum": 0, "maximum": 5},
        },
        "required": ["repo", "changed_entity_key_ids"],
        "additionalProperties": False,
    },
}
```

And add this dispatch branch:

```python
    if name == "reverify":
        return _tool_result(
            id_value,
            commands.reverify(
                Path(args["repo"]),
                [int(value) for value in args["changed_entity_key_ids"]],
                int(args.get("depth", 2)),
            ),
        )
```

**Why minimal:** Test discovery is intentionally generic until Warpline has enough repository evidence to infer exact commands safely.

**Step 4: Run tests**

Run: `uv run pytest tests/test_reverify.py tests/test_mcp.py -v`

Expected output:

```text
passed
```

**Step 5: Commit**

```bash
git add src/warpline/reverify.py src/warpline/commands.py src/warpline/cli.py src/warpline/mcp.py tests/test_reverify.py
git commit -m "feat: render agent-first reverify worklists"
```

**Definition of Done:**
- [ ] MCP exposes `reverify`.
- [ ] JSON worklist is primary; Markdown rendering is optional.
- [ ] Worklist carries staleness and completeness.

---

### Task 11: Add Sibling Boundary and No-Member-Diff Gates

**Files:**
- Create: `tests/test_sibling_boundaries.py`
- Create: `scripts/check_no_member_diffs.sh`
- Modify: `pyproject.toml`

**Step 1: Write the failing tests**

```python
# tests/test_sibling_boundaries.py
from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_IMPORT_ROOTS = {"filigree", "wardline", "legis", "loomweave", "charter"}


def test_warpline_does_not_import_sibling_packages() -> None:
    for path in Path("src/warpline").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            assert not (names & FORBIDDEN_IMPORT_ROOTS), f"{path} imports {names & FORBIDDEN_IMPORT_ROOTS}"
```

**Why this test:** Enrich-only composition is easier to preserve when Warpline uses process/API/file surfaces instead of importing sibling internals.

**Step 2: Run test to verify it fails if forbidden imports exist**

Run: `uv run pytest tests/test_sibling_boundaries.py -v`

Expected output:

```text
passed
```

Add a script-content test in the same file:

```python
def test_no_member_diff_script_covers_all_members() -> None:
    text = Path("scripts/check_no_member_diffs.sh").read_text(encoding="utf-8")
    for repo in ("<filigree-root>", "<wardline-root>", "<legis-root>", "<loomweave-root>", "<charter-root>"):
        assert repo in text
    assert "member-dirty-baseline.txt" in text
```

**Step 3: Add member diff check**

```bash
#!/usr/bin/env bash
set -euo pipefail

baseline="docs/evidence/member-dirty-baseline.txt"
current="$(mktemp)"
trap 'rm -f "$current"' EXIT

for repo in <filigree-root> <wardline-root> <legis-root> <loomweave-root> <charter-root>; do
  printf '## %s\n' "$repo" >>"$current"
  if [ -d "$repo/.git" ]; then
    git -C "$repo" status --short >>"$current"
  fi
done

if ! diff -u "$baseline" "$current"; then
  printf 'Member repo dirty state differs from recorded baseline. Stop and record or resolve the difference explicitly.\n' >&2
  exit 1
fi
```

**Why minimal:** This is a mechanical guard for CON-TEC-02.

**Step 4: Run gates**

Run: `uv run pytest tests/test_sibling_boundaries.py -v`

Expected output:

```text
passed
```

Run: `bash scripts/check_no_member_diffs.sh`

Expected output:

```text
```

No output and exit code `0`.

**Step 5: Commit**

```bash
git add tests/test_sibling_boundaries.py scripts/check_no_member_diffs.sh pyproject.toml
git commit -m "test: guard warpline sibling boundaries"
```

**Definition of Done:**
- [ ] Warpline imports no sibling Python packages.
- [ ] CI can fail if member repos drift from the recorded pre-existing dirty baseline.
- [ ] All integration is through published executable/read surfaces.

---

### Task 12: Build Spike Harness and Report

**Files:**
- Create: `tests/spike/test_harness.py`
- Create: `scripts/run_spike.sh`
- Create: `spike/measurements.json`
- Modify: `spike/REPORT.md`

**Step 1: Write the failing harness tests**

```python
# tests/spike/test_harness.py
from __future__ import annotations

from pathlib import Path

from warpline.reverify import render_reverify_worklist


def test_spike_report_has_recommendation_line() -> None:
    report = Path("spike/REPORT.md")
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "Recommendation:" in text
    assert any(word in text for word in ["go", "no-go", "park-until-cutover"])


def test_spike_measurements_cover_required_nfrs() -> None:
    measurements = Path("spike/measurements.json")
    assert measurements.exists()
    text = measurements.read_text(encoding="utf-8")
    for key in (
        "changed_latency_ms",
        "backfill_events_per_second",
        "hook_ingest_exit_code",
        "planted_recall",
        "snapshot_completeness",
    ):
        assert key in text


def test_reverify_worklist_carries_honesty_fields() -> None:
    worklist = render_reverify_worklist(
        {
            "changed": [],
            "affected": [],
            "staleness": {"snapshot_commit": None, "commits_behind": None},
            "completeness": "NO_SNAPSHOT",
        }
    )
    assert worklist["completeness"] == "NO_SNAPSHOT"
    assert "staleness" in worklist
```

**Why this test:** The spike report is a deliverable, not after-the-fact narration.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/spike/test_harness.py -v`

Expected output:

```text
FAILED test_spike_report_has_recommendation_line
```

**Step 3: Implement `scripts/run_spike.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

repos=(
  <warpline-root>
  <filigree-root>
  <wardline-root>
  <legis-root>
  <loomweave-root>
)

tmp_repo="$(mktemp -d)"
trap 'rm -rf "$tmp_repo"' EXIT
git -C "$tmp_repo" init
git -C "$tmp_repo" config user.email agent@example.test
git -C "$tmp_repo" config user.name Agent
printf 'def planted():\n    return 1\n' >"$tmp_repo/planted.py"
git -C "$tmp_repo" add planted.py
git -C "$tmp_repo" commit -m 'planted initial'
printf 'def planted():\n    return 2\n' >"$tmp_repo/planted.py"
git -C "$tmp_repo" commit -am 'planted change'

uv run warpline loomweave-probe --repo <loomweave-root> --json

for repo in "${repos[@]}"; do
  uv run warpline backfill --repo "$repo" --json
  uv run warpline changed --repo "$repo" --json >/tmp/warpline-changed.json
done

start_ns="$(date +%s%N)"
uv run warpline backfill --repo "$tmp_repo" --json >/tmp/warpline-backfill.json
backfill_ns="$(( $(date +%s%N) - start_ns ))"

start_ns="$(date +%s%N)"
uv run warpline changed --repo "$tmp_repo" --rev-range HEAD~1..HEAD --json >/tmp/warpline-planted-changed.json
changed_ns="$(( $(date +%s%N) - start_ns ))"

hook_exit=0
uv run warpline ingest-commit HEAD --repo "$tmp_repo" >/tmp/warpline-hook-ingest.json || hook_exit="$?"
planted_hits="$(python - <<'PY'
import json
payload = json.load(open('/tmp/warpline-planted-changed.json'))
print(sum(1 for row in payload.get('changed', []) if row.get('path') == 'planted.py'))
PY
)"
mkdir -p spike
python - <<PY
import json
backfill_ns = int("$backfill_ns")
changed_ns = int("$changed_ns")
planted_hits = int("$planted_hits")
payload = {
    "changed_latency_ms": changed_ns / 1_000_000,
    "backfill_events_per_second": None if backfill_ns == 0 else 2 / (backfill_ns / 1_000_000_000),
    "hook_ingest_exit_code": int("$hook_exit"),
    "planted_recall": 1.0 if planted_hits > 0 else 0.0,
    "snapshot_completeness": "measured-by-reverify-output-or-NO_SNAPSHOT",
}
open("spike/measurements.json", "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY

uv run pytest tests -v
```

Update `spike/REPORT.md` with:

- Q1 acquisition evidence and actual Loomweave surface used.
- Q2 snapshot honesty and planted-change results.
- NFR measurement summary copied from `spike/measurements.json`: changed-query latency, backfill throughput, hook exit code, planted-change recall, and snapshot completeness/staleness.
- Q3 doctrine firewall checklist.
- Q4 grep-test dogfood notes.
- Recommendation: `go`, `no-go`, or `park-until-cutover`.

**Why minimal:** The script is intentionally a harness, not a hidden deployment system.

**Step 4: Run harness**

Run: `bash scripts/run_spike.sh`

Expected output:

```text
passed
```

If a live sibling tool is unavailable, record the skipped reason in `spike/REPORT.md` and keep unit tests passing.

**Step 5: Commit**

```bash
git add scripts/run_spike.sh tests/spike/test_harness.py spike/REPORT.md
git commit -m "test: add warpline spike harness and report gate"
```

**Definition of Done:**
- [ ] `spike/REPORT.md` exists.
- [ ] Report has one recommendation line.
- [ ] Harness measures changed-query latency, backfill throughput, hook exit behavior, planted-change recall, and snapshot completeness/staleness.
- [ ] No member repo is modified.

---

### Task 13: Add Full Requirement Fitness Gate

**Files:**
- Create: `tests/test_requirements_traceability.py`
- Modify: `docs/plans/2026-06-12-warpline-delivery.md` if traceability gaps are found

**Step 1: Write the failing test**

```python
# tests/test_requirements_traceability.py
from __future__ import annotations

from pathlib import Path


REQUIREMENTS = [
    "FR-01", "FR-02", "FR-03", "FR-04", "FR-05", "FR-06", "FR-07", "FR-08",
    "NFR-01", "NFR-02", "NFR-03", "NFR-04", "NFR-05", "NFR-06",
    "CON-TEC-01", "CON-TEC-02", "CON-TEC-03",
    "CON-ORG-01", "CON-ORG-02", "CON-ORG-03", "CON-ORG-04",
]


def test_delivery_plan_traces_every_requirement_to_task_and_verification() -> None:
    text = Path("docs/plans/2026-06-12-warpline-delivery.md").read_text(encoding="utf-8")
    missing: list[str] = []
    weak: list[str] = []
    for req in REQUIREMENTS:
        rows = [line for line in text.splitlines() if line.startswith(f"| {req} ")]
        if not rows:
            missing.append(req)
            continue
        row = rows[0]
        if "Task" not in row or not any(token in row for token in ("tests/", "scripts/", "pytest", "bash ")):
            weak.append(req)
    assert missing == []
    assert weak == []
```

**Why this test:** It prevents the delivery plan from satisfying only the obvious feature requirements while missing constraints, and it forces each row to point at an implementation task plus executable evidence.

**Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_requirements_traceability.py -v`

Expected output:

```text
passed
```

**Step 3: If it fails, update the plan and affected task**

Do not weaken the test; fix missing requirement coverage in the plan or implementation.

**Step 4: Commit**

```bash
git add tests/test_requirements_traceability.py docs/plans/2026-06-12-warpline-delivery.md
git commit -m "test: require warpline delivery traceability"
```

**Definition of Done:**
- [ ] Every FR/NFR/CON appears in the Requirements Fitness Review table.
- [ ] Every row points at a task and executable verification.
- [ ] Missing coverage is treated as a plan bug.

---

### Task 14: Add Productization Gate From Spike Findings

**Files:**
- Create: `src/warpline/productization.py`
- Create: `tests/test_productization_gate.py`
- Modify: `src/warpline/cli.py`

**Step 1: Write the failing tests**

```python
# tests/test_productization_gate.py
from __future__ import annotations

from pathlib import Path

from warpline.productization import ProductizationDecision, read_productization_decision


def test_productization_gate_blocks_without_report(tmp_path: Path) -> None:
    decision = read_productization_decision(tmp_path / "missing.md")
    assert decision == ProductizationDecision(
        allowed=False,
        recommendation="missing",
        reason="spike report not found",
    )


def test_productization_gate_allows_go_recommendation(tmp_path: Path) -> None:
    report = tmp_path / "REPORT.md"
    report.write_text(
        "# Warpline Spike Report\n\nRecommendation: go\n\nOwner admission: pending\n",
        encoding="utf-8",
    )
    decision = read_productization_decision(report)
    assert decision.allowed is True
    assert decision.recommendation == "go"


def test_productization_gate_blocks_no_go(tmp_path: Path) -> None:
    report = tmp_path / "REPORT.md"
    report.write_text("Recommendation: no-go\n", encoding="utf-8")
    decision = read_productization_decision(report)
    assert decision.allowed is False
    assert decision.recommendation == "no-go"
```

**Why this test:** The updated objective says to take the spike findings into a product. This pins the rule that productization consumes recorded findings instead of assuming the spike passed.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_productization_gate.py -v`

Expected output:

```text
ModuleNotFoundError: No module named 'warpline.productization'
```

**Step 3: Write minimal implementation**

```python
# src/warpline/productization.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductizationDecision:
    allowed: bool
    recommendation: str
    reason: str


def read_productization_decision(report_path: Path = Path("spike/REPORT.md")) -> ProductizationDecision:
    if not report_path.exists():
        return ProductizationDecision(False, "missing", "spike report not found")
    text = report_path.read_text(encoding="utf-8")
    recommendation = _recommendation(text)
    if recommendation == "go":
        return ProductizationDecision(True, recommendation, "spike recommendation is go")
    if recommendation in {"no-go", "park-until-cutover"}:
        return ProductizationDecision(False, recommendation, f"spike recommendation is {recommendation}")
    return ProductizationDecision(False, "unknown", "spike report has no recognized recommendation")


def _recommendation(text: str) -> str:
    for line in text.splitlines():
        normalized = line.strip().lower()
        if normalized.startswith("recommendation:"):
            value = normalized.split(":", 1)[1].strip()
            for candidate in ("park-until-cutover", "no-go", "go"):
                if value.startswith(candidate):
                    return candidate
    return "unknown"
```

Add a CLI command in `src/warpline/cli.py`:

```python
import json
from pathlib import Path

from warpline.productization import read_productization_decision


def _add_productization_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("productization-gate")
    parser.add_argument("--report", default="spike/REPORT.md")
    parser.set_defaults(func=_productization_gate)


def _productization_gate(args: argparse.Namespace) -> int:
    decision = read_productization_decision(Path(args.report))
    payload = {
        "allowed": decision.allowed,
        "recommendation": decision.recommendation,
        "reason": decision.reason,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if decision.allowed else 2
```

Register the parser beside the other subcommands.

**Why minimal:** This is a product-release guard only. It does not decide owner admission and it does not inspect sibling repos.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_productization_gate.py -v`

Expected output:

```text
3 passed
```

**Step 5: Commit**

```bash
git add src/warpline/productization.py src/warpline/cli.py tests/test_productization_gate.py
git commit -m "feat: gate warpline productization on spike findings"
```

**Definition of Done:**
- [ ] Missing report blocks productization.
- [ ] `Recommendation: go` allows productization.
- [ ] `no-go` and `park-until-cutover` block productization.
- [ ] CLI exposes a machine-readable gate for release scripts.

---

### Task 15: Publish Warpline-Owned Federation Contracts

**Precondition:** Run `uv run warpline productization-gate --report spike/REPORT.md` and stop if it exits non-zero. These fixtures are Warpline-owned draft fixtures only; they are not normative Weft federation contracts until owner admission and glossary clearance.

**Files:**
- Create: `docs/federation/contracts.md`
- Create: `tests/fixtures/contracts/warpline/mcp-tool-inventory.json`
- Create: `tests/fixtures/contracts/warpline/mcp-response-changed.json`
- Create: `tests/fixtures/contracts/warpline/mcp-response-reverify.json`
- Create: `tests/contracts/test_warpline_contract_fixtures.py`

**Step 1: Write the failing contract-fixture tests**

```python
# tests/contracts/test_warpline_contract_fixtures.py
from __future__ import annotations

import json
from pathlib import Path


FIXTURES = Path("tests/fixtures/contracts/warpline")


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_mcp_tool_inventory_is_agent_first_and_enrich_only() -> None:
    fixture = load("mcp-tool-inventory.json")
    assert fixture["schema"] == "warpline.draft.mcp_tool_inventory.v1"
    assert fixture["status"] == "pre-admission-draft"
    names = [tool["name"] for tool in fixture["tools"]]
    assert names == sorted(names)
    assert {"changed", "timeline", "blast_radius", "reverify"} <= set(names)
    for tool in fixture["tools"]:
        assert tool["mutates"] is False
        assert tool["local_only"] is True
        assert tool["peer_side_effects"] == []
        assert tool["authority_boundary"]


def test_changed_response_fixture_carries_enrichment_state() -> None:
    fixture = load("mcp-response-changed.json")
    assert fixture["schema"] == "warpline.draft.changed.v1"
    assert fixture["ok"] is True
    assert "changed" in fixture["data"]
    assert fixture["data"]["enrichment"]["sei"] in {"present", "absent"}
    assert fixture["data"]["enrichment"]["edges"] in {"present", "absent", "stale"}


def test_reverify_response_fixture_carries_honesty_fields() -> None:
    fixture = load("mcp-response-reverify.json")
    data = fixture["data"]
    assert fixture["schema"] == "warpline.draft.reverify.v1"
    assert data["completeness"] in {"FULL", "DELTA", "NO_SNAPSHOT", "SKIPPED"}
    assert "staleness" in data
    assert "worklist" in data
```

**Why this test:** A product entering the federation needs Warpline-owned fixtures for Warpline-owned surfaces; sibling repos should not reverse-engineer Warpline's wire shape from code.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/contracts/test_warpline_contract_fixtures.py -v`

Expected output:

```text
FileNotFoundError: tests/fixtures/contracts/warpline/mcp-tool-inventory.json
```

**Step 3: Add contract documentation and fixtures**

```markdown
# Warpline Federation Contracts

Status: pre-admission draft, Warpline-owned, productization gated by `spike/REPORT.md`.
These fixtures are non-normative until owner admission and glossary clearance.

Warpline exposes read-only, local-first CLI and MCP surfaces over its temporal store.
It owns temporal change facts and dated edge snapshots. It does not own current
structure, requirements, work state, trust policy, or governance.

## MCP tools

- `changed` — changed entities for a rev/range/diff.
- `timeline` — ordered change events for an entity.
- `blast_radius` — downstream affected set over dated snapshots.
- `reverify` — agent-consumable re-verification worklist.

All tools are read-only and local-only. Sibling absence returns explicit
enrichment/completeness fields, not transport failure.
```

```json
{
  "schema": "warpline.draft.mcp_tool_inventory.v1",
  "status": "pre-admission-draft",
  "tools": [
    {
      "name": "blast_radius",
      "mutates": false,
      "local_only": true,
      "peer_side_effects": [],
      "authority_boundary": "Traverses Warpline's dated snapshots; does not answer current graph truth."
    },
    {
      "name": "changed",
      "mutates": false,
      "local_only": true,
      "peer_side_effects": [],
      "authority_boundary": "Returns temporal change facts from git/Warpline store."
    },
    {
      "name": "reverify",
      "mutates": false,
      "local_only": true,
      "peer_side_effects": [],
      "authority_boundary": "Returns reverify worklists; does not file work or govern changes."
    },
    {
      "name": "timeline",
      "mutates": false,
      "local_only": true,
      "peer_side_effects": [],
      "authority_boundary": "Returns per-entity change timeline; does not resolve current structure."
    }
  ]
}
```

```json
{
  "schema": "warpline.draft.changed.v1",
  "ok": true,
  "data": {
    "repo": "example",
    "rev_range": "HEAD~1..HEAD",
    "changed": [
      {
        "entity_key": {"locator": "src/pkg/mod.py::fn", "sei": null},
        "change_kind": "modified",
        "actor": "agent:codex",
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "at": "2026-06-13T00:00:00Z"
      }
    ],
    "enrichment": {"sei": "absent", "edges": "absent"}
  },
  "warnings": [],
  "meta": {"producer": {"tool": "warpline", "version": "0.1.0"}}
}
```

```json
{
  "schema": "warpline.draft.reverify.v1",
  "ok": true,
  "data": {
    "repo": "example",
    "rev_range": "HEAD~1..HEAD",
    "completeness": "NO_SNAPSHOT",
    "staleness": {"snapshot_commit": null, "commits_behind": null},
    "worklist": [
      {
        "entity_key": {"locator": "src/pkg/mod.py::fn", "sei": null},
        "reason": "changed in rev_range",
        "suggested_verification": [{"kind": "test", "command": "run tests touching this entity if known"}]
      }
    ],
    "enrichment": {"sei": "absent", "edges": "absent"}
  },
  "warnings": ["NO_SNAPSHOT: downstream traversal unavailable; changed set only"],
  "meta": {"producer": {"tool": "warpline", "version": "0.1.0"}}
}
```

**Why minimal:** These fixtures cover Warpline-owned read surfaces only. Post-admission sibling consumers pin against these fixtures and Warpline code, not against copied schema prose.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/contracts/test_warpline_contract_fixtures.py -v`

Expected output:

```text
3 passed
```

**Step 5: Commit**

```bash
git add docs/federation/contracts.md tests/fixtures/contracts/warpline tests/contracts/test_warpline_contract_fixtures.py
git commit -m "docs: publish warpline federation contracts"
```

**Definition of Done:**
- [ ] Warpline-owned contract docs exist.
- [ ] MCP fixture inventory is read-only, local-only, and explicit about authority.
- [ ] Response fixtures carry enrichment and honesty fields.
- [ ] No sibling-owned contract is copied or frozen in Warpline.

---

### Task 16: Prepare Post-Admission Consumer Ticket Package

**Precondition:** Run `uv run warpline productization-gate --report spike/REPORT.md` and stop if it exits non-zero. This task writes only Warpline-owned ticket-package documentation; it does not patch sibling repos.

**Files:**
- Create: `docs/integration/post-admission-consumer-tickets.md`
- Create: `tests/test_consumer_ticket_package.py`

**Step 1: Write the failing tests**

```python
# tests/test_consumer_ticket_package.py
from __future__ import annotations

from pathlib import Path


CONSUMERS = ["Loomweave", "Charter", "Legis", "Wardline", "Filigree"]


def test_consumer_ticket_package_exists_for_every_pairwise_story() -> None:
    text = Path("docs/integration/post-admission-consumer-tickets.md").read_text(encoding="utf-8")
    for consumer in CONSUMERS:
        assert f"## {consumer}" in text
    assert "owner admission" in text
    assert "Do not patch sibling repos from Warpline delivery work" in text


def test_consumer_ticket_package_keeps_authorities_separate() -> None:
    text = Path("docs/integration/post-admission-consumer-tickets.md").read_text(encoding="utf-8")
    assert "Loomweave owns current structure" in text
    assert "Charter owns obligations" in text
    assert "Legis owns governance" in text
    assert "Wardline owns trust policy" in text
    assert "Filigree owns work state" in text
```

**Why this test:** Product integration into the federation must become sibling-owned work after owner admission, not hidden patches bundled into Warpline.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_consumer_ticket_package.py -v`

Expected output:

```text
FileNotFoundError: docs/integration/post-admission-consumer-tickets.md
```

**Step 3: Write the consumer ticket package**

```markdown
# Warpline Post-Admission Consumer Tickets

Status: draft ticket package. Use only after `spike/REPORT.md` recommends `go`
and owner admission is explicit. Do not patch sibling repos from Warpline delivery
work.

## Loomweave
- Goal: consume Warpline temporal history to implement or redirect `entity_high_churn_list` and `entity_recent_change_list`.
- Boundary: Loomweave owns current structure and SEI. Warpline supplies temporal history only.
- Acceptance: Loomweave still answers current graph queries from Loomweave storage; Warpline absence disables only churn/recency enrichment.

## Charter
- Goal: consume Warpline reverify/affected-set facts when Charter impact analysis lands.
- Boundary: Charter owns obligations, baselines, verification evidence, and requirement impact. Warpline supplies structural/temporal affected entities.
- Acceptance: Charter impact reports still run from local trace links when Warpline is absent.

## Legis
- Goal: optionally include Warpline affected-set facts in governance/preflight context.
- Boundary: Legis owns governance, sign-offs, CI/check context, and attestations. Warpline does not allow/block changes.
- Acceptance: Legis can surface Warpline context as advisory facts without changing policy decisions when Warpline is absent.

## Wardline
- Goal: optionally scope rescans to Warpline's affected set.
- Boundary: Wardline owns trust policy, findings, baselines, waivers, judge labels, and attestations.
- Acceptance: Wardline full scan remains available and authoritative; scoped scan output says when scope came from Warpline and what completeness/staleness applied.

## Filigree
- Goal: optionally file or link Warpline reverify worklists as work items after explicit user/tool action.
- Boundary: Filigree owns work state, issue lifecycle, claims, and close gates.
- Acceptance: Warpline never auto-files by default; generated work carries `scan_source`/producer identity and affected entity keys.
```

**Why minimal:** This is a handoff package for sibling trackers. It does not implement sibling consumers.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_consumer_ticket_package.py -v`

Expected output:

```text
2 passed
```

**Step 5: Commit**

```bash
git add docs/integration/post-admission-consumer-tickets.md tests/test_consumer_ticket_package.py
git commit -m "docs: prepare warpline post-admission consumer tickets"
```

**Definition of Done:**
- [ ] Every pairwise consumer has a ticket stub.
- [ ] Ticket package requires owner admission.
- [ ] Authority boundaries are explicit.
- [ ] No sibling patch is part of Warpline's delivery.

---

### Task 17: Add Product Release Candidate Gate

**Files:**
- Create: `scripts/check_release_candidate.sh`
- Create: `tests/test_release_candidate_gate.py`

**Step 1: Write the failing tests**

```python
# tests/test_release_candidate_gate.py
from __future__ import annotations

from pathlib import Path


def test_release_candidate_script_runs_required_gates() -> None:
    script = Path("scripts/check_release_candidate.sh")
    assert script.exists()
    text = script.read_text(encoding="utf-8")
    required = [
        "warpline productization-gate",
        "ruff check",
        "mypy src/warpline",
        "pytest tests",
        "check_no_member_diffs.sh",
        "run_spike.sh",
    ]
    for item in required:
        assert item in text
    assert text.index("run_spike.sh") < text.index("warpline productization-gate")
    assert text.count("git diff --quiet") >= 2
```

**Why this test:** The plan needs one operator command that proves Warpline is ready to be treated as a product candidate, not just a pile of passing unit tests.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_release_candidate_gate.py -v`

Expected output:

```text
FileNotFoundError: scripts/check_release_candidate.sh
```

**Step 3: Write the release candidate gate**

```bash
#!/usr/bin/env bash
set -euo pipefail

git diff --quiet
git diff --cached --quiet
bash scripts/check_no_member_diffs.sh
bash scripts/run_spike.sh
uv run warpline productization-gate --report spike/REPORT.md
uv run ruff check .
uv run mypy src/warpline
uv run pytest tests -v
git diff --quiet
git diff --cached --quiet
```

Mark executable:

```bash
chmod +x scripts/check_release_candidate.sh
```

**Why minimal:** The script aggregates existing gates and refuses productization when the spike evidence is absent or negative.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_release_candidate_gate.py -v`

Expected output:

```text
1 passed
```

**Step 5: Commit**

```bash
git add scripts/check_release_candidate.sh tests/test_release_candidate_gate.py
git commit -m "test: add warpline product release candidate gate"
```

**Definition of Done:**
- [ ] One script runs productization, lint, type, unit, member-diff, and spike gates.
- [ ] Script fails when `spike/REPORT.md` is absent or non-go.
- [ ] Script leaves sibling repos untouched.

---

## Requirement Fitness Review

| Requirement | Plan Coverage | Verification |
|---|---|---|
| FR-01 changed-set | Tasks 3, 4 | `tests/test_git_backfill.py`, `tests/test_commands.py`, `tests/test_mcp.py` |
| FR-02 timeline | Task 4 | `tests/test_commands.py`, MCP `timeline` |
| FR-03 blast radius | Tasks 7, 8, 9 | `tests/test_snapshots.py`, `tests/test_propagation.py` |
| FR-04 reverify worklist | Task 10 | `tests/test_reverify.py`, MCP `reverify` |
| FR-05 backfill | Task 3 | `tests/test_git_backfill.py`, `scripts/run_spike.sh` |
| FR-06 hook-fed ingest | Task 5 | `tests/test_hooks.py` |
| FR-07 solo mode | Tasks 3, 6, 7, 9 | `tests/test_loomweave_probe.py`, `tests/test_propagation.py` |
| FR-08 CLI + MCP | Tasks 1, 4, 9, 10 | `tests/test_mcp.py`, `tests/test_commands.py` |
| Source-grounded sibling/Weft facts | Task 0 | `docs/evidence/2026-06-13-source-grounding.md`, `tests/test_source_grounding.py` |
| NFR-01 latency | Tasks 9, 12 | `scripts/run_spike.sh`, `spike/measurements.json` |
| NFR-02 ingest cost | Tasks 3, 5, 12 | `scripts/run_spike.sh`, `spike/measurements.json` |
| NFR-03 local-first | Tasks 1-5, 11 | `tests/test_store.py`, `tests/test_sibling_boundaries.py` |
| NFR-04 enrich-only | Tasks 6, 11 | `tests/test_loomweave_probe.py`, `tests/test_sibling_boundaries.py` |
| NFR-05 cleanliness | Tasks 2, 5, 11, 17 | `tests/test_store.py`, `scripts/check_no_member_diffs.sh`, `scripts/check_release_candidate.sh` |
| NFR-06 false negatives | Tasks 7, 9, 12 | `tests/test_snapshots.py`, `tests/test_propagation.py`, `scripts/run_spike.sh` |
| CON-TEC-01 SEI frozen | Tasks 6, 8, 8A, 11 | `tests/test_sei_resolution.py`, `tests/test_sibling_boundaries.py` |
| CON-TEC-02 no member changes | Tasks 6, 11, 12 | `scripts/check_no_member_diffs.sh`, `tests/test_sibling_boundaries.py` |
| CON-TEC-03 local-first | Tasks 1-5, 11 | `tests/test_store.py`, `tests/test_sibling_boundaries.py` |
| CON-ORG-01 aggregator firewall | Tasks 2, 7, 9, 11 | `tests/test_store.py`, `tests/test_snapshots.py`, `tests/test_propagation.py` |
| CON-ORG-02 owner admission | Tasks 12, 14, 16 | `tests/test_productization_gate.py`, `tests/test_consumer_ticket_package.py` |
| CON-ORG-03 naming placeholder | Tasks 12, 15 | `tests/contracts/test_warpline_contract_fixtures.py`, `scripts/run_spike.sh` |
| CON-ORG-04 hook-fed | Task 5 | `tests/test_hooks.py` |
| Productization from spike findings | Task 14 | `warpline productization-gate`, `tests/test_productization_gate.py` |
| Federation contract preparation | Task 15 | Warpline-owned fixtures and `tests/contracts/test_warpline_contract_fixtures.py` |
| Post-admission integration package | Task 16 | Consumer ticket package with authority boundaries |

## Final Verification Commands

Run before claiming the plan implemented:

```bash
uv run ruff check .
uv run mypy src/warpline
uv run pytest tests -v
bash scripts/check_no_member_diffs.sh
bash scripts/run_spike.sh
git diff --quiet
git diff --cached --quiet
```

Expected final state:

```text
ruff: clean
mypy: Success: no issues found
pytest: all unit tests passed; live sibling tests passed or skipped with explicit reason
member diff check: no output, exit 0
git diff checks: clean after commits
```

## Delivery Notes

- Do not add a dashboard, daemon, cloud sync, or member-side consumer wiring in this delivery slice.
- Do not make Loomweave required for basic changed-set and timeline operation.
- Do not use Warpline to answer current structure. Route current graph questions to Loomweave.
- If an agent finds the flow annoying, fix the flow. Friction in `warpline changed`, `warpline reverify`, MCP `tools/list`, or first-run setup is a product defect, not a documentation issue.
