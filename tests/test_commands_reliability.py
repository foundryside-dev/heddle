"""Phase-2 reliability hardening for ``warpline.commands`` (U2 + U3 + U4).

Three disjoint concerns, all in ``commands.py``:

* **U3 — read-path observability.** The three silent read-path swallows
  (``session_context``, ``_lazy_capture_if_missing``, ``_attest_content_hashes``)
  now leave a ``health_log`` breadcrumb carrying ``repr(exc)`` on the failure
  path, mirroring the in-band ``{exc!r}`` cause federation.py already records.
  Every downstream return value stays byte-for-byte identical — this is pure
  observability, added only inside the ``except``.

* **U4 — throttle a capture-time *raise*.** Previously only an *unavailable*
  probe stamped the lazy-capture throttle marker; a capture that raised left no
  marker, so a hot read path re-paid the probe spin-up on every call. The outer
  ``except`` now also stamps the marker. This changes only internal probe
  *timing* (when a re-probe is re-paid) — the read still honestly degrades to
  ``NO_SNAPSHOT``; no envelope/vocabulary/golden-vector changes.

* **U2 — loud positional invariant.** ``reverify_worklist`` aligns
  ``changed[i] <-> changed_key_ids[i]`` (and the affected axis) before handing
  off to ``render_reverify_worklist``. A length mismatch ALREADY raises today
  (``zip(..., strict=True)`` deep in reverify.py); U2 hoists that into a named,
  diagnostic assert at the call site so a future ``_blast``<->``commands`` drift
  fails early and legibly instead of as an opaque ``ValueError``. The assert can
  never fire on currently-valid input (both lists derive from the same
  ``result["changed"]``/``["affected"]`` rows), so it is behavior-preserving.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import commit, init_repo

from warpline import commands
from warpline.store import WarplineStore, default_store_path


def _seed_two_entities(repo: Path) -> tuple[int, int]:
    """Two warpline-local entity_keys (a, b) and NO snapshot. Returns (a_id, b_id)."""

    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        a = store.ensure_entity_key(
            repo_id, locator="python:function:a", sei=None, commit_sha="c1"
        )
        b = store.ensure_entity_key(
            repo_id, locator="python:function:b", sei=None, commit_sha="c1"
        )
    return a, b


def _health_rows(repo: Path) -> list[tuple[str, str]]:
    """Return ``[(code, message), ...]`` from the local health_log for ``repo``."""

    with WarplineStore.open(default_store_path(repo)) as store:
        rows = store.conn.execute(
            "SELECT code, message FROM health_log ORDER BY id"
        ).fetchall()
    return [(str(r["code"]), str(r["message"])) for r in rows]


# ---------------------------------------------------------------------------
# U3 — session_context breadcrumb
# ---------------------------------------------------------------------------


def test_session_context_failure_logs_breadcrumb_and_returns_honest_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A store that is present-but-erroring (inner read raises) records
    SESSION_CONTEXT_FAILED with the cause AND still returns the exact honest
    one-liner. The return string is unchanged before and after the fix; only the
    breadcrumb is new (so an operator can tell 'absent' from 'erroring')."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    # Materialise the store/db so the re-open log path has somewhere to write.
    with WarplineStore.open(default_store_path(repo)) as store:
        store.ensure_repo(repo)

    boom = RuntimeError("list_change_events exploded")

    def _raise(self: object, *_a: object, **_k: object) -> object:
        raise boom

    # Inject at the INNER read (store present, but erroring) — the honest case
    # the breadcrumb exists for. (An open() failure genuinely cannot log.)
    monkeypatch.setattr(commands.WarplineStore, "list_change_events", _raise)

    result = commands.session_context(repo)
    assert result == "warpline: temporal store unavailable"

    rows = _health_rows(repo)
    codes = [code for code, _ in rows]
    assert "SESSION_CONTEXT_FAILED" in codes
    msg = next(message for code, message in rows if code == "SESSION_CONTEXT_FAILED")
    assert repr(boom) in msg


def test_session_context_success_writes_no_breadcrumb(tmp_path: Path) -> None:
    """The success path is untouched: no health_log row, honest summary string."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        store.ensure_repo(repo)

    result = commands.session_context(repo)
    assert "warpline:" in result
    assert _health_rows(repo) == []


