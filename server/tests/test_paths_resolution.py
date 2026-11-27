"""Tests for the per-call workspace resolution ladder (`resolution` leaf).

Steps land one commit at a time; each rung of the ladder
`paths > _meta > roots > COLGREP_MCP_ROOT > guarded-cwd` is pinned by a test
that fails against the rung's pre-fix state (fail-first):

- Step 1 (`feat(server): resolve the default root from per-call request meta`):
  `test_meta_stamp_beats_pin_and_cwd`, `test_meta_absent_falls_back_silently`,
  `test_meta_alias_priority`.
- Step 2 (`feat(server): resolve per-call roots without the first-call race`):
  `test_first_call_roots_race_regression`, `test_roots_error_falls_to_pin`.
- Step 3 (`feat(search): land the per-call resolution ladder with guided failure`):
  `test_ladder_order_pins_each_rung`, `test_silence_fails_with_paths_guidance`,
  `test_root_source_labels`.

Fabricated `_meta` stamps mirror what `probe.record` records (`request_meta` is
the vendor-key dict from `ctx.request_context.meta`), per the calibration
oracle discipline (02-gap_analysis_calibrated_probe_v0.md).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from colgrep_mcp.config import Settings

pytestmark = pytest.mark.anyio


def _meta_ctx(meta, *, env_root: Path | None = None, session=None) -> SimpleNamespace:
    """A fake MCP `Context` shaped like the SDK's for `resolve_target_paths`.

    `get_settings` reads `ctx.request_context.lifespan_context.settings`;
    `resolve_target_paths` reads `ctx.request_context.meta` (the `_meta` stamp)
    and `ctx.request_context.session` for the roots round-trip.
    """
    settings = Settings(root=env_root)
    return SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(settings=settings),
            meta=meta,
            session=session if session is not None else SimpleNamespace(),
        )
    )


# ---------------------------------------------------------------------------
# Step 1 — request `_meta` workspace stamp (rung 2a)
# ---------------------------------------------------------------------------


def test_meta_stamp_beats_pin_and_cwd(tmp_path):
    """A `_meta` workspace stamp resolves to the stamped root even when a
    `COLGREP_MCP_ROOT` pin *and* a different server cwd are present — meta is
    the higher dynamic rung (R03b; ladder meta > roots > env > guarded-cwd)."""
    from colgrep_mcp.paths import default_root, default_root_from_meta

    stamped = tmp_path / "stamped-workspace"
    stamped.mkdir()
    pinned = tmp_path / "pinned"
    pinned.mkdir()

    meta_root = default_root_from_meta({"com.example.workspace": str(stamped)})
    root, source = default_root(Settings(root=pinned), None, meta_root)
    assert root == stamped.resolve()
    assert source == "meta"


def test_meta_absent_falls_back_silently(tmp_path):
    """No `_meta` stamp degrades to the next rung without raising."""
    from colgrep_mcp.paths import default_root_from_meta

    assert default_root_from_meta(None) is None
    assert default_root_from_meta({}) is None
    # A stamp that is present but unusable (relative path, missing dir, or a
    # non-path value) also degrades silently — never raises.
    assert default_root_from_meta({"com.example.workspace": "relative/path"}) is None
    assert default_root_from_meta({"com.example.workspace": str(tmp_path / "nope")}) is None
    assert default_root_from_meta({"com.example.workspace": 42}) is None


def test_meta_alias_priority(tmp_path):
    """`META_WORKSPACE_KEYS` is honoured in priority order: the first key with
    a usable value wins, even when later (higher-key) aliases carry other
    values."""
    from colgrep_mcp.paths import META_WORKSPACE_KEYS, default_root_from_meta

    winner = tmp_path / "winner"
    winner.mkdir()
    loser = tmp_path / "loser"
    loser.mkdir()

    assert META_WORKSPACE_KEYS[0] == "com.visualstudio.code/workspaceFolder"
    # First alias names the winner; the primary key names a different dir.
    stamp = {
        "com.visualstudio.code/workspaceFolder": str(winner),
        "com.example.workspace": str(loser),
    }
    assert default_root_from_meta(stamp) == winner.resolve()

    # When the leading alias is unusable, the next key is consulted.
    stamp2 = {"com.visualstudio.code/workspaceFolder": "relative/x", "com.example.workspace": str(winner)}
    assert default_root_from_meta(stamp2) == winner.resolve()


async def test_meta_resolves_through_resolve_target_paths(tmp_path):
    """End-to-end: `resolve_target_paths` turns a `_meta` stamp into the
    scoped root without touching env or roots."""
    from colgrep_mcp.paths import resolve_target_paths

    stamped = tmp_path / "ws"
    stamped.mkdir()
    ctx = _meta_ctx({"com.example.workspace": str(stamped)})
    result = await resolve_target_paths(ctx, None)
    assert result == [stamped.resolve()]
