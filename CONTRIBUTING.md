# Contributing to warpline

Thank you for considering a contribution to warpline. Bug reports, feature ideas,
documentation fixes, and code changes are all welcome.

Before you start, one thing is specific to warpline and worth stating up front:
**warpline implements to a frozen cross-member contract.** The MCP tool names, their
input/output schemas, the success/error envelope, and the `error_code` /
`enrichment` / `retryability` vocabularies are all frozen at the federation's
clean-break launch and owned by the Weft hub, not by this repository. Changing any
of them is a hub decision — escalate with evidence rather than diverging. A `v2`
is a new schema URI, never a mutation of `v1`. Internal changes that keep every
contract intact are ordinary contributions.

## How to report bugs

Open a bug report on GitHub. Include:

- warpline version (`warpline --version`)
- Whether you hit the issue via the CLI or the MCP server
- Steps to reproduce
- Expected vs. actual behavior (quote the JSON envelope where relevant)
- Python version and OS

## How to suggest features

Open a feature request describing the problem you are solving and your proposed
approach. If the feature touches a frozen contract surface, say so — it will need a
hub-level decision.

## Development setup

warpline is a zero-dependency package; the dev tooling is managed by
[uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/foundryside-dev/warpline.git
cd warpline
uv sync --group dev
```

## Code style

- **Linter/formatter**: [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`)
- **Type checker**: mypy in strict mode
- **Line length**: 100 characters
- **Python**: 3.12+

Before committing:

```bash
uv run ruff check src tests     # lint
uv run mypy                      # strict type-check
uv run pytest                    # full test suite
```

These are exactly what CI runs (lint, typecheck, and tests on Python 3.12 and
3.13). Live federation tests against loomweave self-skip when the sibling is
absent.

## Verifying the contract is intact

Because warpline implements to a frozen contract, two extra checks matter for any
change near the tool surface:

```bash
uv run pytest tests/contracts/test_golden_vectors.py   # the 14 golden vectors
uv run warpline mcp-smoke --repo . --json               # live stdio MCP smoke
```

The golden vectors (with `tests/fixtures/contracts/warpline/golden-vectors.json` as
the conformance manifest) are the executable definition of the frozen behavior. If
a change makes one fail, either the change is wrong or it is a contract change that
belongs at the hub — it is never something to "fix" by editing the vector.

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>: <short description>

<optional body>
```

| Type | When to use |
| --- | --- |
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `ci` | CI/CD pipeline changes |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore` | Maintenance (deps, config, etc.) |
| `build` | Build system or packaging changes |

Use `!` after the type for a breaking change.

## Pull request process

1. Fork the repository and branch from `main`.
2. Make your change.
3. Run `ruff check`, `mypy`, and `pytest` (plus the contract checks above if you
   touched the tool surface) and confirm they pass.
4. Open a pull request against `main`, describing what it does and why, and linking
   any related issue.
5. Keep PRs focused — one logical change per PR.

## Architecture orientation

| Module | Responsibility |
| --- | --- |
| `src/warpline/cli.py` | The `warpline` CLI entry point and argument parsing. |
| `src/warpline/mcp.py` | The MCP stdio server: tool specs, dispatch, the `warpline-mcp` entry point. |
| `src/warpline/commands.py` | The tool implementations and frozen schema URIs. |
| `src/warpline/envelope.py` | The frozen success envelope and closed `enrichment` vocabulary. |
| `src/warpline/errors.py` | The `warpline.error.v1` error vocabulary. |
| `src/warpline/store.py` | The SQLite temporal store. |
| `src/warpline/git.py` | git backfill / single-commit ingest and entity extraction. |
| `src/warpline/loomweave.py` | The loomweave probe and MCP client (SEI resolution, neighborhoods). |
| `src/warpline/snapshot.py`, `propagation.py`, `reverify.py` | Edge capture, blast-radius traversal, worklist rendering. |
| `src/warpline/siblings.py` | The filigree work-state and rename-feed seams. |
| `src/warpline/install_support.py` | The federation `install` / `doctor` lifecycle. |

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
