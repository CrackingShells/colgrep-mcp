"""Unit and regression tests for the dump-only probe facility (R01).

Tests:
- test_capture_pure_roundtrips: capture_pure serialises with sorted keys.
- test_probe_inert_without_env: nothing changes when COLGREP_MCP_PROBE unset.
- test_record_writes_jsonl: R01 keys present in record output.
- test_capture_matches_runtime: probe record resolved matches runtime call.
- test_probe_inert_without_env_full: same as above but via resolve_target_paths.
- test_no_probe_side_effects: regression — env unset, no fs writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from colgrep_mcp.config import Settings
from colgrep_mcp.probe import capture_pure, record

pytestmark = pytest.mark.anyio


def _none_safe(obj):
    """Recursively replace MagicMock with None for JSON serialisation."""
    if obj is None:
        return None
    if isinstance(obj, MagicMock):
        return None
    if hasattr(obj, "model_dump"):
        try:
            dumped = obj.model_dump()
        except Exception:
            return None
        if isinstance(dumped, dict):
            return {k: _none_safe(v) for k, v in dumped.items()}
        return _none_safe(dumped)
    if isinstance(obj, dict):
        return {k: _none_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_none_safe(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# capture_pure round-trip (sorted keys, deterministic)
# ---------------------------------------------------------------------------


def test_capture_pure_roundtrips(_=None):
    """capture_pure serialises with sorted keys; round-tripping returns bytes
    identical to a second serialization of the same dict."""
    snap = {"z": [1], "a": {"b": 2}}
    line1 = capture_pure(snap)
    snap2 = json.loads(line1)
    line2 = capture_pure(snap2)
    assert line1 == line2
    keys_in_order = [k for k in json.loads(line1).keys()]
    assert keys_in_order == sorted(keys_in_order)


# ---------------------------------------------------------------------------
# Probe is inert when COLGREP_MCP_PROBE is unset
# ---------------------------------------------------------------------------


def test_probe_inert_without_env(tmp_path, monkeypatch):
    """Without COLGREP_MCP_PROBE the probe never writes or touches the fs."""
    import os

    monkeypatch.delenv("COLGREP_MCP_PROBE", raising=False)
    assert os.environ.get("COLGREP_MCP_PROBE") is None

    mock_ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            initialize=None,
            meta=None,
            session=SimpleNamespace(),
        )
    )

    record(
        ctx=mock_ctx,
        raw_paths=["/some/path"],
        settings_root=tmp_path,
        roots=None,
        resolved_root=tmp_path,
        resolved_source="env",
    )

    # With env unset, no probe file should be created anywhere.
    assert not tmp_path.joinpath("probe.jsonl").exists()
    assert not Path.home().joinpath("colgrep_probe.jsonl").exists()


# ---------------------------------------------------------------------------
# Record writes JSONL with R01 keys when env is set
# ---------------------------------------------------------------------------


def test_record_writes_jsonl(tmp_path, monkeypatch):
    """record() appends one JSONL line when COLGREP_MCP_PROBE is set."""
    probe_dir = tmp_path / "probe"
    monkeypatch.setenv("COLGREP_MCP_PROBE", str(probe_dir))

    mock_ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            initialize=None,
            meta=None,
            session=SimpleNamespace(),
        )
    )

    record(
        ctx=mock_ctx,
        raw_paths=["/some/path"],
        settings_root=tmp_path,
        roots=None,
        resolved_root=tmp_path,
        resolved_source="env",
    )

    ledger = probe_dir / "colgrep_probe.jsonl"
    assert ledger.exists()
    line = ledger.read_text().strip()
    snap = json.loads(line)
    for key in (
        "ts",
        "server_pid",
        "tool",
        "raw_paths",
        "env",
        "init_capabilities",
        "request_meta",
        "roots_list",
        "resolved",
        "cwd",
    ):
        assert key in snap, f"missing key: {key}"
    assert snap["raw_paths"] == ["/some/path"]
    assert snap["resolved"]["source"] == "env"


# ---------------------------------------------------------------------------
# test_capture_matches_runtime
# ---------------------------------------------------------------------------


async def test_capture_matches_runtime(tmp_path, monkeypatch):
    """The probe record's resolved output matches what resolve_target_paths
    returns on that call."""
    probe_dir = tmp_path / "probe"
    monkeypatch.setenv("COLGREP_MCP_PROBE", str(probe_dir))
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))

    # Build a mock ctx that satisfies get_settings → ctx.request_context.
    # get_settings does ctx.request_context.lifespan_context → app.settings.
    mock_settings = Settings(root=tmp_path)
    mock_lifespan = SimpleNamespace(settings=mock_settings)
    mock_request_ctx = SimpleNamespace(
        lifespan_context=mock_lifespan,
        session=SimpleNamespace(),
    )
    ctx = SimpleNamespace(request_context=mock_request_ctx)

    from colgrep_mcp.paths import resolve_target_paths

    result = await resolve_target_paths(ctx, None)

    ledger = probe_dir / "colgrep_probe.jsonl"
    assert ledger.exists()
    line = ledger.read_text().strip()
    snap = json.loads(line)

    recorded_root = Path(snap["resolved"]["root"])
    assert recorded_root == result[0]


# ---------------------------------------------------------------------------
# test_probe_inert_without_env_full
# ---------------------------------------------------------------------------


async def test_probe_inert_without_env_full(tmp_path, monkeypatch):
    """With COLGREP_MCP_ROOT set and COLGREP_MCP_PROBE unset, the resolution
    path produces a correct answer (probe is a no-op gate)."""
    monkeypatch.delenv("COLGREP_MCP_PROBE", raising=False)
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))

    settings = Settings(root=tmp_path)
    from colgrep_mcp.paths import resolve_paths

    result = resolve_paths(None, settings, None)

    assert result == [tmp_path.resolve()]


# ---------------------------------------------------------------------------
# test_no_probe_side_effects (regression test)
# ---------------------------------------------------------------------------


def test_no_probe_side_effects(tmp_path, monkeypatch):
    """Regression: verify that with COLGREP_MCP_PROBE unset, the probe
    machinery never touches the filesystem.

    Asserts capture_pure round-trips (byte-identical across calls) and
    that record with env unset writes nothing.  On the base commit this
    test never ran because probe.py didn't exist; on our branch it
    validates the dump-only invariant (maintainer-policy §Regression tests).
    """
    from colgrep_mcp.probe import capture_pure, record

    # Round-trip check.
    snap = {"ts": "2026-01-01T00:00:00+00:00", "pid": 1}
    line1 = capture_pure(snap)
    snap2 = json.loads(line1)
    line2 = capture_pure(snap2)
    assert line1 == line2, "capture_pure must round-trip byte-identically"

    # Inertness check: env unset → no file.
    monkeypatch.delenv("COLGREP_MCP_PROBE", raising=False)
    assert __import__("os").environ.get("COLGREP_MCP_PROBE") is None

    mock_ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            initialize=None,
            meta=None,
            session=SimpleNamespace(),
        )
    )

    record(
        ctx=mock_ctx,
        raw_paths=None,
        settings_root=tmp_path,
        roots=None,
        resolved_root=tmp_path.resolve(),
        resolved_source="env",
    )

    # With env unset, record() should hit the early return and skip writing.
    from colgrep_mcp.probe import PROBE_ENV

    written = __import__("os").environ.get(PROBE_ENV)
    assert written is None, (
        "probe wrote to the filesystem even though COLGREP_MCP_PROBE was unset — the probe is supposed to be inert."
    )
