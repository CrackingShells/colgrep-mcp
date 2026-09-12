"""Tests for `colgrep_mcp.errors`: the coded `[CODE] ... Next: ...` shape every
deliberately-raised `ToolError`/`ResourceError` and every `SearchResult` note
must carry (roadmap leaf `error_taxonomy`; R01 §Error model; PI request
2026-09-12, mid-run: "standardized tool call error code that can point the
agents toward different usage patterns").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp import Client

from colgrep_mcp.adapter import ColgrepFailed, ColgrepNotFound, ColgrepParseError, ColgrepTimeout
from colgrep_mcp.errors import HINTS, Code, from_adapter_error, note, tool_error
from colgrep_mcp.server import build

pytestmark = pytest.mark.anyio


# --- the vocabulary itself ---------------------------------------------------


def test_code_enum_has_exactly_the_specified_members():
    assert {c.value for c in Code} == {
        "NO_HITS",
        "LIMIT_DEFAULT_APPLIED",
        "TEXT_TRUNCATED",
        "LOCATION_UNVERIFIED",
        "INDEX_COLD",
        "PATH_NOT_FOUND",
        "PROJECT_ROOT_MISMATCH",
        "CONFIRMATION_REQUIRED",
        "COLGREP_MISSING",
        "COLGREP_FAILED",
        "COLGREP_TIMEOUT",
        "BAD_HIT_ID",
    }


def test_hints_covers_every_code_with_a_nonempty_imperative_sentence():
    assert set(HINTS) == set(Code)
    for code, hint in HINTS.items():
        assert hint, code
        assert hint[0].isupper(), f"{code} hint should read as an imperative sentence: {hint!r}"


def test_tool_error_is_coded_detail_next_hint():
    err = tool_error(Code.BAD_HIT_ID, "malformed hit_id: 'x'")
    text = str(err)
    assert text.startswith(f"[{Code.BAD_HIT_ID}] ")
    assert text.endswith(f"Next: {HINTS[Code.BAD_HIT_ID]}")
    assert "malformed hit_id" in text


def test_note_with_detail_carries_only_the_code_prefix():
    assert note(Code.NO_HITS, "no units matched") == f"[{Code.NO_HITS}] no units matched"


def test_note_without_detail_falls_back_to_the_hint():
    assert note(Code.NO_HITS) == f"[{Code.NO_HITS}] {HINTS[Code.NO_HITS]}"


# --- from_adapter_error: pure mapping (R01 §Error model; R05 D6) ------------


def test_from_adapter_error_not_found_maps_to_colgrep_missing():
    text = str(from_adapter_error(ColgrepNotFound("colgrep")))
    assert text.startswith(f"[{Code.COLGREP_MISSING}]")
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_MISSING]}")


def test_from_adapter_error_timeout_maps_to_colgrep_timeout_naming_index_build():
    text = str(from_adapter_error(ColgrepTimeout("colgrep timed out after 30s: search x")))
    assert text.startswith(f"[{Code.COLGREP_TIMEOUT}]")
    assert "index_build" in text  # COLGREP_TIMEOUT's own hint names it, no separate INDEX_COLD needed
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_TIMEOUT]}")


def test_from_adapter_error_path_does_not_exist_stderr_maps_to_path_not_found():
    exc = ColgrepFailed(
        1,
        "Error: Path does not exist: /nope\nClosest existing directory: /\nContents: a, b",
        ["status", "/nope"],
    )
    text = str(from_adapter_error(exc))
    assert text.startswith(f"[{Code.PATH_NOT_FOUND}]")
    assert "Closest existing directory" in text  # colgrep's own hint, kept verbatim (R05 D6)
    assert text.endswith(f"Next: {HINTS[Code.PATH_NOT_FOUND]}")


def test_from_adapter_error_other_failure_maps_to_colgrep_failed():
    exc = ColgrepFailed(2, "error: forced failure", ["search", "--json", "x"])
    text = str(from_adapter_error(exc))
    assert text.startswith(f"[{Code.COLGREP_FAILED}]")
    assert "forced failure" in text
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_FAILED]}")


def test_from_adapter_error_parse_error_maps_to_colgrep_failed():
    text = str(from_adapter_error(ColgrepParseError("bad json", "not json")))
    assert text.startswith(f"[{Code.COLGREP_FAILED}]")
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_FAILED]}")


# --- end-to-end: every tool failure path through the fake binary ------------


async def test_search_missing_binary_is_coded_colgrep_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("COLGREP_MCP_BINARY", "/no/such/colgrep-binary-xyz")
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))
    monkeypatch.setenv("COLGREP_MCP_TIMEOUT", "5")

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x"})

    assert r.is_error is True
    text = r.content[0].text
    # The SDK wraps every raised `ToolError` as "Error executing tool <name>: <message>"
    # (`mcp.server.mcpserver.tools.base.Tool.run`), so the coded prefix is present but
    # not necessarily at index 0 — only a `ToolError`/`ResourceError` built directly
    # from `errors.py` (tested above, unwrapped) is asserted with `.startswith`.
    assert f"[{Code.COLGREP_MISSING}] " in text
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_MISSING]}")


async def test_search_colgrep_exit_is_coded_colgrep_failed(settings_env, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_EXIT", "2")

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x"})

    assert r.is_error is True
    text = r.content[0].text
    assert f"[{Code.COLGREP_FAILED}] " in text
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_FAILED]}")


async def test_search_timeout_is_coded_colgrep_timeout(monkeypatch, tmp_path, fake_colgrep_bin):
    monkeypatch.setenv("COLGREP_MCP_BINARY", fake_colgrep_bin)
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))
    monkeypatch.setenv("COLGREP_MCP_TIMEOUT", "0.2")
    monkeypatch.setenv("FAKE_COLGREP_SLEEP", "2")

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x"})

    assert r.is_error is True
    text = r.content[0].text
    assert f"[{Code.COLGREP_TIMEOUT}] " in text
    assert "index_build" in text
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_TIMEOUT]}")


async def test_search_bad_path_is_coded_path_not_found(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x", "paths": ["/nonexistent/nope"]})

    assert r.is_error is True
    text = r.content[0].text
    assert f"[{Code.PATH_NOT_FOUND}] " in text
    assert "/nonexistent/nope" in text
    assert text.endswith(f"Next: {HINTS[Code.PATH_NOT_FOUND]}")


async def test_expand_malformed_hit_id_is_coded_bad_hit_id(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": ["not-a-valid-hit-id"]})

    assert r.is_error is False  # expand itself succeeds; the failure is per-unit
    error = r.structured_content["units"][0]["error"]
    assert error.startswith(f"[{Code.BAD_HIT_ID}] ")
    assert error.endswith(f"Next: {HINTS[Code.BAD_HIT_ID]}")


async def test_index_clear_project_mismatch_is_coded_project_root_mismatch(settings_env, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_STATUS_PROJECT", "/tmp/some-ancestor-project")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path), "confirm": True})

    assert result.is_error
    text = result.content[0].text
    assert f"[{Code.PROJECT_ROOT_MISMATCH}] " in text
    assert "/tmp/some-ancestor-project" in text
    assert text.endswith(f"Next: {HINTS[Code.PROJECT_ROOT_MISMATCH]}")


async def test_index_clear_without_confirm_is_coded_confirmation_required(settings_env, tmp_path):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_clear", {"path": str(tmp_path)})

    assert result.is_error
    text = result.content[0].text
    assert f"[{Code.CONFIRMATION_REQUIRED}] " in text
    assert "confirm=true" in text
    assert text.endswith(f"Next: {HINTS[Code.CONFIRMATION_REQUIRED]}")


async def test_index_status_missing_binary_is_coded_colgrep_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("COLGREP_MCP_BINARY", "/no/such/colgrep-binary-xyz")
    monkeypatch.setenv("COLGREP_MCP_ROOT", str(tmp_path))
    monkeypatch.setenv("COLGREP_MCP_TIMEOUT", "5")

    async with Client(build(), raise_exceptions=True) as client:
        result = await client.call_tool("index_status", {"path": str(tmp_path)})

    assert result.is_error
    text = result.content[0].text
    assert f"[{Code.COLGREP_MISSING}] " in text
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_MISSING]}")


# --- notes: SearchResult degraded-success codes (never raised, never spammed) -


async def test_search_zero_hits_note_is_coded_no_hits(settings_env, monkeypatch, tmp_path):
    empty_fixture = tmp_path / "empty.json"
    empty_fixture.write_text("[]")
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(empty_fixture))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "nothing matches this"})

    assert r.is_error is False
    assert any(n.startswith(f"[{Code.NO_HITS}]") for n in r.structured_content["notes"])


async def test_search_limit_none_without_pattern_note_is_coded_limit_default_applied(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x", "limit": None})

    assert any(n.startswith(f"[{Code.LIMIT_DEFAULT_APPLIED}]") for n in r.structured_content["notes"])


async def test_search_limit_none_with_pattern_has_no_limit_default_note(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x", "limit": None, "pattern": "def "})

    assert not any(n.startswith(f"[{Code.LIMIT_DEFAULT_APPLIED}]") for n in r.structured_content["notes"])


async def test_search_location_unverified_note_appears_once_per_result_not_per_hit(settings_env, monkeypatch, tmp_path):
    target = tmp_path / "stale_source.py"
    target.write_text("# this file no longer contains the indexed units\n")

    fixture = [
        {
            "unit": {
                "name": f"vanished_{i}",
                "qualified_name": f"stale_source.py::vanished_{i}",
                "file": str(target),
                "line": 7,
                "end_line": 9,
                "language": "python",
                "unit_type": "function",
                "signature": "def vanished()",
                "code": "def vanished():\n    return 0",
            },
            "score": 1.0,
        }
        for i in range(3)
    ]
    fixture_path = tmp_path / "unverified_hits.json"
    fixture_path.write_text(json.dumps(fixture))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "vanished"})

    assert len(r.structured_content["hits"]) == 3
    location_notes = [n for n in r.structured_content["notes"] if n.startswith(f"[{Code.LOCATION_UNVERIFIED}]")]
    assert len(location_notes) == 1


async def test_search_text_truncated_note_when_renderer_caps_the_text(settings_env, monkeypatch, tmp_path):
    hits = [
        {
            "unit": {
                "name": f"unit_{i}",
                "qualified_name": f"mod{i}.py::unit_{i}",
                "file": f"/tmp/fake-corpus/mod{i}.py",
                "line": 1,
                "end_line": 2,
                "language": "python",
                "unit_type": "function",
                "signature": f"def unit_{i}()",
                "code": f"def unit_{i}():\n    return {i}\n",
            },
            "score": round(1.0 - i * 0.0001, 6),
        }
        for i in range(200)
    ]
    fixture_path = tmp_path / "hits_large.json"
    fixture_path.write_text(json.dumps(hits))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))
    monkeypatch.setenv("COLGREP_MCP_TEXT_BUDGET", "2000")

    async with Client(build(), raise_exceptions=True) as c:
        # `pattern` set so an omitted `limit` is a legitimate exhaustive search (R05 D5).
        r = await c.call_tool("search", {"query": "x", "limit": None, "pattern": "unit_"})

    assert r.structured_content["truncated"] is True
    assert any(n.startswith(f"[{Code.TEXT_TRUNCATED}]") for n in r.structured_content["notes"])


# --- the colgrep://errors resource -------------------------------------------


async def test_errors_resource_lists_every_code(settings_env):
    async with Client(build(), raise_exceptions=True) as client:
        result = await client.read_resource("colgrep://errors")

    assert result.contents[0].mime_type == "text/markdown"
    text = result.contents[0].text
    codes_in_text = set()
    for code in Code:
        assert f"`{code}`" in text
        assert HINTS[code] in text
        codes_in_text.add(code)
    assert codes_in_text == set(Code)


# --- translate_adapter_errors: the one wrapper tools put around adapter calls --


async def test_translate_adapter_errors_catches_the_base_class():
    from mcp.server.mcpserver.exceptions import ToolError

    from colgrep_mcp.adapter import ColgrepError
    from colgrep_mcp.errors import translate_adapter_errors

    # A bare ColgrepError (the adapter's own argument guards) must come out
    # coded, not as an uncoded generic error.
    with pytest.raises(ToolError) as e:
        async with translate_adapter_errors():
            raise ColgrepError("query must not start with '-'")
    assert str(e.value).startswith(f"[{Code.COLGREP_FAILED}]")
    assert str(e.value).endswith(f"Next: {HINTS[Code.COLGREP_FAILED]}")

    with pytest.raises(ToolError) as e:
        async with translate_adapter_errors(path=Path("/proj")):
            raise ColgrepTimeout("colgrep timed out after 1s")
    assert str(e.value).startswith(f"[{Code.COLGREP_TIMEOUT}]") and "(/proj)" in str(e.value)

    # Non-adapter exceptions pass through untouched.
    with pytest.raises(ValueError):
        async with translate_adapter_errors():
            raise ValueError("unrelated")
