"""Tests for the index management tools (R01 §Tools; R05 D2, D3; roadmap leaf `index_tools`).

Step 1 covers the read-only tools (`index_status`, `list_indexes`, `doctor`).
Step 2 extends this file with `index_build` (heartbeat progress) and
`index_clear` (project-root refusal + elicitation-guarded confirmation).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp import Client
from mcp.types import ElicitRequestParams, ElicitResult

from colgrep_mcp import tools_index
from colgrep_mcp.server import build

pytestmark = pytest.mark.anyio


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
    assert "/tmp/some-ancestor-project" in result.content[0].text


async def test_index_clear_without_confirm_and_no_elicitation_refused(settings_env, tmp_path):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path)})

    assert result.is_error
    assert "confirm=true" in result.content[0].text


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
