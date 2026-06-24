from __future__ import annotations

from pathlib import Path

import pytest

from warpline.install import hook_body, install_hook


def test_hook_body_exits_zero_and_invokes_ingest() -> None:
    body = hook_body("/usr/bin/warpline")
    assert "warpline ingest-commit HEAD" in body
    assert "exit 0" in body


def test_hook_body_carries_bounded_reresolve_but_defers_capture() -> None:
    """The post-commit path stays bounded: ingest + a small SEI repair sweep.

    Edge snapshot capture is deferred to reads or explicit capture commands so a
    commit never waits on a full graph capture.
    """

    body = hook_body("/usr/bin/warpline")
    assert "/usr/bin/warpline reresolve-sei --limit 25 >/dev/null 2>&1 || true" in body
    assert "capture-snapshot" not in body
    assert body.index("ingest-commit") < body.index("reresolve-sei")


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


# ---------------------------------------------------------------------------
# Test C — hook body carries an OS-level timeout guard (Part 2 defense-in-depth).
# ---------------------------------------------------------------------------
def test_hook_body_has_os_level_timeout_guard() -> None:
    """hook_body() must wrap each warpline command with a portable `timeout`
    guard: detect the binary with `command -v timeout`, then prefix each
    command invocation with the variable.  The BEGIN/END markers and exit 0
    must still be present.
    """
    body = hook_body("warpline")

    # Portability guard must be present
    assert "command -v timeout" in body

    # Both commands must be prefixed with the timeout variable
    assert "$_wl_timeout warpline ingest-commit HEAD" in body
    assert "$_wl_timeout warpline reresolve-sei --limit 25" in body

    # Structural invariants must be preserved
    assert "# BEGIN WARPLINE MANAGED BLOCK" in body
    assert "# END WARPLINE MANAGED BLOCK" in body
    assert "exit 0" in body
