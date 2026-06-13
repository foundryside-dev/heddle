from __future__ import annotations

from pathlib import Path


def hook_body(executable: str) -> str:
    return f"""#!/bin/sh
# BEGIN WARPLINE MANAGED BLOCK
# Managed by Warpline. Fail-soft by design: Warpline must never block commits.
{executable} ingest-commit HEAD >/dev/null 2>&1 || true
# END WARPLINE MANAGED BLOCK
exit 0
"""


def install_hook(repo: Path, executable: str = "warpline") -> Path:
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    if hook.exists():
        existing = hook.read_text(encoding="utf-8")
        if "BEGIN WARPLINE MANAGED BLOCK" not in existing:
            raise FileExistsError(f"refusing to overwrite unmanaged hook: {hook}")
    hook.write_text(hook_body(executable), encoding="utf-8")
    hook.chmod(0o755)
    return hook
