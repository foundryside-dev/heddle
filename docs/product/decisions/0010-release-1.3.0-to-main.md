# PDR-0010 - Release warpline 1.3.0 to main (owner-directed)

Date: 2026-07-01
Status: accepted
Owner sign-off: the RELEASE — merge to `main`, annotated tag, **push to origin** — was
**owner-directed this session** ("please merge the 1.3.0 release to main and then tag it
for release"; "please push to remote and get 1.3.0 out the door"). The outward-facing act
is therefore sanctioned, not an open escalation, mirroring PDR-0006's 1.2.0 release. The
`uv tool install` (live MCP binary) and the heddle-shadow retirement are repo-local /
environment-local.
Supersedes: none
Related: PDR-0005/0007 (verification-freshness), PDR-0008 (requirements consumer),
PDR-0009 (Phase-2 hardening); `CHANGELOG.md` [1.3.0]; merge commit `3768794`; tag `v1.3.0`.

## Context

"Cut + release the `release/1.2.0` stack" was the standing **Now** bet and the open owner
escalation across the last several checkpoints — the version cut (1.3.0 vs 1.2.x) plus the
public-release-status change. This session the owner directed the release.

## The call

Cut the `release/1.2.0` stack as **v1.3.0** (minor — new capability; the frozen
`warpline.<contract>.v1` data contracts are unchanged) and ship it to `main` + origin:

- **Bump** 1.2.0 → 1.3.0 (`pyproject.toml` + `CHANGELOG.md` `[1.3.0] - 2026-07-01` +
  `uv.lock`), commit `8e5eeea`. `__version__` is single-sourced from package metadata, so
  `--version` and every envelope `producer.version` follow automatically.
- **Merge** `release/1.2.0` → `main` (`3768794`), reconciling the `beea0f8` divergence
  (a swarm session had forward-ported project_status + v4 straight to `main`). All conflicts
  resolved in favor of `release/1.2.0`, the canonical superset that already contained that
  capability; verified **`git diff release/1.2.0 main` == empty** pre- and post-commit, so
  `main` holds exactly the release content and nothing divergent survived.
- **Gate** green on merged `main`: ruff + `mypy src/warpline` clean; pytest 572 passed / 1 skipped.
- **Tag** annotated `v1.3.0` on the merge commit; **pushed** `main` + tag to origin
  (`d693812..3768794`, `[new tag] v1.3.0`; clean fast-forward, tachyon-beep identity).
- **Install**: `uv tool install --force .` → the live `.mcp.json` binary
  (`~/.local/bin/warpline` + `warpline-mcp`) is **1.3.0**; retired the stale
  `heddle`-venv editable install so bare `warpline` on PATH is 1.3.0 too (no shadow).

**1.3.0 content:** verify-record + verification-freshness (PDR-0005/0007); the four-member
federation seam — filigree (work), wardline (risk / attest-2), legis (`governance_read.v1`),
plainweave (`requirements_enrichment.v1`) — (PDR-0008); the `project_status` store-binding
probe; and the arch-analysis Phase-2 reliability hardening U1/U2/U3/U4/U8 (PDR-0009).

## Rationale

The stack was already accepted capability (PDR-0007/0008/0009), gate-green, with the frozen
data contracts untouched — a clean **minor**. Shipping it retires the long-standing release
escalation and makes the federation enrichment live for consumers. Resolving the `beea0f8`
divergence in favor of the canonical branch (verified by the empty tree-diff) prevented `main`
accreting the release piecemeal.

## Reversal trigger

Reopen if a 1.3.0 consumer hits a **frozen-contract break** the release gate missed, or a
**post-release correctness defect** surfaces in the shipped capability — specifically any
field crash or wrong-answer traced to verification-freshness, a federation consumer, or a
Phase-2 guard (the U1 orphan invariant / U2 identity echo firing on valid input) on a real
repo. Tie to `metrics.md`: a north-star regression (an agent can no longer get a non-empty
federation-enriched reverify) or a guardrail breach after the release.

**Known post-release gap (NOT a reversal trigger):** the `requirements` member reads
`disabled` until the **plainweave producer binary is reshipped** (v1.0.0 → v1.1.0 on PATH;
PDR-0008 watch). The consumer ships correct; the live contract stays dark until that sibling
install — an owner escalation tracked in `current-state.md`.