# ---------------------------------------------------------------------------
# U3 + U4 — _lazy_capture_if_missing breadcrumb AND throttle-on-raise
# ---------------------------------------------------------------------------


def _force_available_then_capture_raises(monkeypatch: pytest.MonkeyPatch) -> RuntimeError:
    """Probe says 'available' but the capture itself raises. Returns the exc."""

    boom = RuntimeError("capture_edge_snapshot exploded")
    monkeypatch.setattr(
        commands.LoomweaveProbe,
        "probe",
        lambda self: {"status": "available", "version": "fake-1"},
    )
    monkeypatch.setattr(
        commands, "LoomweaveMcpClient", lambda *a, **k: object()
    )

    def _raise(*_a: object, **_k: object) -> object:
        raise boom

    monkeypatch.setattr(commands, "capture_edge_snapshot", _raise)
    return boom


def test_lazy_capture_failure_logs_breadcrumb_and_stays_no_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U3: a capture-time raise records LAZY_CAPTURE_FAILED with the cause while
    the function still returns None and leaves the NO_SNAPSHOT path intact (no
    snapshot written)."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)
    boom = _force_available_then_capture_raises(monkeypatch)

    with WarplineStore.open(default_store_path(repo)) as store:
        ret = commands._lazy_capture_if_missing(
            store, repo, key_ids=[a], loomweave_command=None
        )
        assert ret is None
        assert store.latest_snapshot(repo) is None  # NO_SNAPSHOT preserved

    rows = _health_rows(repo)
    codes = [code for code, _ in rows]
    assert "LAZY_CAPTURE_FAILED" in codes
    msg = next(message for code, message in rows if code == "LAZY_CAPTURE_FAILED")
    assert repr(boom) in msg


def test_lazy_capture_raise_throttles_subsequent_probe_within_cooldown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U4: a capture-time RAISE now stamps the throttle marker, so a second read
    inside the cooldown does NOT re-pay the probe spin-up. Before the fix the
    except only logged/returned — leaving no marker — so the probe ran twice."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, _b = _seed_two_entities(repo)

    probe_calls: list[int] = []

    def _available_then_raise(self: object) -> dict[str, object]:
        probe_calls.append(1)
        return {"status": "available", "version": "fake-1"}

    monkeypatch.setattr(commands.LoomweaveProbe, "probe", _available_then_raise)
    monkeypatch.setattr(commands, "LoomweaveMcpClient", lambda *a, **k: object())

    def _raise(*_a: object, **_k: object) -> object:
        raise RuntimeError("capture exploded")

    monkeypatch.setattr(commands, "capture_edge_snapshot", _raise)

    first = commands.impact_radius(repo, [a], depth=2)
    assert first["data"]["completeness"] == "NO_SNAPSHOT"
    assert len(probe_calls) == 1  # first read probes, capture raises.

    second = commands.impact_radius(repo, [a], depth=2)
    assert second["data"]["completeness"] == "NO_SNAPSHOT"
    # U4: the raise stamped the throttle marker -> the second read short-circuits
    # at the cooldown check and does NOT re-probe.
    assert len(probe_calls) == 1


# ---------------------------------------------------------------------------
# U3 — _attest_content_hashes breadcrumb (signature gains a leading store)
# ---------------------------------------------------------------------------


