"""Tests for the index management tools (R01 §Tools; R05 D2, D3): the
read-only tools (`index_status`, `list_indexes`, `doctor`), `index_build`
(heartbeat progress) and `index_clear` (project-root refusal +
elicitation-guarded confirmation).
"""

from __future__ import annotations

import asyncio
import dataclasses
import json

import pytest
from mcp import Client
from mcp.types import ElicitRequestParams, ElicitResult, ListRootsResult, Root

from colgrep_mcp import tools_index
from colgrep_mcp.adapter import ColgrepAdapter
from colgrep_mcp.config import Settings
from colgrep_mcp.errors import HINTS, Code
from colgrep_mcp.models import IndexInfo
from colgrep_mcp.server import AppContext, build

pytestmark = pytest.mark.anyio


class _StubRequestContext:
    def __init__(self, lifespan_context: AppContext) -> None:
        self.lifespan_context = lifespan_context


class _StubCtx:
    """Minimal stand-in for `Context`: just enough for `index_build`'s own
    use of `ctx.request_context.lifespan_context`, `ctx.report_progress` and
    `ctx.notify_resource_updated` — no real MCP session involved.

    Lets F2's regression test cancel `index_build` directly (as a plain
    asyncio task) without depending on whether the SDK's own transport
    delivers a client cancellation as `asyncio.CancelledError`.
    """

    def __init__(self, adapter: ColgrepAdapter, settings: Settings) -> None:
        self.request_context = _StubRequestContext(AppContext(settings=settings, adapter=adapter))

    async def report_progress(self, *args: object, **kwargs: object) -> None:
        pass

    async def notify_resource_updated(self, *args: object, **kwargs: object) -> None:
        pass


# --- index_status -------------------------------------------------------------


async def test_index_status_indexed(settings_env, tmp_path):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_status", {"path": str(tmp_path)})

    assert not result.is_error
    assert result.structured_content["indexed"] is True
    assert result.structured_content["project"] == str(tmp_path)
    assert result.structured_content["requested_path"] == str(tmp_path)
    assert "Indexed" in result.content[0].text


async def test_index_status_not_indexed(settings_env, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_INDEXED", "0")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_status", {"path": str(tmp_path)})

    assert not result.is_error
    assert result.structured_content["indexed"] is False
    assert "Not indexed" in result.content[0].text


async def test_index_status_enriches_units_from_stats(settings_env, tmp_path, monkeypatch):
    # The fake binary's `--stats` output always names /tmp/fake-corpus; make
    # `status` report that same project so index_status can match and enrich.
    monkeypatch.setenv("FAKE_COLGREP_STATUS_PROJECT", "/tmp/fake-corpus")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_status", {"path": str(tmp_path)})

    assert not result.is_error
    assert result.structured_content["units_indexed"] == 3
    assert result.structured_content["search_count"] == 7


async def test_index_status_matches_stats_by_resolved_path_when_strings_differ(settings_env, tmp_path, monkeypatch):
    """`_match_stats` falls back to a resolved-path comparison only when the
    plain string comparison misses; here `status.project` carries a trailing
    `/.` the fake `--stats` output (always `/tmp/fake-corpus`) never has, so
    a string-only match would miss the enrichment entirely."""
    monkeypatch.setenv("FAKE_COLGREP_STATUS_PROJECT", "/tmp/fake-corpus/.")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_status", {"path": str(tmp_path)})

    assert not result.is_error
    assert result.structured_content["project"] == "/tmp/fake-corpus/."
    assert result.structured_content["units_indexed"] == 3
    assert result.structured_content["search_count"] == 7


# --- list_indexes ---------------------------------------------------------------


