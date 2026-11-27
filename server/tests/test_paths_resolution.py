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
from mcp.types import ListRootsResult, Root

from colgrep_mcp.config import Settings

pytestmark = pytest.mark.anyio


async def _absent_roots():
    """Default fake `session.list_roots`: a genuine zero-root answer."""
    return ListRootsResult(roots=[])


def _meta_ctx(meta, *, env_root: Path | None = None, session=None) -> SimpleNamespace:
    """A fake MCP `Context` shaped like the SDK's for `resolve_target_paths`.

    `get_settings` reads `ctx.request_context.lifespan_context.settings`;
    the resolver reads the `_meta` stamp from `ctx.request_context.meta`; the
    roots round-trip goes over `ctx.session` (the SDK's `Context.session`
    property).  The same object is reachable through both paths so a fake can
    drive the roots response.  ``session`` defaults to a genuine zero-root
    responder; a test overrides ``ctx.session.list_roots`` to drive a race.
    """
    settings = Settings(root=env_root)
    session = session if session is not None else SimpleNamespace(list_roots=_absent_roots)
    return SimpleNamespace(
        session=session,
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(settings=settings),
            meta=meta,
            session=session,
        ),
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


# ---------------------------------------------------------------------------
# Step 2 — per-call client roots without the first-call race (rung 2b)
# ---------------------------------------------------------------------------


def _flaky_first_empty_root(ctx, root: Path):
    """Give `ctx` a `session.list_roots` that answers the *first* call with an
    empty set and the second with `root` — the R03b first-call race shape —
    and return a counter recording how many `roots/list` round-trips ran."""
    calls = {"n": 0}

    async def list_roots():
        calls["n"] += 1
        if calls["n"] == 1:
            return ListRootsResult(roots=[])
        return ListRootsResult(roots=[Root(uri=root.as_uri())])

    ctx.session.list_roots = list_roots
    return calls


async def test_first_call_roots_race_regression(tmp_path):
    """The first `resolve` on a fresh connection must answer from the roots the
    client actually sent, never from a premature cwd fallback (R03b: first
    resolve empty -> `cwd`, second -> `roots`; a late root must win)."""
    from colgrep_mcp import paths as paths_module
    from colgrep_mcp.paths import resolve_target_paths

    # Re-enter the freshly-connected state: once a non-first empty has turned
    # the reassurance off, later calls must not keep re-asking (one round-trip
    # per call steady state) — so re-arm it for the race the fix targets.
    paths_module._FIRST_EMPTY_REASSURE = True
    try:
        project = tmp_path / "corpus"
        project.mkdir()
        ctx = _meta_ctx(None)
        calls = _flaky_first_empty_root(ctx, project)

        resolved = await resolve_target_paths(ctx, None)

        assert calls["n"] == 2, "the first empty must be re-asked once (bounded reassurance)"
        assert resolved == [project.resolve()], (
            f"the late-arriving root must win over a premature cwd fallback; resolved {resolved}"
        )
    finally:
        paths_module._FIRST_EMPTY_REASSURE = True


def test_roots_error_falls_to_pin(tmp_path):
    """A failed roots round-trip (`error`, not `empty`) falls to the
    `COLGREP_MCP_ROOT` pin; it must never land on cwd when a pin is set."""
    from colgrep_mcp.paths import default_root

    pinned = tmp_path / "pin"
    pinned.mkdir()
    # roots = None is the `error`-classed form `_client_roots` returns when the
    # back-channel raised or was absent (probe lever 6: error != empty).
    root, source = default_root(Settings(root=pinned), None)
    assert root == pinned.resolve() and source == "env"
