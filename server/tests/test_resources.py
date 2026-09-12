"""Tests for `colgrep_mcp.resources` (roadmap leaf `resources_prompts`, step 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fixture_paths import FAKE_CORPUS, FAKE_NEVER_INDEXED
from mcp import Client

from colgrep_mcp.errors import HINTS, Code
from colgrep_mcp.resources import _normalize_status_path
from colgrep_mcp.server import build

pytestmark = pytest.mark.anyio

# `FAKE_CORPUS`/`FAKE_NEVER_INDEXED` are already absolute (POSIX: "/tmp/...",
# Windows: "C:/tmp/..."); the "bare" forms below are what a client would put
# in the URI's `{+path}` segment for the "no leading slash" tests, i.e. the
# same literal with any leading `/` stripped off (a no-op on Windows, which
# never had one).
_CORPUS_BARE = FAKE_CORPUS.lstrip("/")
_NEVER_INDEXED_BARE = FAKE_NEVER_INDEXED.lstrip("/")


def test_normalize_status_path_accepts_with_and_without_leading_slash():
    # Compare `Path` objects, not `str()` renderings: `str(Path("/tmp/proj"))`
    # is already OS-native (`\tmp\proj` on Windows), so a POSIX-only string
    # literal isn't the right expectation on every OS.
    assert _normalize_status_path("tmp/proj") == Path("/tmp/proj")
    assert _normalize_status_path("/tmp/proj") == Path("/tmp/proj")


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


async def test_guide_is_read_once(settings_env, monkeypatch):
    """`guide()` is `functools.cache`d: the packaged file is read once per
    process no matter how many times `colgrep://guide` is requested."""
    from colgrep_mcp import resources as resources_module

    resources_module._guide_text.cache_clear()
    calls = {"n": 0}
    real_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        calls["n"] += 1
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    async with Client(build(), raise_exceptions=True) as client:
        first = await client.read_resource("colgrep://guide")
        second = await client.read_resource("colgrep://guide")

    assert first.contents[0].text == second.contents[0].text
    assert calls["n"] == 1


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
    expected = str(_normalize_status_path(_CORPUS_BARE))
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource(f"colgrep://status/{_CORPUS_BARE}")
        data = json.loads(result.contents[0].text)
        assert data["project"] == expected
        assert data["indexed"] is True
        assert data["requested_path"] == expected


async def test_read_status_with_leading_slash(settings_env):
    expected = str(_normalize_status_path(_CORPUS_BARE))
    async with Client(build(), raise_exceptions=True) as client:
        # {+path} keeps the inner slash, so a leading '/' arrives as a second
        # slash right after "status/"; the handler must accept both forms.
        result = await client.read_resource(f"colgrep://status//{_CORPUS_BARE}")
        data = json.loads(result.contents[0].text)
        assert data["project"] == expected
        assert data["indexed"] is True


async def test_status_not_indexed(settings_env, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_INDEXED", "0")
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource(f"colgrep://status/{_NEVER_INDEXED_BARE}")
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
