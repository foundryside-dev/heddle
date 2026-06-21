#!/usr/bin/env bash
set -euo pipefail

git diff --quiet
git diff --cached --quiet
bash scripts/maybe_check_member_diffs.sh
bash scripts/run_spike.sh
uv run warpline dogfood-eval --output /tmp/warpline-dogfood-results.json --json >/tmp/warpline-dogfood-results-run.json
uv run warpline productization-gate --report spike/REPORT.md
uv run ruff check .
uv run mypy src/warpline
uv run pytest tests -v
git diff --quiet
git diff --cached --quiet
