from __future__ import annotations

import json
from pathlib import Path

import pytest

from warpline import install_support
from warpline.cli import main


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git" / "hooks").mkdir(parents=True)
    return repo


@pytest.fixture(autouse=True)
def _fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))


def test_install_wires_every_component_and_doctor_is_green(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    report = install_support.run_install(repo)
    assert report.ok, report.errors

    # MCP binding
    mcp = json.loads((repo / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp["mcpServers"]["warpline"]["type"] == "stdio"
    assert mcp["mcpServers"]["warpline"]["command"]

    # skill injection into BOTH skill systems
    assert (repo / ".claude" / "skills" / "warpline-workflow" / "SKILL.md").exists()
    assert (repo / ".agents" / "skills" / "warpline-workflow" / "SKILL.md").exists()

    # config under .weft/warpline
    config = json.loads((repo / ".weft" / "warpline" / "config.json").read_text(encoding="utf-8"))
    assert config == {"prefix": "warpline", "name": "warpline", "version": 1}
    assert (repo / ".weft" / "warpline" / "INSTALL_VERSION").read_text().strip() == "1"

    # git hook
    assert "WARPLINE MANAGED BLOCK" in (repo / ".git" / "hooks" / "post-commit").read_text()

    doctor = install_support.run_doctor(repo)
    assert doctor.ok
    assert all(r.ok for r in doctor.results)


def test_install_preserves_foreign_instruction_blocks(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    (repo).mkdir(parents=True, exist_ok=True)
    foreign = (
        "<!-- filigree:instructions:v3 -->\nfiligree stuff\n<!-- /filigree:instructions -->\n"
    )
    (repo / "CLAUDE.md").write_text(foreign, encoding="utf-8")

    install_support.run_install(repo, {"claude_md"})
    text = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "filigree:instructions" in text  # foreign block untouched
    assert "<!-- warpline:instructions" in text
    assert "<!-- /warpline:instructions -->" in text

    # idempotent: a second pass does not duplicate the warpline block
    install_support.run_install(repo, {"claude_md"})
    text2 = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert text2.count("<!-- /warpline:instructions -->") == 1
    assert text2.count("<!-- /filigree:instructions -->") == 1


def test_doctor_reports_missing_then_fix_repairs(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    install_support.run_install(repo)
    # break one component: remove the skill
    import shutil

    shutil.rmtree(repo / ".claude" / "skills" / "warpline-workflow")
    pre = install_support.run_doctor(repo)
    assert not pre.ok
    assert any(not r.ok and r.name == "Claude Code skills" for r in pre.results)

    fixed = install_support.run_doctor(repo, fix=True)
    assert fixed.ok
    assert any(name == "Claude Code skills" for name, _ in fixed.fixed)
    assert (repo / ".claude" / "skills" / "warpline-workflow" / "SKILL.md").exists()


def test_doctor_flags_non_git_repo_as_unfixable(tmp_path: Path) -> None:
    repo = tmp_path / "plain"
    repo.mkdir()
    report = install_support.run_doctor(repo, fix=True)
    hook = next(r for r in report.results if r.name == "git post-commit hook")
    assert hook.ok is False
    assert hook.fixable is False


def test_codex_mcp_block_is_valid_toml_and_preserves_existing(tmp_path: Path) -> None:
    import tomllib

    config_path = Path.home() / ".codex" / "config.toml"
    config_path.write_text('[existing]\nkeep = true\n', encoding="utf-8")
    repo = _git_repo(tmp_path)
    install_support.run_install(repo, {"codex"})
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert data["existing"]["keep"] is True
    assert data["mcp_servers"]["warpline"]["command"]


def test_cli_install_and_doctor_json_exit_codes(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    assert main(["install", "--repo", str(repo), "--json"]) == 0
    assert main(["doctor", "--repo", str(repo), "--json"]) == 0


def test_cli_session_context_is_fail_soft(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert main(["session-context", "--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "warpline" in out
