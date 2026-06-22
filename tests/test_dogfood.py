from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import git as _git
from conftest import init_repo as _init_repo

from warpline import cli
from warpline.dogfood import _select_real_member_rev_range, run_dogfood_evaluator
from warpline.git import backfill
from warpline.store import WarplineStore, default_store_path


def _commit_file(repo: Path, path: str, body: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def test_dogfood_evaluator_writes_required_machine_readable_contract(
    tmp_path: Path,
) -> None:
    output = tmp_path / "dogfood.json"
    result = run_dogfood_evaluator(
        output_path=output,
        work_dir=tmp_path / "work",
        real_member_repo=None,
        require_real_member=False,
    )

    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == result
    assert payload["schema"] == "warpline.dogfood_results.v1"
    assert payload["thresholds"] == {
        "synthetic_solo_parity": 8,
        "synthetic_federation_uplift": 8,
        "real_member_parity": 1,
        "real_loomweave_uplift": 1,
        "real_baseline_executed": 1,
    }
    assert payload["summary"]["solo"]["parity"] == 0
    assert payload["summary"]["federation"]["uplift"] >= 8
    assert payload["summary"]["real_member"]["cases"] == 0
    assert payload["ready"] is False
    assert len(payload["cases"]) == 20
    for case in payload["cases"]:
        assert {
            "case_id",
            "lane",
            "tool_calls",
            "baseline_answer",
            "warpline_answer",
            "parity",
            "uplift",
            "failure_reason",
            "manual_escape_required",
            "enrichment_state",
        } <= set(case)
        assert case["tool_calls"] <= 2
        assert case["manual_escape_required"] is False


def test_cli_dogfood_eval_writes_output(tmp_path: Path) -> None:
    output = tmp_path / "dogfood.json"
    assert (
        cli.main(
            [
                "dogfood-eval",
                "--output",
                str(output),
                "--work-dir",
                str(tmp_path / "work"),
                "--skip-real-member",
                "--json",
            ]
        )
        == 2
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ready"] is False


def test_real_member_selector_skips_commits_without_executable_baseline(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    _commit_file(repo, "README.md", "# demo\n", "initial")
    code_sha = _commit_file(repo, "src/tool.py", "def target():\n    return 1\n", "code")
    _commit_file(repo, "site/package.json", "{}\n", "package metadata")

    with WarplineStore.open(default_store_path(repo)) as store:
        backfill(store, repo)

    rev_range, _selected = _select_real_member_rev_range(repo)

    assert rev_range == f"{code_sha}^..{code_sha}"


def test_cli_dogfood_eval_accepts_custom_real_member_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_run_dogfood_evaluator(**kwargs: object) -> dict[str, object]:
        seen.update(kwargs)
        return {"ready": True}

    repo = tmp_path / "member"
    repo.mkdir()
    output = tmp_path / "dogfood.json"
    monkeypatch.setattr(cli, "run_dogfood_evaluator", fake_run_dogfood_evaluator)

    assert (
        cli.main(
            [
                "dogfood-eval",
                "--output",
                str(output),
                "--work-dir",
                str(tmp_path / "work"),
                "--real-member-repo",
                str(repo),
                "--json",
            ]
        )
        == 0
    )
    assert seen["real_member_repo"] == repo
    assert seen["require_real_member"] is True
