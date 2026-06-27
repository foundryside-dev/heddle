from __future__ import annotations

from pathlib import Path

from warpline.loomweave import (
    loomweave_entity_id_candidates,
    loomweave_resolve_qualnames,
    resolve_content_hash_for_locator,
    resolve_sei_for_locator,
)
from warpline.store import WarplineStore


class FakeClient:
    """Mirrors the REAL loomweave entity_resolve: bare dotted qualnames resolve,
    the prefixed/filesystem forms stay unresolved (HX1)."""

    def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        assert name == "entity_resolve"
        assert arguments == {"qualnames": ["pkg.mod.fn", "python:function:pkg/mod.py::fn"]}
        return {
            "results": [
                {
                    "qualname": "pkg.mod.fn",
                    "result_kind": "resolved",
                    "candidates": [
                        {
                            "id": "python:function:pkg.mod.fn",
                            "sei": "loomweave:eid:opaque-value",
                        }
                    ],
                },
                {
                    "qualname": "python:function:pkg/mod.py::fn",
                    "result_kind": "unresolved",
                    "candidates": [],
                },
            ]
        }


def test_resolve_qualnames_are_bare_dotted_for_real_loomweave() -> None:
    assert loomweave_resolve_qualnames("python:function:src/warpline/store.py::S.fn") == [
        "warpline.store.S.fn",
        "src.warpline.store.S.fn",
        "python:function:src/warpline/store.py::S.fn",
    ]


def test_resolve_sei_for_locator_returns_opaque_value() -> None:
    assert (
        resolve_sei_for_locator(FakeClient(), "python:function:pkg/mod.py::fn")
        == "loomweave:eid:opaque-value"
    )


class _HashClient:
    """entity_resolve carrying BOTH sei and content_hash on the candidate — the
    REAL shape (verified live: candidate.content_hash is loomweave's per-entity
    body hash, the same value wardline binds into a wardline-attest-2 boundary)."""

    def __init__(self, content_hash: str | None = "42f3670fbeefbeefbeef") -> None:
        self._chash = content_hash

    def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        assert name == "entity_resolve"
        return {
            "results": [
                {
                    "qualname": "pkg.mod.fn",
                    "result_kind": "resolved",
                    "candidates": [
                        {
                            "id": "python:function:pkg.mod.fn",
                            "sei": "loomweave:eid:opaque-value",
                            "content_hash": self._chash,
                        }
                    ],
                }
            ]
        }


def test_resolve_content_hash_for_locator_reads_loomweave_body_hash() -> None:
    assert (
        resolve_content_hash_for_locator(_HashClient(), "python:function:pkg/mod.py::fn")
        == "42f3670fbeefbeefbeef"
    )


def test_resolve_content_hash_absent_is_none_not_guessed() -> None:
    client = _HashClient(content_hash=None)
    assert resolve_content_hash_for_locator(client, "python:function:pkg/mod.py::fn") is None


def test_loomweave_entity_id_candidates_translate_python_locators() -> None:
    assert loomweave_entity_id_candidates("python:function:pkg/mod.py::Class.fn") == [
        "python:function:pkg.mod.Class.fn",
        "python:function:pkg/mod.py::Class.fn",
    ]


def test_resolve_sei_for_locator_degrades_when_absent() -> None:
    class MissingClient:
        def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
            return {
                "results": [
                    {
                        "qualname": "python:function:pkg.mod::fn",
                        "result_kind": "unresolved",
                        "candidates": [],
                    }
                ]
            }

    assert resolve_sei_for_locator(MissingClient(), "python:function:pkg.mod::fn") is None


def test_resolve_sei_for_locator_accepts_legacy_entity_payload() -> None:
    class LegacyClient:
        def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
            return {
                "entity": {
                    "id": "python:function:pkg.mod::fn",
                    "sei": "loomweave:eid:legacy-value",
                }
            }

    assert (
        resolve_sei_for_locator(LegacyClient(), "python:function:pkg.mod::fn")
        == "loomweave:eid:legacy-value"
    )


def test_store_persists_sei_without_parsing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with WarplineStore.open(tmp_path / "warpline.db") as store:
        repo_id = store.ensure_repo(repo)
        key_id = store.ensure_entity_key(
            repo_id,
            locator="python:function:pkg.mod::fn",
            sei="loomweave:eid:opaque-value",
            commit_sha="c1",
        )
        events = store.list_entity_keys(repo)
    assert events[0]["id"] == key_id
    assert events[0]["sei"] == "loomweave:eid:opaque-value"
