from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORT_ROOTS = {"filigree", "wardline", "legis", "loomweave", "charter"}


def test_heddle_does_not_import_sibling_packages() -> None:
    for path in Path("src/heddle").rglob("*.py"):
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
