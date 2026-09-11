"""Tests for `colgrep_mcp.resources` (roadmap leaf `resources_prompts`, step 1)."""

from __future__ import annotations

import json

import pytest
from mcp import Client

from colgrep_mcp.errors import HINTS, Code
from colgrep_mcp.resources import _normalize_status_path
from colgrep_mcp.server import build

pytestmark = pytest.mark.anyio


def test_normalize_status_path_accepts_with_and_without_leading_slash():
    assert str(_normalize_status_path("tmp/proj")) == "/tmp/proj"
    assert str(_normalize_status_path("/tmp/proj")) == "/tmp/proj"


async def test_list_resources_and_templates(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        resources = await client.list_resources()
        by_uri = {r.uri: r.mime_type for r in resources.resources}
        assert by_uri["colgrep://guide"] == "text/markdown"
        assert by_uri["colgrep://settings"] == "application/json"
        assert by_uri["colgrep://indexes"] == "application/json"
        assert by_uri["colgrep://errors"] == "text/markdown"

        templates = await client.list_resource_templates()
        assert [t.uri_template for t in templates.resource_templates] == ["colgrep://status/{+path}"]


async def test_read_guide(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource("colgrep://guide")
        text = result.contents[0].text
        assert "colgrep" in text.lower()
        assert result.contents[0].mime_type == "text/markdown"


async def test_read_settings(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource("colgrep://settings")
        data = json.loads(result.contents[0].text)
        assert data["model"].startswith("lightonai/LateOn-Code-edge")
        assert data["k"] == "25 (default)"


async def test_read_indexes(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource("colgrep://indexes")
        data = json.loads(result.contents[0].text)
        projects = {i["project"] for i in data["indexes"]}
        assert projects == {"/tmp/fake-corpus", "/tmp/other"}


async def test_read_status_without_leading_slash(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource("colgrep://status/tmp/fake-corpus")
        data = json.loads(result.contents[0].text)
        assert data["project"] == "/tmp/fake-corpus"
        assert data["indexed"] is True
        assert data["requested_path"] == "/tmp/fake-corpus"


async def test_read_status_with_leading_slash(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        # {+path} keeps the inner slash, so a leading '/' arrives as a second
        # slash right after "status/"; the handler must accept both forms.
        result = await client.read_resource("colgrep://status//tmp/fake-corpus")
        data = json.loads(result.contents[0].text)
        assert data["project"] == "/tmp/fake-corpus"
        assert data["indexed"] is True


async def test_status_not_indexed(settings_env, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_INDEXED", "0")
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource("colgrep://status/tmp/never-indexed")
        data = json.loads(result.contents[0].text)
        assert data["indexed"] is False


async def test_binary_missing_raises_resource_error(settings_env, monkeypatch):
    monkeypatch.setenv("COLGREP_MCP_BINARY", "/no/such/colgrep-binary")
    async with Client(build(), raise_exceptions=False) as client:
        with pytest.raises(Exception) as exc_info:
            await client.read_resource("colgrep://settings")
        text = str(exc_info.value)
        assert f"[{Code.COLGREP_MISSING}]" in text
        assert f"Next: {HINTS[Code.COLGREP_MISSING]}" in text
        assert "colgrep not found on PATH" in text


async def test_colgrep_failure_raises_resource_error(settings_env, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_EXIT", "1")
    async with Client(build(), raise_exceptions=False) as client:
        with pytest.raises(Exception) as exc_info:
            await client.read_resource("colgrep://indexes")
        text = str(exc_info.value)
        assert f"[{Code.COLGREP_FAILED}]" in text
        assert f"Next: {HINTS[Code.COLGREP_FAILED]}" in text
        assert "colgrep exited 1" in text


async def test_read_errors_resource_lists_every_code(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource("colgrep://errors")

    assert result.contents[0].mime_type == "text/markdown"
    text = result.contents[0].text
    for code in Code:
        assert f"`{code}`" in text
        assert HINTS[code] in text