async def test_list_indexes_count(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("list_indexes", {})

    assert not result.is_error
    assert len(result.structured_content["indexes"]) == 2
    projects = {i["project"] for i in result.structured_content["indexes"]}
    assert projects == {"/tmp/fake-corpus", "/tmp/other"}


async def test_list_indexes_single_project_block_format_unchanged(settings_env):
    """R01 §C7: adding the `"<n> indexed projects on this machine"` header
    must not touch the per-index block format (`project  model=…  units=…
    searches=…`) that predates the budgeted renderer."""
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("list_indexes", {})

    assert not result.is_error
    lines = result.content[0].text.splitlines()
    assert lines[0] == "2 indexed projects on this machine"
    for info in result.structured_content["indexes"]:
        expected = (
            f"{info['project']}  model={info['model']}  units={info['units_indexed']}  searches={info['search_count']}"
        )
        assert expected in lines[1:]


async def test_list_indexes_text_is_budgeted_and_structured_content_is_complete(settings_env, monkeypatch):
    """R01 §C7: `list_indexes`' text is machine-global (24 kB observed on one
    machine, KT-B) and must be capped like every other renderer
    (R01 consistency §Token-budget invariant), while `structured_content`
    keeps every index. Regression test: this fails against the pre-change
    `_render_index_list` (no budget parameter, unbounded `"\\n".join(...)`)."""
    fake_indexes = [
        IndexInfo(
            project=f"/very/long/synthetic/path/that/pads/out/the/rendered/block/length/project-{i:04d}",
            model="lightonai/LateOn-Code-edge",
            units_indexed=i,
            search_count=i * 2,
        )
        for i in range(400)
    ]

    async def fake_stats(self):
        return fake_indexes

    monkeypatch.setattr(ColgrepAdapter, "stats", fake_stats)

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("list_indexes", {})

    assert not result.is_error
    text = result.content[0].text
    settings = Settings.from_env()
    assert len(text) <= settings.text_budget
    assert "more indexes in structured_content]" in text.splitlines()[-1]
    assert len(result.structured_content["indexes"]) == 400


@pytest.fixture
def housekeeping_store(fake_store, tmp_path, monkeypatch):
    """A store with one live project, one shadowed child, one orphan and one machine-state
    entry (index_housekeeping R01 §C3). The machine-state roots are pinned to one directory
    under `tmp_path` because the CI runners' own temp directory sits under the home
    directory on Windows (R01 risk 2) — `tmp_path` itself must never read as machine state."""
    live = tmp_path / "live"
    (live / "sub").mkdir(parents=True)
    scratch = tmp_path / "temp" / "scratch"
    scratch.mkdir(parents=True)
    monkeypatch.setattr(tools_index.store, "machine_state_roots", lambda home: [str(tmp_path / "temp")])
    fake_store("live-0001", live, search_count=9, files=5)
    fake_store("sub-0002", live / "sub", search_count=1, files=2)
    fake_store("gone-0003", tmp_path / "gone", search_count=1, files=4, age_days=45)
    fake_store("scratch-0004", scratch, search_count=0, files=1)
    old = tmp_path / "old"
    old.mkdir()
    fake_store("old-0005", old, search_count=1, files=2, age_days=45)
    return {"live": live, "sub": live / "sub", "gone": tmp_path / "gone", "scratch": scratch, "old": old}


async def test_list_indexes_carries_store_fields(settings_env, housekeeping_store):
    """R01 §C4: size, age, path-exists, shadowing and the `stale` class ride along."""
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("list_indexes", {})

    assert not result.is_error
    by_project = {i["project"]: i for i in result.structured_content["indexes"]}
    assert set(by_project) == {str(p) for p in housekeeping_store.values()}
    live = by_project[str(housekeeping_store["live"])]
    assert live["path_exists"] is True and live["stale"] is None and live["size_bytes"] > 1024
    assert live["last_modified"][:2] == "20"
    sub = by_project[str(housekeeping_store["sub"])]
    assert sub["stale"] == "shadowed" and sub["shadowed_by"] == str(housekeeping_store["live"])
    gone = by_project[str(housekeeping_store["gone"])]
    assert gone["stale"] == "orphaned" and gone["path_exists"] is False
    assert by_project[str(housekeeping_store["scratch"])]["stale"] == "machine_state"
    assert by_project[str(housekeeping_store["old"])]["stale"] is None  # `cold` is index_prune's, not `stale`
    assert result.structured_content["total"] == 5
    assert result.structured_content["total_bytes"] > 5 * 1024

    text = result.content[0].text
    assert text.splitlines()[0].startswith("5 indexed projects on this machine (")
    assert "1 orphaned, 1 machine-state, 1 shadowed)" in text.splitlines()[0]
    assert f"{housekeeping_store['gone']}  model=lightonai/LateOn-Code-edge  units=4  searches=1  size=" in text
    assert "  [orphaned]" in text
    assert f"  [shadowed by {housekeeping_store['live']}]" in text
    assert "  [machine_state]" in text


async def test_list_indexes_stale_only_filters_and_keeps_the_total(settings_env, housekeeping_store):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("list_indexes", {"stale_only": True})

    assert not result.is_error
    kinds = sorted(i["stale"] for i in result.structured_content["indexes"])
    assert kinds == ["machine_state", "orphaned", "shadowed"]
    assert result.structured_content["total"] == 5
    assert result.content[0].text.splitlines()[0].startswith("3 stale of 5 indexed projects on this machine (")


async def test_list_indexes_stale_only_with_nothing_stale(settings_env, fake_store, tmp_path, monkeypatch):
    live = tmp_path / "live"
    live.mkdir()
    monkeypatch.setattr(tools_index.store, "machine_state_roots", lambda home: [])
    fake_store("live-0001", live, search_count=3)

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("list_indexes", {"stale_only": True})

    assert result.structured_content["indexes"] == []
    assert result.content[0].text == "No stale indexes among the 1 indexed projects on this machine."


async def test_list_indexes_without_a_derivable_store_keeps_the_legacy_fields(settings_env):
    """R01 §C1: the fake's default `--stats` projects do not exist on disk, so no
    `status` call can yield an `Index:` line; every store field stays `None`."""
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("list_indexes", {})

    assert result.structured_content["store_root"] is None
    for info in result.structured_content["indexes"]:
        assert info["size_bytes"] is None and info["stale"] is None and info["path_exists"] is None


# --- doctor ---------------------------------------------------------------------


async def test_doctor_ok(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("doctor", {})

    assert not result.is_error
    doc = result.structured_content
    assert doc["ok"] is True
    assert doc["problems"] == []
    assert doc["version"] == "colgrep 1.6.2"
    assert doc["colgrep_path"] is not None
    assert doc["root_source"] == "env"


async def test_doctor_bogus_binary(monkeypatch, tmp_path):
    monkeypatch.setenv("COLGREP_MCP_BINARY", "/no/such/colgrep-binary-xyz")
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))
    monkeypatch.setenv("COLGREP_MCP_TIMEOUT", "5")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("doctor", {})

    assert not result.is_error
    doc = result.structured_content
    assert doc["ok"] is False
    assert doc["colgrep_path"] is None
    assert doc["version"] is None
    assert any("not found" in p for p in doc["problems"])


