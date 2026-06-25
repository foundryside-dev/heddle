from __future__ import annotations

import subprocess
from pathlib import Path

from warpline.git import commits_between, is_ancestor, resolve_commit


def _run(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()


def _repo_with_three_commits(tmp_path: Path) -> tuple[Path, list[str]]:
    repo = tmp_path / "r"
    repo.mkdir()
    _run(repo, "init", "-q")
    _run(repo, "config", "user.email", "t@t")
    _run(repo, "config", "user.name", "t")
    shas: list[str] = []
    for i in range(3):
        (repo / "f.txt").write_text(f"v{i}\n")
        _run(repo, "add", ".")
        _run(repo, "commit", "-q", "-m", f"c{i}")
        shas.append(_run(repo, "rev-parse", "HEAD"))
    return repo, shas


def test_resolve_commit_resolves_head_to_object_sha(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    resolved = resolve_commit(repo, "HEAD")
    assert resolved == shas[2]
    assert len(resolved) == 40


def test_resolve_commit_returns_none_for_bad_ref(tmp_path: Path) -> None:
    repo, _ = _repo_with_three_commits(tmp_path)
    assert resolve_commit(repo, "no-such-ref") is None


def test_is_ancestor_true_for_earlier_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, shas[0], shas[2]) is True


def test_is_ancestor_true_for_equal_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, shas[1], shas[1]) is True


def test_is_ancestor_false_for_later_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, shas[2], shas[0]) is False


def test_is_ancestor_none_for_unknown_commit(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert is_ancestor(repo, "f" * 40, shas[0]) is None


def test_commits_between_counts_distance(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert commits_between(repo, shas[0], shas[2]) == 2


def test_commits_between_zero_for_same(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert commits_between(repo, shas[1], shas[1]) == 0


def test_commits_between_none_for_unknown(tmp_path: Path) -> None:
    repo, shas = _repo_with_three_commits(tmp_path)
    assert commits_between(repo, "f" * 40, shas[0]) is None
