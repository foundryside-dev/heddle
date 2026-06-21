from __future__ import annotations

from pathlib import Path

PUBLIC_DOC_ROOTS = [
    Path("README.md"),
    Path("CHANGELOG.md"),
    Path("docs"),
    Path("spike"),
    Path("src/warpline/skills"),
]

ALLOWLIST = {
    Path("docs/evidence/member-dirty-baseline.txt"),
}


def _public_doc_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(
        path
        for path in root.rglob("*")
        if path.suffix in {".md", ".txt"} and path.is_file()
    )


def test_public_docs_do_not_expose_developer_absolute_paths() -> None:
    offenders: list[str] = []
    for root in PUBLIC_DOC_ROOTS:
        for path in _public_doc_files(root):
            if path in ALLOWLIST:
                continue
            text = path.read_text(encoding="utf-8")
            if "/home/john" in text:
                offenders.append(str(path))

    assert offenders == []