async def test_doctor_reports_client_root_when_env_root_unset(monkeypatch, fake_colgrep_bin, tmp_path):
    """R01 §C2: `doctor` reports `default_root(settings, roots)` with the same
    lazily fetched client roots the path-taking tools would use, so its
    answer matches what a call without an explicit `path` will resolve to."""
    monkeypatch.setenv("COLGREP_MCP_BINARY", fake_colgrep_bin)
    monkeypatch.delenv("COLGREP_MCP_ROOT", raising=False)
    monkeypatch.setenv("COLGREP_MCP_TIMEOUT", "30")

    async def list_roots(context: object) -> ListRootsResult:
        return ListRootsResult(roots=[Root(uri=tmp_path.as_uri())])  # file:///C:/... on Windows

    # `roots/list` is a server-initiated back channel, which only
    # `mode="legacy"` negotiates under the 2026-07-28 protocol (same reason
    # `index_clear`'s elicitation tests below use it).
    async with Client(build(), raise_exceptions=True, list_roots_callback=list_roots, mode="legacy") as client:
        result = await client.call_tool("doctor", {})

    assert not result.is_error
    doc = result.structured_content
    assert doc["root_source"] == "roots"
    assert doc["default_root"] == str(tmp_path.resolve())


async def test_doctor_hints_at_a_stale_store(settings_env, housekeeping_store, fake_store):
    """R01 §C6: orphaned and machine-state indexes are a hint, not a problem — `ok` stays true."""
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("doctor", {})

    doc = result.structured_content
    assert doc["ok"] is True and doc["problems"] == []
    assert len(doc["hints"]) == 1
    hint = doc["hints"][0]
    assert hint.startswith(f"[{Code.INDEX_STORE_STALE}] 1 orphaned and 1 machine-state indexes (")
    assert str(fake_store.root) in hint
    assert hint.endswith(HINTS[Code.INDEX_STORE_STALE])
    assert f"hint: [{Code.INDEX_STORE_STALE}]" in result.content[0].text


