from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_mcp_smoke(repo: Path, *, include_bad_input: bool = True) -> dict[str, Any]:
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "warpline-mcp-smoke", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "changed", "arguments": {"repo": str(repo)}},
        },
    ]
    if include_bad_input:
        requests.extend(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "changed",
                        "arguments": {"repo": str(repo), "rev_range": "not-a-rev"},
                    },
                },
                {"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
            ]
        )
    responses = _run_stdio_conversation(requests)
    checks = _checks(responses, include_bad_input=include_bad_input)
    return {
        "schema": "warpline.mcp_smoke.v1",
        "ok": all(check["ok"] is True for check in checks),
        "repo": str(repo),
        "transport": "stdio",
        "checks": checks,
    }


def _run_stdio_conversation(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    env = os.environ.copy()
    source_path = str(Path(__file__).resolve().parents[2] / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        source_path
        if not existing_pythonpath
        else f"{source_path}{os.pathsep}{existing_pythonpath}"
    )
    proc = subprocess.run(
        [sys.executable, "-c", "from warpline.mcp import main; raise SystemExit(main())"],
        input="\n".join(json.dumps(request) for request in requests) + "\n",
        check=True,
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def _checks(
    responses: list[dict[str, Any]],
    *,
    include_bad_input: bool,
) -> list[dict[str, Any]]:
    by_id = {response.get("id"): response for response in responses}
    initialize = by_id.get(1, {})
    initialize_result = initialize.get("result")
    checks = [
        {
            "name": "initialize_spec_complete",
            "ok": _initialize_ok(initialize_result),
            "details": initialize_result if isinstance(initialize_result, dict) else initialize,
        },
        {
            "name": "tools_list_available",
            "ok": _tools_list_ok(by_id.get(2, {})),
            "details": {"tool_names": _tool_names(by_id.get(2, {}))},
        },
        {
            "name": "changed_call_returns_payload",
            "ok": _tool_payload_ok(by_id.get(3, {})),
            "details": _tool_summary(by_id.get(3, {})),
        },
    ]
    if include_bad_input:
        bad_response = by_id.get(4, {})
        post_error_tools = by_id.get(5, {})
        checks.extend(
            [
                {
                    "name": "bad_tool_error_structured",
                    "ok": _bad_error_ok(bad_response),
                    "details": bad_response.get("error", bad_response),
                },
                {
                    "name": "server_survives_after_tool_error",
                    "ok": _tools_list_ok(post_error_tools),
                    "details": {"tool_names": _tool_names(post_error_tools)},
                },
            ]
        )
    return checks


def _initialize_ok(result: object) -> bool:
    return (
        isinstance(result, dict)
        and isinstance(result.get("protocolVersion"), str)
        and isinstance(result.get("serverInfo"), dict)
        and result.get("capabilities") == {"tools": {}}
    )


def _tools_list_ok(response: dict[str, Any]) -> bool:
    result = response.get("result")
    tools = result.get("tools") if isinstance(result, dict) else None
    return isinstance(tools, list) and any(
        isinstance(tool, dict) and tool.get("name") == "changed" for tool in tools
    )


def _tool_names(response: dict[str, Any]) -> list[str]:
    result = response.get("result")
    tools = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(tools, list):
        return []
    return sorted(str(tool.get("name")) for tool in tools if isinstance(tool, dict))


def _tool_payload_ok(response: dict[str, Any]) -> bool:
    payload = _structured_content(response)
    return isinstance(payload, dict) and payload.get("ok") is True


def _tool_summary(response: dict[str, Any]) -> dict[str, Any]:
    payload = _structured_content(response)
    if not isinstance(payload, dict):
        return {"payload": None}
    data = payload.get("data")
    return {
        "schema": payload.get("schema"),
        "ok": payload.get("ok"),
        "query": data.get("query") if isinstance(data, dict) else None,
    }


def _structured_content(response: dict[str, Any]) -> object:
    result = response.get("result")
    if not isinstance(result, dict):
        return None
    structured = result.get("structuredContent")
    if structured is not None:
        return structured
    content = result.get("content")
    if not isinstance(content, list) or not content:
        return None
    first = content[0]
    if not isinstance(first, dict):
        return None
    try:
        return json.loads(str(first.get("text", "")))
    except json.JSONDecodeError:
        return None


def _bad_error_ok(response: dict[str, Any]) -> bool:
    error = response.get("error")
    if not isinstance(error, dict) or error.get("code") != -32602:
        return False
    data = error.get("data")
    return (
        isinstance(data, dict)
        and data.get("schema") == "warpline.error.v1"
        and data.get("error_code") == "invalid_rev_range"
        and data.get("retryability") == "retry_with_changes"
    )
