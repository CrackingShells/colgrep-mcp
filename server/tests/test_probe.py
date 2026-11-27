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
- test_probe_record_survives_unresolvable_ladder: the probe hook records an
  unresolved outcome instead of raising when the ladder declines a root.
- test_probe_record_reports_meta_source: a meta-sourced resolution is
  recorded as "meta" (lead integration: probe re-derivation must agree with
  the runtime ladder).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from colgrep_mcp.config import Settings
from colgrep_mcp.probe import PROBE_ENV, _classify_roots, capture_pure, diff_record, forge_record, record

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
# test_record_never_raises_on_hostile_snapshot (lever 2b kill)
# ---------------------------------------------------------------------------


class _ExplodingStr:
    """An object whose ``str()`` raises — the worst case for serialisation."""

    def __str__(self) -> str:  # pragma: no cover - never reached, must raise
        raise RuntimeError("cannot stringify")


def test_record_never_raises_on_hostile_snapshot(tmp_path, monkeypatch):
    """record() is total: a non-JSON-serializable snapshot value must never
    raise.  A coercible value becomes a coerced record (a witness); a value
    whose str() itself fails is swallowed.  Both leave the caller untouched."""
    probe_dir = tmp_path / "probe"
    monkeypatch.setenv("COLGREP_MCP_PROBE", str(probe_dir))

    # 1. Coercible but non-serializable: coerced to a string witness.
    class _Coercible:
        def model_dump(self):
            return {"answer": 42}

        def __str__(self) -> str:
            return "coerced-witness"

    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            initialize=None,
            meta=_Coercible(),
            session=SimpleNamespace(),
        )
    )
    # Must not raise.
    record(ctx=ctx, raw_paths=None, settings_root=None, roots=None, resolved_root=tmp_path, resolved_source="env")
    ledger = probe_dir / "colgrep_probe.jsonl"
    assert ledger.exists()
    snap = json.loads(ledger.read_text().strip().splitlines()[0])
    # request_meta came from model_dump of the _Coercible object.
    assert snap["request_meta"] == {"answer": 42}

    # 2. A value whose str() raises must be swallowed, never raised.
    hostile_ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            initialize=_ExplodingStr(),
            meta=None,
            session=SimpleNamespace(),
        )
    )
    record(
        ctx=hostile_ctx, raw_paths=None, settings_root=None, roots=None, resolved_root=tmp_path, resolved_source="env"
    )  # must not raise


# ---------------------------------------------------------------------------
# test_tool_call_survives_probe_rename (lever 2b, end-to-end)
# ---------------------------------------------------------------------------


async def test_tool_call_survives_probe_rename(tmp_path, monkeypatch):
    """A real tool call through resolve_target_paths survives even when the
    probe encounters a hostile snapshot value.  Regression: the original
    capture_pure sat outside the never-raise boundary, so a TypeError from
    serialising a hostile value propagated up through the resolve path and
    broke the very tool call the docstring promises never to break."""
    probe_dir = tmp_path / "probe"
    monkeypatch.setenv("COLGREP_MCP_PROBE", str(probe_dir))
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))

    # A request_ctx whose _meta carries a value with no JSON encoding and a
    # str() that raises — the worst non-serializable case.
    mock_settings = Settings(root=tmp_path)
    mock_lifespan = SimpleNamespace(settings=mock_settings)
    mock_request_ctx = SimpleNamespace(
        lifespan_context=mock_lifespan,
        meta=_ExplodingStr(),
        session=SimpleNamespace(),
    )
    ctx = SimpleNamespace(request_context=mock_request_ctx)

    from colgrep_mcp.paths import resolve_target_paths

    # The tool call must complete with the correct resolved path, not raise.
    result = await resolve_target_paths(ctx, None)
    assert result == [tmp_path.resolve()]


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


# ---------------------------------------------------------------------------
# test_calibration_whistles_on_fabrication (calibration oracle)
# ---------------------------------------------------------------------------


def test_calibration_whistles_on_fabrication():
    """diff_record must be silent on a truthful record and whistle on a
    fabricated one — e.g. a stub-authoring a `init_capabilities` the harness
    never sent (lever 1b / gap defect 1).  The stub's canonical fabrication
    (FORGED_SAMPLE) must be caught verbatim."""
    from colgrep_mcp.probe import FORGED_SAMPLE

    var = "init_capabilities"
    true_record = forge_record(**{var: {"protocolVersion": "2026-07-28"}}, request_meta={"workspace": "/x"})
    # A truthful record diffs empty.
    assert diff_record(true_record, true_record) == []

    # A fabricated record — the stub's hardcode-lie — must whistle.
    fabricated = dict(true_record)
    fabricated[var] = {"protocolVersion": "NONE"}  # stub wrote this, never the harness
    gaps = diff_record(true_record, fabricated)
    assert gaps, "diff_record must whistle on a fabricated record"
    assert any(var in g for g in gaps), f"fabrication must be named, got {gaps}"

    # The stub's exact fabrication is a fabricated init_capabilities too.
    forged_gaps = diff_record(forge_record(**{var: {"protocolVersion": "2026-07-28"}}), FORGED_SAMPLE)
    assert forged_gaps, "diff_record must whistle on FORGED_SAMPLE verbatim"