async def test_doctor_no_hint_for_a_clean_store(settings_env, fake_store, tmp_path, monkeypatch):
    live = tmp_path / "live"
    (live / "sub").mkdir(parents=True)
    monkeypatch.setattr(tools_index.store, "machine_state_roots", lambda home: [])
    fake_store("live-0001", live, search_count=3)
    fake_store("sub-0002", live / "sub", search_count=3)  # shadowed: reported by list_indexes, not nagged about

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("doctor", {})

    assert result.structured_content["hints"] == []
    assert "hint:" not in result.content[0].text


async def test_doctor_hints_when_every_indexed_project_is_gone(settings_env):
    """The fake's default `--stats` names two projects that do not exist on disk."""
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("doctor", {})

    hints = result.structured_content["hints"]
    assert len(hints) == 1 and hints[0].startswith(f"[{Code.INDEX_STORE_UNKNOWN}] 2 indexed projects")


async def test_doctor_no_hint_on_a_machine_with_no_index(settings_env, fake_store):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("doctor", {})

    assert result.structured_content["hints"] == []


# --- index_build ------------------------------------------------------------------


async def test_index_build_reports_final_progress(settings_env, tmp_path):
    calls: list[tuple[float, float | None, str | None]] = []

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        calls.append((progress, total, message))

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_build", {"path": str(tmp_path)}, progress_callback=on_progress)

    assert not result.is_error
    assert len(calls) >= 1
    assert calls[-1][0] == 1
    assert calls[-1][1] == 1
    assert result.structured_content["added"] == 155
    assert result.structured_content["changed"] == 1


