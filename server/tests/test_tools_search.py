"""End-to-end tests for the `search`, `find_files` and `expand` tools, through
`Client(build())` against the fake colgrep binary (R01 §Tools, §Error model,
§Token-budget invariant; R05 D1, D5, D7)."""

from __future__ import annotations

import json

import pytest
from mcp import Client

from colgrep_mcp.errors import HINTS, Code
from colgrep_mcp.models import ExpandResult, FileResult, SearchResult
from colgrep_mcp.server import build

pytestmark = pytest.mark.anyio


# --- search: shape, argv, error translation ---------------------------------


async def test_search_text_and_structured_shape(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "config parsing"})

    assert r.is_error is False
    SearchResult.model_validate(r.structured_content)  # raises if the shape is wrong
    assert r.structured_content["total"] == 3
    assert len(r.structured_content["hits"]) == 3
    assert 'hits for "config parsing"' in r.content[0].text
    assert r.structured_content["index_updated"] is False


async def test_search_limit_none_omits_k_flag(settings_env, monkeypatch, tmp_path):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x", "limit": None, "pattern": "def "})

    argv = json.loads(argv_file.read_text())
    assert "-k" not in argv
    assert not any(n.startswith(f"[{Code.LIMIT_DEFAULT_APPLIED}]") for n in r.structured_content["notes"])


async def test_search_limit_none_without_pattern_appends_d5_note(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x", "limit": None})

    assert any(n.startswith(f"[{Code.LIMIT_DEFAULT_APPLIED}]") for n in r.structured_content["notes"])


async def test_search_pattern_and_include_flags_reach_argv(settings_env, monkeypatch, tmp_path):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    async with Client(build(), raise_exceptions=True) as c:
        await c.call_tool(
            "search",
            {
                "query": "x",
                "pattern": "foo",
                "include": ["*.py"],
                "exclude_dir": ["node_modules"],
                "case_sensitive": True,
            },
        )

    argv = json.loads(argv_file.read_text())
    assert argv[argv.index("-e") + 1] == "foo"
    assert argv[argv.index("--include") + 1] == "*.py"
    assert argv[argv.index("--exclude-dir") + 1] == "node_modules"
    assert "-s" in argv


async def test_search_bad_path_is_tool_error_listing_the_path(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x", "paths": ["/nonexistent/nope"]})

    assert r.is_error is True
    text = r.content[0].text
    # SDK-wrapped as "Error executing tool search: <message>", so the coded
    # prefix is present but not necessarily at index 0.
    assert f"[{Code.PATH_NOT_FOUND}] " in text
    assert text.endswith(f"Next: {HINTS[Code.PATH_NOT_FOUND]}")
    assert "/nonexistent/nope" in text


async def test_search_colgrep_exit_2_surfaces_as_tool_error_text(settings_env, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_EXIT", "2")

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "x"})

    assert r.is_error is True
    text = r.content[0].text
    assert f"[{Code.COLGREP_FAILED}] " in text
    assert text.endswith(f"Next: {HINTS[Code.COLGREP_FAILED]}")
    assert "colgrep exited 2" in text
    assert "forced failure" in text


async def test_search_zero_hits_is_not_an_error(settings_env, monkeypatch, tmp_path):
    empty_fixture = tmp_path / "empty.json"
    empty_fixture.write_text("[]")
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(empty_fixture))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "nothing matches this"})

    assert r.is_error is False
    assert r.structured_content["hits"] == []
    assert r.structured_content["notes"][0].startswith(f"[{Code.NO_HITS}]")
    assert "no units matched" in r.structured_content["notes"][0]
    assert "no units matched" in r.content[0].text


# --- find_files ---------------------------------------------------------


