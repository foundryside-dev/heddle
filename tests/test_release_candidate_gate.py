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
        "warpline dogfood-eval",
    ]
    for item in required:
        assert item in text
    assert text.index("run_spike.sh") < text.index("warpline productization-gate")
    assert text.index("warpline dogfood-eval") < text.index("warpline productization-gate")
    assert text.count("git diff --quiet") >= 2