async def test_index_build_heartbeat_streams_while_slow(settings_env, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_SLEEP", "0.3")
    monkeypatch.setattr(tools_index, "HEARTBEAT_S", 0.05)

    calls: list[tuple[float, float | None, str | None]] = []

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        calls.append((progress, total, message))

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_build", {"path": str(tmp_path)}, progress_callback=on_progress)

    assert not result.is_error
    assert len(calls) >= 2
    # every heartbeat but the final one is indeterminate (total=None)
    assert any(total is None for _progress, total, _message in calls[:-1])


async def test_index_build_cancellation_reaps_init_task_and_subprocess(settings_env, tmp_path, monkeypatch):
    """F2: cancelling `index_build` while it's inside the heartbeat loop must
    not abandon the still-running `init()` task (and its colgrep subprocess).

    `asyncio.wait` (unlike `gather`) never propagates cancellation to the
    task it's waiting on, so the bare `try/except ColgrepError` around the
    loop let a cancellation drop straight through, leaving `task` (and the
    fake binary's process) running after the project lock had already been
    released by the `async with` exiting.
    """
    monkeypatch.setenv("FAKE_COLGREP_SLEEP", "5")
    monkeypatch.setattr(tools_index, "HEARTBEAT_S", 0.05)
    # `index_build` runs the actual subprocess through `adapter.with_stderr(...)`,
    # a *shallow copy* of `adapter` (by design, so the shared adapter's own
    # `on_stderr` is never mutated) — make it return `self` here so this
    # test can observe `_last_proc` on the same object it holds a reference to.
    monkeypatch.setattr(ColgrepAdapter, "with_stderr", lambda self, on_stderr: self)

    settings = Settings.from_env()
    adapter = ColgrepAdapter(binary=settings.binary, timeout_s=30)
    ctx = _StubCtx(adapter=adapter, settings=settings)

    build_task = asyncio.ensure_future(tools_index.index_build(str(tmp_path), ctx=ctx))
    await asyncio.sleep(0.2)
    build_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await build_task

    # The `init()` task's colgrep subprocess must have been killed and
    # reaped, not orphaned running in the background.
    assert adapter._last_proc is not None
    assert adapter._last_proc.returncode is not None


async def test_index_build_up_to_date(settings_env, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_UPTODATE", "1")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_build", {"path": str(tmp_path)})

    assert not result.is_error
    assert result.structured_content["up_to_date"] is True
    assert "up to date" in result.content[0].text


# --- index_clear --------------------------------------------------------------------


async def test_index_clear_project_mismatch_refused(settings_env, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_STATUS_PROJECT", "/tmp/some-ancestor-project")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path), "confirm": True})

    assert result.is_error
    text = result.content[0].text
    # SDK-wrapped as "Error executing tool index_clear: <message>", so the
    # coded prefix is present but not necessarily at index 0.
    assert f"[{Code.PROJECT_ROOT_MISMATCH}] " in text
    assert text.endswith(f"Next: {HINTS[Code.PROJECT_ROOT_MISMATCH]}")
    assert "/tmp/some-ancestor-project" in text


async def test_index_clear_without_confirm_and_no_elicitation_refused(settings_env, tmp_path):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path)})

    assert result.is_error
    text = result.content[0].text
    assert f"[{Code.CONFIRMATION_REQUIRED}] " in text
    assert text.endswith(f"Next: {HINTS[Code.CONFIRMATION_REQUIRED]}")
    assert "confirm=true" in text


async def test_index_clear_confirm_flag_runs_clear(settings_env, tmp_path, monkeypatch):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path), "confirm": True})

    assert not result.is_error
    assert result.structured_content["cleared"] is True
    argv = json.loads(argv_file.read_text())
    assert "clear" in argv


async def test_index_clear_elicitation_accept_runs_clear(settings_env, tmp_path, monkeypatch):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    async def accept(context: object, params: ElicitRequestParams) -> ElicitResult:
        return ElicitResult(action="accept", content={"confirm": True})

    # Classic request/response elicitation needs a server-initiated back
    # channel, which only `mode="legacy"` negotiates (R05 M3 / NoBackChannelError
    # under the 2026-07-28 protocol — see `index_clear`'s guarded try/except).
    async with Client(build(), raise_exceptions=True, elicitation_callback=accept, mode="legacy") as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path)})

    assert not result.is_error
    assert result.structured_content["cleared"] is True
    argv = json.loads(argv_file.read_text())
    assert "clear" in argv


async def test_index_clear_elicitation_failure_raises_confirmation_required(settings_env, tmp_path, monkeypatch):
    """F8: `ctx.elicit()` itself raising (e.g. `NoBackChannelError`) is not
    the same as the user declining — it must surface the same
    `CONFIRMATION_REQUIRED` coded refusal as "no elicitation capability",
    not the silent `cleared=False` "declined" text a real decline gets."""
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    async def failing(context: object, params: ElicitRequestParams) -> ElicitResult:
        raise RuntimeError("elicitation back channel exploded")

    async with Client(build(), raise_exceptions=True, elicitation_callback=failing, mode="legacy") as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path)})

    assert result.is_error
    text = result.content[0].text
    assert f"[{Code.CONFIRMATION_REQUIRED}] " in text
    assert text.endswith(f"Next: {HINTS[Code.CONFIRMATION_REQUIRED]}")
    argv = json.loads(argv_file.read_text())
    # only `status` ran; `clear` must not have.
    assert "clear" not in argv


