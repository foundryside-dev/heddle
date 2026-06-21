from __future__ import annotations

import ast
import os
import subprocess
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
            assert not (names & FORBIDDEN_IMPORT_ROOTS), (
                f"{path} imports {names & FORBIDDEN_IMPORT_ROOTS}"
            )


def test_no_member_diff_script_covers_all_members() -> None:
    text = Path("scripts/check_no_member_diffs.sh").read_text(encoding="utf-8")
    for repo in (
        "/home/john/filigree",
        "/home/john/wardline",
        "/home/john/legis",
        "/home/john/loomweave",
        "/home/john/charter",
    ):
        assert repo in text
    assert "member-dirty-baseline.txt" in text


def test_member_diff_check_is_opt_in_for_release_gates() -> None:
    wrapper = Path("scripts/maybe_check_member_diffs.sh")
    assert wrapper.exists()
    text = wrapper.read_text(encoding="utf-8")
    assert "WARPLINE_CHECK_MEMBER_DIFFS" in text
    assert "check_no_member_diffs.sh" in text


def test_member_diff_wrapper_skips_by_default_and_runs_on_opt_in(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "maybe_check_member_diffs.sh").write_text(
        Path("scripts/maybe_check_member_diffs.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sentinel = tmp_path / "member-diff-ran"
    (scripts / "check_no_member_diffs.sh").write_text(
        f"#!/usr/bin/env bash\nprintf ran > {sentinel}\nexit 42\n",
        encoding="utf-8",
    )

    default = subprocess.run(
        ["bash", "scripts/maybe_check_member_diffs.sh"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert default.returncode == 0
    assert "Skipping sibling dirty-baseline check" in default.stderr
    assert not sentinel.exists()

    opt_in_env = os.environ.copy()
    opt_in_env["WARPLINE_CHECK_MEMBER_DIFFS"] = "1"
    opt_in = subprocess.run(
        ["bash", "scripts/maybe_check_member_diffs.sh"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        env=opt_in_env,
    )
    assert opt_in.returncode == 42
    assert sentinel.read_text(encoding="utf-8") == "ran"