async def test_find_files_groups_hits_by_file_preserving_score_order(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("find_files", {"query": "config parsing"})

    assert r.is_error is False
    FileResult.model_validate(r.structured_content)
    files = r.structured_content["files"]
    by_file = {f["file"]: f for f in files}

    assert by_file["/tmp/fake-corpus/src/config.py"]["hits"] == 2
    assert by_file["/tmp/fake-corpus/src/config.py"]["best_score"] == pytest.approx(1.4321)
    assert set(by_file["/tmp/fake-corpus/src/config.py"]["top_units"]) == {"parse_config", "Settings"}
    assert by_file["/tmp/fake-corpus/README.md"]["hits"] == 1
    # Score-descending: config.py's best hit outranks README's only hit.
    assert [f["file"] for f in files][0] == "/tmp/fake-corpus/src/config.py"


# --- expand ---------------------------------------------------------------


async def test_expand_happy_path_reads_exact_span(settings_env, tmp_path):
    target = tmp_path / "code.py"
    target.write_text("x = 1\ny = 2\ndef f():\n    return 1\nz = 3\n")
    hit_id = f"{target}:3-4"

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": [hit_id]})

    assert r.is_error is False
    result = ExpandResult.model_validate(r.structured_content)
    unit = result.units[0]
    assert unit.error is None
    assert unit.code == "def f():\n    return 1"
    assert unit.truncated is False
    assert f"```{hit_id}" in r.content[0].text


async def test_expand_truncates_to_max_lines(settings_env, tmp_path):
    target = tmp_path / "code.py"
    target.write_text("\n".join(f"line{i}" for i in range(1, 11)) + "\n")
    hit_id = f"{target}:1-10"

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": [hit_id], "max_lines": 3})

    unit = r.structured_content["units"][0]
    assert unit["truncated"] is True
    assert unit["code"] == "line1\nline2\nline3"


async def test_expand_missing_file_yields_per_unit_error_not_a_tool_error(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": ["/nonexistent/does_not_exist.py:1-2"]})

    assert r.is_error is False  # the tool call itself succeeds
    unit = r.structured_content["units"][0]
    assert unit["error"] is not None
    assert unit["code"] is None


async def test_expand_malformed_hit_id_yields_per_unit_error(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": ["not-a-valid-hit-id"]})

    assert r.is_error is False
    unit = r.structured_content["units"][0]
    assert unit["error"].startswith(f"[{Code.BAD_HIT_ID}] ")
    assert unit["error"].endswith(f"Next: {HINTS[Code.BAD_HIT_ID]}")
    assert "malformed" in unit["error"]


# --- location_verified (R05 D1) -------------------------------------------


async def test_search_location_verified_true_when_file_contains_the_code(settings_env, monkeypatch, tmp_path):
    target = tmp_path / "real_source.py"
    # The real definition sits at line 4-5; colgrep will (wrongly) report line 1.
    target.write_text("# header\n# more header\n\ndef real_func():\n    return 42\n")

    fixture = [
        {
            "unit": {
                "name": "real_func",
                "qualified_name": "real_source.py::real_func",
                "file": str(target),
                "line": 1,
                "end_line": 1,
                "language": "python",
                "unit_type": "function",
                "signature": "def real_func()",
                "code": "def real_func():\n    return 42",
            },
            "score": 1.0,
        }
    ]
    fixture_path = tmp_path / "verified_hits.json"
    fixture_path.write_text(json.dumps(fixture))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "real func"})

    hit = r.structured_content["hits"][0]
    assert hit["location_verified"] is True
    assert (hit["line"], hit["end_line"]) == (4, 5)
    assert hit["hit_id"] == f"{target}:4-5"


async def test_search_location_verified_false_when_file_lacks_the_code(settings_env, monkeypatch, tmp_path):
    target = tmp_path / "stale_source.py"
    target.write_text("# this file no longer contains the indexed unit\n")

    fixture = [
        {
            "unit": {
                "name": "vanished_func",
                "qualified_name": "stale_source.py::vanished_func",
                "file": str(target),
                "line": 7,
                "end_line": 9,
                "language": "python",
                "unit_type": "function",
                "signature": "def vanished_func()",
                "code": "def vanished_func():\n    return 0",
            },
            "score": 1.0,
        }
    ]
    fixture_path = tmp_path / "unverified_hits.json"
    fixture_path.write_text(json.dumps(fixture))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "vanished func"})

    hit = r.structured_content["hits"][0]
    assert hit["location_verified"] is False
    # Falls back to colgrep's (unverifiable) reported line/end_line verbatim.
    assert (hit["line"], hit["end_line"]) == (7, 9)
    assert hit["hit_id"] == f"{target}:7-9"


# --- token budget (R01 §Token-budget invariant) ----------------------------


async def test_search_text_budget_holds_for_a_2000_hit_fixture(settings_env, monkeypatch, tmp_path):
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
        for i in range(2000)
    ]
    fixture_path = tmp_path / "hits_large.json"
    fixture_path.write_text(json.dumps(hits))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))
    monkeypatch.setenv("COLGREP_MCP_TEXT_BUDGET", "3000")

    async with Client(build(), raise_exceptions=True) as c:
        # `pattern` set so an omitted `limit` is a legitimate exhaustive search (R05 D5).
        r = await c.call_tool("search", {"query": "x", "limit": None, "pattern": "unit_"})

    assert r.is_error is False
    SearchResult.model_validate(r.structured_content)
    assert r.structured_content["total"] == 2000
    assert len(r.structured_content["hits"]) == 2000  # structured_content is never truncated
    assert r.structured_content["truncated"] is True
    assert len(r.content[0].text) <= 3000
    assert "more hits in structured_content" in r.content[0].text
    assert any(n.startswith(f"[{Code.TEXT_TRUNCATED}]") for n in r.structured_content["notes"])
