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


# ---------------------------------------------------------------------------
# Step 3 — the ladder, the pin rung, and fail-with-guidance (R01 guarded-cwd)
# ---------------------------------------------------------------------------


def test_ladder_order_pins_each_rung(tmp_path, monkeypatch):
    """The rung order `_meta > roots > COLGREP_MCP_ROOT > guarded-cwd` is the
    single resolution idiom: each higher rung wins over every lower one, and
    a silent-everything call under a plausible cwd uses the cwd."""
    from colgrep_mcp.paths import default_root

    stamped = tmp_path / "meta-ws"
    stamped.mkdir()
    rooted = tmp_path / "roots-ws"
    rooted.mkdir()
    pinned = tmp_path / "pin"
    pinned.mkdir()
    cwd_proj = tmp_path / "cwd-proj"
    cwd_proj.mkdir()
    (cwd_proj / "pyproject.toml").touch()

    settings = Settings(root=pinned)
    # meta beats roots, pin, and cwd.
    assert default_root(settings, [rooted], stamped)[1] == "meta"
    # roots beats pin and cwd (no meta).
    assert default_root(settings, [rooted], None) == (rooted.resolve(), "roots")
    # pin beats cwd (no meta, no roots).
    assert default_root(settings, None, None) == (pinned.resolve(), "env")
    # all silent under a plausible cwd uses the cwd.
    monkeypatch.chdir(cwd_proj)
    root, source = default_root(Settings(), None, None)
    assert source == "cwd"
    assert root == cwd_proj.resolve()


def test_silence_fails_with_paths_guidance(tmp_path, monkeypatch):
    """When every rung is silent and the working directory is not a plausible
    project root, resolution raises `ROOT_UNRESOLVED` whose message names the
    remedy verbatim: pass an absolute `paths` entry (R01 fail+guidance)."""
    from mcp.server.mcpserver.exceptions import ToolError

    from colgrep_mcp.errors import Code
    from colgrep_mcp.paths import default_root

    not_a_project = tmp_path / "not-a-project"
    not_a_project.mkdir()
    monkeypatch.chdir(not_a_project)

    with pytest.raises(ToolError) as excinfo:
        default_root(Settings(), None, None)

    msg = str(excinfo.value)
    assert Code.ROOT_UNRESOLVED in msg
    assert "paths" in msg and "absolute" in msg


def test_root_source_labels(tmp_path):
    """Every ladder source is surfaced through the `root_source` label, and a
    multi-root answer uses `roots[0]` (R01 multi-root policy)."""
    from colgrep_mcp.paths import default_root

    pinned = tmp_path / "pin"
    pinned.mkdir()
    first = tmp_path / "first"
    first.mkdir()
    second = tmp_path / "second"
    second.mkdir()
    stamped = tmp_path / "stamp"
    stamped.mkdir()

    assert default_root(Settings(), [first, second], None)[1] == "roots"
    assert default_root(Settings(), [first, second], None)[0] == first.resolve()  # roots[0]
    assert default_root(Settings(root=pinned), None, stamped)[1] == "meta"


def test_guide_documents_ladder_and_remedy():
    """The served guide's §Scoping pins the ladder order and the absolute-`paths`
    remedy — the client-visible behaviour change of this leaf (maintainer-policy)."""
    import importlib.resources

    guide = importlib.resources.files("colgrep_mcp").joinpath("guide.md").read_text()
    assert "## Scoping" in guide
    assert "explicit paths" in guide and "_meta" in guide and "client roots" in guide
    assert "COLGREP_MCP_ROOT" in guide
    assert "ROOT_UNRESOLVED" in guide
    assert "absolute `paths` entry" in guide


# ---------------------------------------------------------------------------
# Close-out — verifier findings (F1–F4), each pinned fail-first
# ---------------------------------------------------------------------------


