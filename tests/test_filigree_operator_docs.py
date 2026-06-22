from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _one_line(text: str) -> str:
    return " ".join(text.split())


def test_filigree_api_url_is_documented_for_operators() -> None:
    readme = _read("README.md")
    federation = _read("docs/federation.md")
    mcp_tools = _read("docs/reference/mcp-tools.md")
    cli = _read("docs/reference/cli.md")
    federation_line = _one_line(federation)
    mcp_tools_line = _one_line(mcp_tools)

    for text in [readme, federation, mcp_tools, cli]:
        assert "`FILIGREE_API_URL`" in text
        assert "http://localhost:8724" in text

    assert "Filigree work-state enrichment uses filigree's dashboard HTTP API" in readme
    assert "`unavailable` / member `unreachable`" in readme

    assert "MCP `reverify` / `warpline_reverify_worklist_get`" in federation_line
    assert "records the filigree member as `unreachable`" in federation_line
    assert "reports work enrichment as `unavailable`" in federation_line

    assert "`include_federation=true`" in mcp_tools_line
    assert "records work enrichment as `unavailable`" in mcp_tools_line
    assert "filigree member reason `unreachable`" in mcp_tools_line

    cli_line = _one_line(cli)
    assert "`FILIGREE_API_URL` | `http://localhost:8724`" in cli_line
    assert "work `unavailable` / filigree `unreachable`" in cli_line
    assert "Loomweave scope: `WARPLINE_LOOMWEAVE_COMMAND`" in cli
