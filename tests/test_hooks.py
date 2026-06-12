from __future__ import annotations

from pathlib import Path

import pytest

from heddle.install import hook_body, install_hook


def test_hook_body_exits_zero_and_invokes_ingest() -> None:
    body = hook_body("/usr/bin/heddle")
    assert "heddle ingest-commit HEAD" in body
    assert "exit 0" in body


def test_install_hook_writes_post_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
    install_hook(repo, executable="heddle")
    hook = hooks / "post-commit"
    assert hook.exists()
    assert "heddle ingest-commit HEAD" in hook.read_text(encoding="utf-8")


def test_install_hook_refuses_to_clobber_unmanaged_hook(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "post-commit"
    hook.write_text("#!/bin/sh\necho existing\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        install_hook(repo, executable="heddle")


def test_ingest_commit_returns_zero_on_internal_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from heddle import cli

    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "ingest_commit", fail)
    assert cli.main(["ingest-commit", "HEAD", "--repo", str(tmp_path)]) == 0