async def test_index_clear_elicitation_decline_does_not_clear(settings_env, tmp_path, monkeypatch):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    async def decline(context: object, params: ElicitRequestParams) -> ElicitResult:
        return ElicitResult(action="decline")

    async with Client(build(), raise_exceptions=True, elicitation_callback=decline, mode="legacy") as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path)})

    assert not result.is_error
    assert result.structured_content["cleared"] is False
    assert "declined" in result.content[0].text
    argv = json.loads(argv_file.read_text())
    # only `status` ran; `clear` must not have.
    assert "clear" not in argv


# --- index_prune -----------------------------------------------------------------------


def _store_names(root):
    return sorted(p.name for p in root.iterdir() if p.is_dir())


async def test_index_prune_dry_run_groups_candidates_and_removes_nothing(settings_env, housekeeping_store, fake_store):
    """R01 §C5: the default call is a dry run over the three parameter-free classes."""
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_prune", {})

    assert not result.is_error
    sc = result.structured_content
    assert sc["dry_run"] is True and sc["pruned"] == [] and sc["failed"] == []
    assert sc["store_root"] == str(fake_store.root)
    kinds = {c["project"]: c["kind"] for c in sc["candidates"]}
    assert kinds == {
        str(housekeeping_store["gone"]): "orphaned",
        str(housekeeping_store["scratch"]): "machine_state",
        str(housekeeping_store["sub"]): "shadowed",
    }
    assert sc["total_bytes"] == sum(c["size_bytes"] for c in sc["candidates"]) > 3 * 1024
    assert _store_names(fake_store.root) == ["gone-0003", "live-0001", "old-0005", "scratch-0004", "sub-0002"]

    lines = result.content[0].text.splitlines()
    assert lines[0].startswith("3 prune candidates (")
    assert "orphaned (1, " in result.content[0].text
    assert "machine_state (1, " in result.content[0].text
    assert "shadowed (1, " in result.content[0].text
    assert f"  shadowed by {housekeeping_store['live']}" in result.content[0].text
    assert lines[-1] == (
        "Dry run: nothing removed. Call index_prune(dry_run=false, confirm=true, "
        'classes=["orphaned", "machine_state", "shadowed"]) to remove them.'
    )


async def test_index_prune_cold_is_opt_in(settings_env, housekeeping_store):
    async with Client(build(), raise_exceptions=True) as client:
        default = await client.call_tool("index_prune", {})
        cold = await client.call_tool("index_prune", {"classes": ["cold"]})
        cold_recent = await client.call_tool("index_prune", {"classes": ["cold"], "days": 60})
        cold_busy = await client.call_tool("index_prune", {"classes": ["cold"], "max_searches": 0})

    assert all("cold" != c["kind"] for c in default.structured_content["candidates"])
    assert [c["project"] for c in cold.structured_content["candidates"]] == [str(housekeeping_store["old"])]
    assert cold_recent.structured_content["candidates"] == []
    assert cold_busy.structured_content["candidates"] == []
    assert cold_recent.content[0].text.startswith("Nothing to prune in ")


async def test_index_prune_rejects_an_unknown_class(settings_env, housekeeping_store):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_prune", {"classes": ["live"]})
    assert result.is_error


