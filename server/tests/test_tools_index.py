"""Tests for the index management tools (R01 §Tools; R05 D2, D3; roadmap leaf `index_tools`).

Step 1 covers the read-only tools (`index_status`, `list_indexes`, `doctor`).
Step 2 extends this file with `index_build` (heartbeat progress) and
`index_clear` (project-root refusal + elicitation-guarded confirmation).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp import Client

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
