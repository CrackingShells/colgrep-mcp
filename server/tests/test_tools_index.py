"""Tests for the index management tools (R01 §Tools; R05 D2, D3; roadmap leaf `index_tools`).

Step 1 covers the read-only tools (`index_status`, `list_indexes`, `doctor`).
Step 2 extends this file with `index_build` (heartbeat progress) and
`index_clear` (project-root refusal + elicitation-guarded confirmation).
"""

from __future__ import annotations

import asyncio
import json

import pytest
from mcp import Client
from mcp.types import ElicitRequestParams, ElicitResult, ListRootsResult, Root

from colgrep_mcp import tools_index
from colgrep_mcp.adapter import ColgrepAdapter
from colgrep_mcp.config import Settings
from colgrep_mcp.errors import HINTS, Code
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
        return ListRootsResult(roots=[Root(uri=f"file://{tmp_path}")])

    # `roots/list` is a server-initiated back channel, which only
    # `mode="legacy"` negotiates under the 2026-07-28 protocol (same reason
    # `index_clear`'s elicitation tests below use it).
    async with Client(build(), raise_exceptions=True, list_roots_callback=list_roots, mode="legacy") as client:
        result = await client.call_tool("doctor", {})

    assert not result.is_error
    doc = result.structured_content
    assert doc["root_source"] == "roots"
    assert doc["default_root"] == str(tmp_path.resolve())


# --- index_build ------------------------------------------------------------------


async def test_index_build_reports_final_progress(settings_env, tmp_path):
    calls: list[tuple[float, float | None, str | None]] = []

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        calls.append((progress, total, message))

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool(
            "index_build", {"path": str(tmp_path)}, progress_callback=on_progress
        )

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
        result = await client.call_tool(
            "index_build", {"path": str(tmp_path)}, progress_callback=on_progress
        )

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