def test_attest_content_hashes_failure_logs_breadcrumb_and_returns_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A loomweave consult raise records ATTEST_HASH_FAILED with the cause while
    still returning the partial/empty by_sei dict (attestation stays incomplete —
    NEVER a faked-good match)."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        store.ensure_repo(repo)

    boom = RuntimeError("loomweave resolve exploded")

    def _raise(*_a: object, **_k: object) -> object:
        raise boom

    monkeypatch.setattr(commands, "LoomweaveMcpClient", _raise)

    with WarplineStore.open(default_store_path(repo)) as store:
        result = commands._attest_content_hashes(
            store,
            repo,
            affected_seis=["sei:x"],
            sei_to_locator={"sei:x": "loc"},
            loomweave_command=None,
        )
    assert result == {}  # no faked-good hash — attestation stays incomplete.

    rows = _health_rows(repo)
    codes = [code for code, _ in rows]
    assert "ATTEST_HASH_FAILED" in codes
    msg = next(message for code, message in rows if code == "ATTEST_HASH_FAILED")
    assert repr(boom) in msg


def test_attest_content_hashes_success_writes_no_breadcrumb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Happy path is untouched: the dict is populated and NO breadcrumb is
    written (the log is only reached inside the except)."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    with WarplineStore.open(default_store_path(repo)) as store:
        store.ensure_repo(repo)

    class _Client:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(commands, "LoomweaveMcpClient", _Client)
    monkeypatch.setattr(
        commands,
        "resolve_content_hash_for_locator",
        lambda _client, _locator: "deadbeef",
    )

    with WarplineStore.open(default_store_path(repo)) as store:
        result = commands._attest_content_hashes(
            store,
            repo,
            affected_seis=["sei:x"],
            sei_to_locator={"sei:x": "loc"},
            loomweave_command=None,
        )
    assert result == {"sei:x": "deadbeef"}
    assert _health_rows(repo) == []


# ---------------------------------------------------------------------------
# U2 — positional invariant assert at the reverify_worklist call site
# ---------------------------------------------------------------------------


def test_reverify_worklist_raises_on_changed_key_id_misalignment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U2: if a future drift makes ``enrich_blast``'s ``changed`` list shorter
    than ``result["changed"]`` (so changed[i] no longer aligns with
    changed_key_ids[i]), the call-site assert fires with a named, diagnostic
    message — instead of an opaque ``zip(strict=True)`` ValueError deep in
    reverify.py. The assert can never fire on currently-valid input."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, b = _seed_two_entities(repo)
    # Give it a usable snapshot so the worklist has a non-trivial changed axis.
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        sid = store.create_edge_snapshot(repo_id, "c1", "loomweave", "v0", "FULL")
        store.append_snapshot_edge(
            sid,
            source_entity_key_id=a,
            target_entity_key_id=b,
            edge_kind="calls",
            confidence="resolved",
        )

    real_enrich = commands.enrich_blast

    def _drop_first_changed(store: object, repo: Path, result: dict[str, object]):
        changed, affected = real_enrich(store, repo, result)
        # Simulate drift: changed now has FEWER rows than result["changed"].
        return changed[1:], affected

    monkeypatch.setattr(commands, "enrich_blast", _drop_first_changed)

    with pytest.raises(AssertionError, match="changed_key_ids"):
        commands.reverify_worklist(repo, [a], depth=2)


def test_reverify_worklist_aligned_input_does_not_assert(tmp_path: Path) -> None:
    """The invariant holds on real (un-tampered) input: a normal reverify call
    succeeds without tripping the U2 assert — proving it is behavior-preserving
    on every currently-valid input."""

    repo = init_repo(tmp_path)
    commit(repo, "f.py", "x = 1\n")
    a, b = _seed_two_entities(repo)
    with WarplineStore.open(default_store_path(repo)) as store:
        repo_id = store.ensure_repo(repo)
        sid = store.create_edge_snapshot(repo_id, "c1", "loomweave", "v0", "FULL")
        store.append_snapshot_edge(
            sid,
            source_entity_key_id=a,
            target_entity_key_id=b,
            edge_kind="calls",
            confidence="resolved",
        )

    payload = commands.reverify_worklist(repo, [a], depth=2)
    assert payload["data"]["completeness"] == "FULL"
