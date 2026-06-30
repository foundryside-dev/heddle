from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from warpline import commands
from warpline.errors import WarplineError
from warpline.store import WarplineStore, default_store_path


def _git_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "r"
    repo.mkdir()
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    (repo / "f.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "c0"], cwd=repo, check=True, capture_output=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()
    return repo, sha


def test_mcp_module_imports() -> None:
    # mcp.py runs assert_inputschema_consumed() + a strict zip at IMPORT time; a
    # missing consume-declaration or handler crashes here. Keep this first so an
    # import crash is distinguishable from a metadata-assertion failure below.
    from warpline import mcp

    assert mcp.TOOL_SPECS


def test_verify_record_stores_resolved_sha(tmp_path: Path) -> None:
    repo, sha = _git_repo(tmp_path)
    env = commands.verify_record(
        repo, commit="HEAD", kind="test_pass", actor="ci", now="2026-06-25T10:00:00+00:00"
    )
    assert env["ok"] is True
    assert env["schema"] == "warpline.verification_record.v1"
    # The SYMBOLIC ref HEAD must be stored as the resolved 40-hex object SHA.
    assert env["data"]["commit_sha"] == sha
    assert env["data"]["kind"] == "test_pass"
    assert env["data"]["actor"] == "ci"
    assert env["data"]["source"] == "warpline"
    with WarplineStore.open(default_store_path(repo)) as store:
        events = store.list_verification_events(repo)
    assert len(events) == 1
    assert events[0]["commit_sha"] == sha


def test_verify_record_envelope_is_local_only(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    env = commands.verify_record(repo, commit="HEAD", kind="test_pass")
    assert env["meta"]["local_only"] is True
    assert env["meta"]["peer_side_effects"] == []


def test_verify_record_is_idempotent(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    commands.verify_record(
        repo, commit="HEAD", kind="test_pass", now="2026-06-25T10:00:00+00:00"
    )
    env2 = commands.verify_record(
        repo, commit="HEAD", kind="test_pass", now="2026-06-25T10:00:00+00:00"
    )
    assert env2["data"]["idempotency"] == "already_recorded"
    with WarplineStore.open(default_store_path(repo)) as store:
        assert len(store.list_verification_events(repo)) == 1


def test_verify_record_idempotent_across_different_timestamps(tmp_path: Path) -> None:
    # verified_at is NOT part of UNIQUE(repo_id, commit_sha, kind, source), so a
    # re-record at a DIFFERENT time must still collapse to a single row.
    repo, _ = _git_repo(tmp_path)
    commands.verify_record(repo, commit="HEAD", kind="test_pass", now="2026-06-25T10:00:00+00:00")
    commands.verify_record(repo, commit="HEAD", kind="test_pass", now="2026-06-25T23:00:00+00:00")
    with WarplineStore.open(default_store_path(repo)) as store:
        assert len(store.list_verification_events(repo)) == 1


def test_verify_record_in_detached_head(tmp_path: Path) -> None:
    # CI commonly runs on a detached HEAD. verify_record(commit="HEAD") must still
    # resolve HEAD to the detached commit's object SHA and store that.
    repo, sha = _git_repo(tmp_path)
    subprocess.run(["git", "checkout", "-q", sha], cwd=repo, check=True, capture_output=True)
    env = commands.verify_record(
        repo, commit="HEAD", kind="ci_pass", now="2026-06-25T10:00:00+00:00"
    )
    assert env["data"]["commit_sha"] == sha


def test_cli_verify_record_bad_commit_does_not_exit_zero(tmp_path: Path) -> None:
    # Mirror tests/test_cli_dispatch.py's invocation style (read it first). A bad
    # --commit must not return success. If cli.main has a top-level WarplineError
    # handler producing an ok:false envelope + nonzero return, assert that;
    # otherwise assert the non-zero/raised outcome the existing verbs produce.
    from warpline import cli

    repo, _ = _git_repo(tmp_path)
    try:
        rc = cli.main(
            ["verify-record", "--repo", str(repo), "--commit", "no-such-ref",
             "--kind", "test_pass", "--json"]
        )
    except Exception:
        return  # surfaced as an exception (traceback) -> not a success path
    assert rc != 0


def test_verify_record_bad_ref_raises_structured_error(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    with pytest.raises(WarplineError) as exc:
        commands.verify_record(repo, commit="no-such-ref", kind="test_pass")
    data = exc.value.to_error_data()
    assert data["error_code"] == "invalid_rev_range"
    assert data["rejected_field"] == "commit"
    # No row written.
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.list_verification_events(repo) == []


def test_verify_record_empty_kind_raises_structured_error(tmp_path: Path) -> None:
    repo, _ = _git_repo(tmp_path)
    with pytest.raises(WarplineError) as exc:
        commands.verify_record(repo, commit="HEAD", kind="   ")
    data = exc.value.to_error_data()
    assert data["error_code"] == "missing_required_field"
    assert data["rejected_field"] == "kind"


def test_verify_record_empty_commit_raises_missing_required_field(tmp_path: Path) -> None:
    # An absent/empty commit must raise MissingRequiredFieldError (missing_required_field),
    # NOT BadRevisionError (invalid_rev_range) — symmetric with the blank-kind guard.
    repo, _ = _git_repo(tmp_path)
    with pytest.raises(WarplineError) as exc:
        commands.verify_record(repo, commit="", kind="test_pass")
    data = exc.value.to_error_data()
    assert data["error_code"] == "missing_required_field"
    assert data["rejected_field"] == "commit"


def test_mcp_verify_record_rejects_non_string_kind_without_writing(tmp_path: Path) -> None:
    from warpline import mcp

    repo, _ = _git_repo(tmp_path)

    response = mcp.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "warpline_verification_record",
                "arguments": {"repo": str(repo), "commit": "HEAD", "kind": None},
            },
        }
    )

    assert response["error"]["code"] == -32602
    data = response["error"]["data"]
    assert data["schema"] == "warpline.error.v1"
    assert data["error_code"] == "missing_required_field"
    assert data["rejected_field"] == "kind"
    with WarplineStore.open(default_store_path(repo)) as store:
        assert store.list_verification_events(repo) == []


def test_mcp_lists_verification_record_tool_with_mutating_metadata() -> None:
    from warpline import mcp

    names = {spec["endorsed"] for spec in mcp.TOOL_SPECS}
    assert "warpline_verification_record" in names
    spec = next(s for s in mcp.TOOL_SPECS if s["endorsed"] == "warpline_verification_record")
    meta = spec["metadata"]
    assert meta["read_only"] is False
    assert meta["writes_local_state"] is True
    assert meta["mutates_paths"] == [".weft/warpline/"]
    assert meta["local_only"] is True
    assert meta["peer_side_effects"] == []
    # Both endorsed + shim dispatch to a handler.
    assert "warpline_verification_record" in mcp._HANDLERS
    assert "verify_record" in mcp._HANDLERS
