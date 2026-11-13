"""Unit and regression tests for the dump-only probe facility (R01).

Tests:
- test_capture_pure_roundtrips: capture_pure serialises with sorted keys.
- test_probe_inert_without_env: nothing changes when COLGREP_MCP_PROBE unset.
- test_record_writes_jsonl: R01 keys present in record output.
- test_capture_matches_runtime: probe record resolved matches runtime call.
- test_tool_column_names_the_actual_tool: the ledger names the calling tool,
  never "record" (lever 1 repair).
- test_roots_error_distinct_from_empty: a failed round-trip is "error", a
  genuine zero-root answer is "empty" (lever 6 / gap defect 6).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from colgrep_mcp.config import Settings
from colgrep_mcp.probe import _classify_roots, capture_pure, record

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


def _simple_ctx() -> SimpleNamespace:
    return SimpleNamespace(
        request_context=SimpleNamespace(
            initialize=None,
            meta=None,
            session=SimpleNamespace(),
        )
    )


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

    record(
        ctx=_simple_ctx(),
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

    record(
        ctx=_simple_ctx(),
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
# test_tool_column_names_the_actual_tool (lever 1 repair)
# ---------------------------------------------------------------------------


async def test_tool_column_names_the_actual_tool(tmp_path, monkeypatch):
    """The record's ``tool`` column names the actual calling tool, never
    ``"record"``.  Regression: the original frame scan resolved to ``record``
    itself every time, silently falsifying the matrix column."""
    probe_dir = tmp_path / "probe"
    monkeypatch.setenv("COLGREP_MCP_PROBE", str(probe_dir))
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))

    mock_settings = Settings(root=tmp_path)
    mock_lifespan = SimpleNamespace(settings=mock_settings)
    mock_request_ctx = SimpleNamespace(
        lifespan_context=mock_lifespan,
        session=SimpleNamespace(),
    )
    ctx = SimpleNamespace(request_context=mock_request_ctx)

    from colgrep_mcp.paths import resolve_target_paths

    # Wire the resolution path through a helper whose name stands for the
    # "calling tool" the way a real tool handler would.
    async def _fake_tool_handler(ctx_: object) -> object:
        return await resolve_target_paths(ctx_, None)  # type: ignore[arg-type]

    await _fake_tool_handler(ctx)

    ledger = probe_dir / "colgrep_probe.jsonl"
    assert ledger.exists()
    snap = json.loads(ledger.read_text().strip())
    assert snap["tool"] == "_fake_tool_handler", "tool column should name the calling tool, not 'record'"
    assert snap["tool"] != "record"


# ---------------------------------------------------------------------------
# test_roots_error_distinct_from_empty (lever 6 / gap defect 6)
# ---------------------------------------------------------------------------


def test_roots_error_distinct_from_empty(tmp_path):
    """A failed round-trip classifies as ``error``; a genuine zero-root answer
    classifies as ``empty``; a present pin or returned roots classify as
    ``declared`` (never merged into one value)."""
    # declared: COLGREP_MCP_ROOT pin present, roots consulted or not.
    assert _classify_roots(settings_root=tmp_path, roots=None, roots_error=False) == "declared"
    # declared: client_roots returned items.
    assert _classify_roots(settings_root=None, roots=[tmp_path], roots_error=False) == "declared"
    # error: the round-trip raised / back-channel absent.
    assert _classify_roots(settings_root=None, roots=None, roots_error=True) == "error"
    # empty: a client genuinely answered with zero roots.
    assert _classify_roots(settings_root=None, roots=None, roots_error=False) == "empty"
