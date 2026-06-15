from __future__ import annotations

from pathlib import Path

import pytest

from warpline.install import hook_body, install_hook


def test_hook_body_exits_zero_and_invokes_ingest() -> None:
    body = hook_body("/usr/bin/warpline")
    assert "warpline ingest-commit HEAD" in body
    assert "exit 0" in body


def test_hook_body_carries_reresolve_and_capture_lines() -> None:
    """Rung 1d: the managed block runs a bounded reresolve sweep + a HEAD capture
    after ingest, both fail-soft (`|| true`)."""

    body = hook_body("/usr/bin/warpline")
    assert "/usr/bin/warpline reresolve-sei --limit 25 >/dev/null 2>&1 || true" in body
    assert "/usr/bin/warpline capture-snapshot --commit HEAD >/dev/null 2>&1 || true" in body
    # Ordering: ingest first, then heal SEIs, then capture (so capture sees them).
    assert body.index("ingest-commit") < body.index("reresolve-sei") < body.index(
        "capture-snapshot"
    )


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


def test_ingest_commit_returns_zero_on_internal_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from warpline import cli

    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "ingest_commit", fail)
    assert cli.main(["ingest-commit", "HEAD", "--repo", str(tmp_path)]) == 0