async def test_named_remedy_is_itself_a_working_escape(tmp_path, monkeypatch):
    """Following the ROOT_UNRESOLVED remedy literally must work (verifier F1):
    with the ladder silent, an explicit absolute `paths` entry naming an
    existing directory scopes the call on its own — never re-raises the same
    error the entry is the remedy for.  The absolute entry is the user
    speaking; no inferred default root is needed to honor it."""
    from colgrep_mcp.paths import resolve_target_paths

    not_a_project = tmp_path / "not-a-project"
    not_a_project.mkdir()
    monkeypatch.chdir(not_a_project)  # every ladder rung silent

    ctx = _meta_ctx(None)
    resolved = await resolve_target_paths(ctx, [str(not_a_project)])
    assert resolved == [not_a_project.resolve()]


async def test_pathless_file_uri_root_never_scopes_the_filesystem(tmp_path, monkeypatch):
    """A client root that names no directory must not become the filesystem
    root (verifier F2): a path-less `file:` URI normalizes to path `'/'`, and
    `'/'` scopes a path-less call to the entire disk — the silent wrong root
    this campaign exists to prevent.  Such a root is unusable: it degrades to
    the zero-root class and the ladder falls through to its guided failure."""
    from mcp.server.mcpserver.exceptions import ToolError

    from colgrep_mcp.errors import Code
    from colgrep_mcp.paths import resolve_target_paths

    monkeypatch.chdir(tmp_path)  # not a plausible project root

    async def pathless_roots():
        return ListRootsResult(roots=[Root(uri="file:")])

    ctx = _meta_ctx(None)
    ctx.session.list_roots = pathless_roots

    with pytest.raises(ToolError) as excinfo:
        await resolve_target_paths(ctx, None)
    assert Code.ROOT_UNRESOLVED in str(excinfo.value)


def test_classify_needs_usable_items_for_declared():
    """`declared` means the client returned usable root items (verifier F3):
    an empty list is never `declared`, or the ledger certifies roots the
    client never sent."""
    from colgrep_mcp.probe import _classify_roots

    assert _classify_roots(None, [], False) == "empty"
    assert _classify_roots(None, [], True) == "error"
    assert _classify_roots(None, [Path("/ws")], False) == "declared"


async def test_concurrent_first_calls_both_reassure_before_settling(tmp_path, monkeypatch):
    """A pair of concurrent path-less first calls must both settle on the late
    arriving root (verifier F4): the reassurance budget belongs to the
    freshly-connected *state*, not to one winner of the first lock.  With the
    budget spent by one caller, the other's premature emptiness conclusion
    lands on a wrong project cwd — the silent wrong root this campaign
    exists to prevent."""
    import asyncio

    from colgrep_mcp import paths as paths_module
    from colgrep_mcp.paths import resolve_target_paths

    project = tmp_path / "corpus"
    project.mkdir()
    bogus = tmp_path / "looks-like-project"
    bogus.mkdir()
    (bogus / "pyproject.toml").touch()
    monkeypatch.chdir(bogus)  # a premature fallback lands on the WRONG project

    class Flaky:
        """Answers provisional-empty until the harness root lands (R03b)."""

        def __init__(self, ready_after: int):
            self.n = 0
            self.ready_after = ready_after

        async def list_roots(self):
            self.n += 1
            resp = [] if self.n <= self.ready_after else [Root(uri=project.as_uri())]
            await asyncio.sleep(0)
            return ListRootsResult(roots=resp)

    session = Flaky(ready_after=2)
    ctx_a, ctx_b = _meta_ctx(None), _meta_ctx(None)
    ctx_a.session.list_roots = session.list_roots
    ctx_b.session.list_roots = session.list_roots

    paths_module._FIRST_EMPTY_REASSURE = True
    try:
        ra, rb = await asyncio.gather(
            resolve_target_paths(ctx_a, None),
            resolve_target_paths(ctx_b, None),
        )
    finally:
        paths_module._FIRST_EMPTY_REASSURE = True

    assert ra == [project.resolve()], f"caller A resolved {ra} — lost the late root to a premature fallback"
    assert rb == [project.resolve()], f"caller B resolved {rb} — lost the late root to a premature fallback"