async def test_index_prune_confirm_removes_only_the_candidates(settings_env, housekeeping_store, fake_store):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_prune", {"dry_run": False, "confirm": True})

    assert not result.is_error
    sc = result.structured_content
    assert sc["dry_run"] is False
    assert sorted(sc["pruned"]) == sorted(str(housekeeping_store[k]) for k in ("gone", "scratch", "sub"))
    assert sc["failed"] == []
    assert sc["freed_bytes"] == sc["total_bytes"] > 0
    assert _store_names(fake_store.root) == ["live-0001", "old-0005"]
    assert result.content[0].text.startswith("Pruned 3 of 3 indexes (")


async def test_index_prune_without_confirm_and_no_elicitation_refused(settings_env, housekeeping_store, fake_store):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_prune", {"dry_run": False})

    assert result.is_error
    text = result.content[0].text
    assert f"[{Code.CONFIRMATION_REQUIRED}] " in text
    assert text.endswith(f"Next: {HINTS[Code.CONFIRMATION_REQUIRED]}")
    assert len(_store_names(fake_store.root)) == 5


async def test_index_prune_elicitation_accept_removes(settings_env, housekeeping_store, fake_store):
    async def accept(context: object, params: ElicitRequestParams) -> ElicitResult:
        assert "Remove 3 colgrep indexes" in params.message
        return ElicitResult(action="accept", content={"confirm": True})

    async with Client(build(), raise_exceptions=True, elicitation_callback=accept, mode="legacy") as client:
        result = await client.call_tool("index_prune", {"dry_run": False})

    assert not result.is_error
    assert len(result.structured_content["pruned"]) == 3
    assert _store_names(fake_store.root) == ["live-0001", "old-0005"]


async def test_index_prune_elicitation_decline_removes_nothing(settings_env, housekeeping_store, fake_store):
    async def decline(context: object, params: ElicitRequestParams) -> ElicitResult:
        return ElicitResult(action="decline")

    async with Client(build(), raise_exceptions=True, elicitation_callback=decline, mode="legacy") as client:
        result = await client.call_tool("index_prune", {"dry_run": False})

    assert not result.is_error
    assert result.content[0].text == "Not pruned (declined)"
    assert result.structured_content["pruned"] == []
    assert len(_store_names(fake_store.root)) == 5


async def test_index_prune_nothing_to_prune_needs_no_confirmation(settings_env, fake_store, tmp_path, monkeypatch):
    live = tmp_path / "live"
    live.mkdir()
    monkeypatch.setattr(tools_index.store, "machine_state_roots", lambda home: [])
    fake_store("live-0001", live, search_count=3)

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_prune", {"dry_run": False})

    assert not result.is_error
    assert result.content[0].text.startswith("Nothing to prune in ")


async def test_index_prune_guard_refuses_a_directory_naming_another_project(
    settings_env, housekeeping_store, fake_store, monkeypatch
):
    """R01 §C5: the delete re-reads `project.json`; a candidate whose directory names a
    different project (a store that changed under us) lands in `failed` and stays."""
    real_read_store = tools_index.store.read_store
    live_dir = fake_store.root / "live-0001"

    def tampered(root):
        entries = real_read_store(root)
        # Point the orphan's candidate at the live project's directory.
        return [
            e if e.project != str(housekeeping_store["gone"]) else dataclasses.replace(e, index_dir=live_dir)
            for e in entries
        ]

    monkeypatch.setattr(tools_index.store, "read_store", tampered)

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_prune", {"dry_run": False, "confirm": True, "classes": ["orphaned"]})

    assert not result.is_error
    sc = result.structured_content
    assert sc["pruned"] == []
    assert len(sc["failed"]) == 1 and "project.json names" in sc["failed"][0]
    assert live_dir.is_dir()
    assert "failed: " in result.content[0].text


async def test_index_prune_without_a_derivable_store_is_a_coded_error(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_prune", {})

    assert result.is_error
    text = result.content[0].text
    assert f"[{Code.INDEX_STORE_UNKNOWN}] " in text
    assert text.endswith(f"Next: {HINTS[Code.INDEX_STORE_UNKNOWN]}")