# ---------------------------------------------------------------------------
# test_no_probe_side_effects (rewritten: reads the real ledger)
# ---------------------------------------------------------------------------


def test_no_probe_side_effects(tmp_path, monkeypatch):
    """Regression against the real ledger `colgrep_probe.jsonl` (the old test
    asserted dead filenames and re-read only the env, so it could never see a
    fabricated record — lever 3).  A truthful probe writes a record that
    matches forge_record ground truth on every signal column and names the
    calling tool, never "record"."""
    probe_dir = tmp_path / "probe"
    monkeypatch.setenv("COLGREP_MCP_PROBE", str(probe_dir))

    record(
        ctx=_simple_ctx(),
        raw_paths=["/some/path"],
        settings_root=tmp_path,
        roots=None,
        resolved_root=tmp_path.resolve(),
        resolved_source="env",
    )

    ledger = probe_dir / "colgrep_probe.jsonl"
    assert ledger.exists(), "the real ledger colgrep_probe.jsonl must have been written"
    actual = json.loads(ledger.read_text().strip())

    # The tool column must never be the fabricated "record".
    assert actual["tool"] != "record", "probe fabricated the tool column as 'record'"

    expected = forge_record(
        tool="test_no_probe_side_effects",
        raw_paths=["/some/path"],
        roots_list={"static": "declared", "items": []},
        resolved={"root": str(tmp_path.resolve()), "source": "env"},
    )
    signal_cols = ("tool", "raw_paths", "init_capabilities", "request_meta", "roots_list", "resolved")
    gaps = diff_record({k: expected[k] for k in signal_cols}, {k: actual[k] for k in signal_cols})
    assert not gaps, f"probe record diverges from ground truth: {gaps}"


# ---------------------------------------------------------------------------
# Gap-record tolerance and stub provenance (driver hygiene, lever 5 / defect 5)
# ---------------------------------------------------------------------------


def test_gap_records_validate_as_gaps(tmp_path):
    """A validator call with a gap row ({"error": ...}) must return a named
    gap verdict, never raise on snap['ts'] (lever 5 / gap defect 5)."""
    from e2e import probe_workspace as driver

    verdict = driver._validate_record('{"error": "harness not found: claude"}')
    assert verdict == "gap"
    assert driver._validate_record("not json at all") != "valid"
    assert driver._validate_record("{}") != "valid"

    # A file whose only row is a gap validates as OK (gaps report, not crash).
    gap_file = tmp_path / "ledger.jsonl"
    gap_file.write_text('{"error": "completed but no probe record written"}\n', encoding="utf-8")
    assert driver.validate(gap_file) is True


def test_stub_records_carry_provenance():
    """Every stub-written record is stamped provenance: "stub" so a ledger
    reader can separate stub synthesis from server-written rows (lever 1b)."""
    from e2e import probe_workspace as driver

    assert '"provenance": "stub"' in driver._STUB_SCRIPT


# ---------------------------------------------------------------------------
# Probe hook and the resolution ladder agree (lead tier-2 integration)
# ---------------------------------------------------------------------------


def test_probe_record_survives_unresolvable_ladder(tmp_path, monkeypatch):
    """When every ladder rung is silent and cwd is not a project root, the
    probe hook must record the unresolved outcome — never raise past the
    resolve call site (the ladder's ROOT_UNRESOLVED belongs to the caller,
    not to the dump-only probe)."""
    from colgrep_mcp.probe import _probe_record

    monkeypatch.setenv(PROBE_ENV, str(tmp_path / "probe"))
    monkeypatch.chdir(tmp_path)  # no project markers => guarded-cwd declines

    _probe_record(None, None, Settings(), None)  # must not raise

    ledger = [json.loads(line) for line in (tmp_path / "probe" / "colgrep_probe.jsonl").read_text().splitlines()]
    assert len(ledger) == 1
    assert ledger[0]["resolved"] == {"root": None, "source": "unresolved"}


def test_probe_record_reports_meta_source(tmp_path, monkeypatch):
    """A meta-sourced resolution is recorded as source "meta": the probe's
    re-derivation must thread meta_root through the same ladder the runtime
    used, or the ledger contradicts the call it measures."""
    from colgrep_mcp.probe import _probe_record

    monkeypatch.setenv(PROBE_ENV, str(tmp_path / "probe"))
    meta_root = tmp_path / "ws" / "proj"
    meta_root.mkdir(parents=True)

    _probe_record(None, None, Settings(), None, meta_root=meta_root)

    ledger = [json.loads(line) for line in (tmp_path / "probe" / "colgrep_probe.jsonl").read_text().splitlines()]
    assert ledger[0]["resolved"] == {"root": str(meta_root.resolve()), "source": "meta"}
