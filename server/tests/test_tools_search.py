"""End-to-end tests for the `search`, `find_files` and `expand` tools, through
`Client(build())` against the fake colgrep binary (R01 §Tools, §Error model,
§Token-budget invariant; R05 D1, D5, D7)."""

from __future__ import annotations

import asyncio
import builtins
import json
import threading
from pathlib import Path

import pytest
from fixture_paths import FAKE_CORPUS
from mcp import Client

from colgrep_mcp import tools_search
from colgrep_mcp.errors import HINTS, Code
from colgrep_mcp.locks import project_lock
from colgrep_mcp.models import ExpandResult, FileResult, SearchResult
from colgrep_mcp.server import build
from colgrep_mcp.tools_search import _fill_file_cache

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


# --- input validation bounds (F12) ------------------------------------------


async def test_search_rejects_non_positive_limit(settings_env):
    async with Client(build(), raise_exceptions=False) as c:
        r = await c.call_tool("search", {"query": "x", "limit": 0})

    assert r.is_error is True
    assert "limit" in r.content[0].text


async def test_search_rejects_alpha_out_of_range(settings_env):
    async with Client(build(), raise_exceptions=False) as c:
        r = await c.call_tool("search", {"query": "x", "alpha": 1.5})

    assert r.is_error is True
    assert "alpha" in r.content[0].text


async def test_search_rejects_negative_snippet_lines(settings_env):
    async with Client(build(), raise_exceptions=False) as c:
        r = await c.call_tool("search", {"query": "x", "snippet_lines": -1})

    assert r.is_error is True
    assert "snippet_lines" in r.content[0].text


async def test_find_files_rejects_non_positive_limit(settings_env):
    async with Client(build(), raise_exceptions=False) as c:
        r = await c.call_tool("find_files", {"query": "x", "limit": -5})

    assert r.is_error is True
    assert "limit" in r.content[0].text


async def test_expand_rejects_non_positive_max_lines(settings_env, tmp_path):
    target = tmp_path / "code.py"
    target.write_text("x = 1\n")

    async with Client(build(), raise_exceptions=False) as c:
        r = await c.call_tool("expand", {"hit_ids": [f"{target}:1-1"], "max_lines": 0})

    assert r.is_error is True
    assert "max_lines" in r.content[0].text


async def test_search_resolves_relative_unit_file_against_first_search_path(settings_env, tmp_path, monkeypatch):
    """F13: colgrep is documented to always emit an absolute `unit.file`, but
    if it ever emitted a relative one, `hit_id` must still be built from an
    absolute path — resolved against the first search path — rather than a
    relative `hit_id` that `expand` would then resolve against the server
    process's own cwd instead of the searched project."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "mod.py").write_text("def real_func():\n    return 42\n")

    fixture = [
        {
            "unit": {
                "name": "real_func",
                "qualified_name": "mod.py::real_func",
                "file": "mod.py",  # relative — not what colgrep is documented to emit, but defend anyway
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
    fixture_path = tmp_path / "hits.json"
    fixture_path.write_text(json.dumps(fixture))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "real func", "paths": [str(proj)]})
        hit = r.structured_content["hits"][0]
        assert Path(hit["file"]).is_absolute()

        expand_r = await c.call_tool("expand", {"hit_ids": [hit["hit_id"]]})

    unit = expand_r.structured_content["units"][0]
    assert unit["error"] is None
    assert "real_func" in (unit["code"] or "")


# --- concurrency (R01 §Concurrency invariant) --------------------------------


async def test_search_locks_every_resolved_path_not_only_the_first(settings_env, tmp_path, monkeypatch):
    """F6: a multi-path search must serialise against *every* project it
    touches, not only `resolved[0]` — otherwise a concurrent `index_build`
    (or another search) on the second path races the in-flight search."""
    monkeypatch.setenv("FAKE_COLGREP_SLEEP", "0.3")
    proj_a = tmp_path / "a"
    proj_a.mkdir()
    proj_b = tmp_path / "b"
    proj_b.mkdir()

    async with Client(build(), raise_exceptions=True) as c:
        search_task = asyncio.ensure_future(
            c.call_tool("search", {"query": "x", "paths": [str(proj_a), str(proj_b)]})
        )
        await asyncio.sleep(0.05)  # let _do_search acquire its lock(s) and start the slow adapter call

        async def _acquire_and_release(path):
            async with project_lock(path):
                pass

        # The second path must be locked too — acquiring it directly here,
        # while the search above is still in flight, must block.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_acquire_and_release(proj_b.resolve()), timeout=0.1)

        result = await search_task

    assert not result.is_error


# --- find_files ---------------------------------------------------------


async def test_find_files_groups_hits_by_file_preserving_score_order(settings_env):
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("find_files", {"query": "config parsing"})

    assert r.is_error is False
    FileResult.model_validate(r.structured_content)
    files = r.structured_content["files"]
    by_file = {f["file"]: f for f in files}

    # hits_small.json hard-codes its hit files under the "/tmp/fake-corpus"
    # stand-in project; `fake_colgrep.py` swaps that for `FAKE_CORPUS` before
    # printing (the literal is only genuinely absolute, and so left
    # unrebased by `_resolve_hit_file`, on POSIX — see `fixture_paths.py`).
    config_py = f"{FAKE_CORPUS}/src/config.py"
    readme = f"{FAKE_CORPUS}/README.md"
    assert by_file[config_py]["hits"] == 2
    assert by_file[config_py]["best_score"] == pytest.approx(1.4321)
    assert set(by_file[config_py]["top_units"]) == {"parse_config", "Settings"}
    assert by_file[readme]["hits"] == 1
    # Score-descending: config.py's best hit outranks README's only hit.
    assert [f["file"] for f in files][0] == config_py


async def test_find_files_does_not_read_hit_files(settings_env, monkeypatch):
    """R01 §C5 (Step 3): `find_files` never exposes `line`/`hit_id`, so `_do_search`
    must call it with `locate=False` and skip `_fill_file_cache` entirely — that
    used to cost up to 300 file reads (plus a `locate_unit` pass each) per call
    for output nothing downstream reads."""
    calls: list[None] = []
    real_fill_file_cache = tools_search._fill_file_cache

    async def spy(*args: object, **kwargs: object) -> None:
        calls.append(None)
        return await real_fill_file_cache(*args, **kwargs)

    monkeypatch.setattr(tools_search, "_fill_file_cache", spy)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("find_files", {"query": "config parsing"})

    assert r.is_error is False
    assert calls == []


# --- off-loop file I/O (F11) --------------------------------------------


def _spy_on_read_text(monkeypatch) -> list[int]:
    """Record the thread identity `Path.read_text` actually runs on."""
    thread_ids: list[int] = []
    real_read_text = Path.read_text

    def spy(self: Path, *args: object, **kwargs: object) -> str:
        thread_ids.append(threading.get_ident())
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    return thread_ids


def _spy_on_open(monkeypatch) -> list[int]:
    """Record the thread identity the builtin `open` (what `_read_span` uses) runs on."""
    thread_ids: list[int] = []
    real_open = builtins.open

    def spy(*args: object, **kwargs: object):
        thread_ids.append(threading.get_ident())
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    return thread_ids


async def test_search_reads_hit_files_off_the_event_loop(settings_env, tmp_path, monkeypatch):
    """F11: a hit's file is read via `asyncio.to_thread`, not directly on the
    event loop thread that is also running the rest of the server."""
    target = tmp_path / "real_source.py"
    target.write_text("def real_func():\n    return 42\n")

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
    fixture_path = tmp_path / "hits.json"
    fixture_path.write_text(json.dumps(fixture))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))

    main_thread_id = threading.get_ident()
    read_thread_ids = _spy_on_read_text(monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "real func"})

    assert not r.is_error
    assert r.structured_content["hits"][0]["location_verified"] is True
    assert read_thread_ids  # the file was actually read
    assert all(tid != main_thread_id for tid in read_thread_ids)


async def test_fill_file_cache_reads_each_distinct_file_at_most_once(tmp_path, monkeypatch):
    """F11: the caching behaviour that used to live inside `hit_from_raw`
    (read each file at most once per call) now belongs to `_fill_file_cache`,
    the async helper that populates `file_cache` before `hit_from_raw` runs."""
    target = tmp_path / "config.py"
    target.write_text("def parse_config(path: str) -> dict:\n    return {}\n")

    read_calls: list[Path] = []
    real_read_text = Path.read_text

    def spy(self: Path, *args: object, **kwargs: object) -> str:
        read_calls.append(self)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)

    raw_hits = [
        {"unit": {"file": str(target)}, "score": 1.0},
        {"unit": {"file": str(target)}, "score": 0.5},  # same file, second hit
    ]
    file_cache: dict[str, str] = {}
    await _fill_file_cache(raw_hits, file_cache)

    assert file_cache[str(target)] == "def parse_config(path: str) -> dict:\n    return {}\n"
    assert len(read_calls) == 1  # only one actual read for two hits on the same file

    # Mutate the cache in place: a second call must trust it, not re-read.
    file_cache[str(target)] = "mutated"
    await _fill_file_cache(raw_hits, file_cache)
    assert len(read_calls) == 1
    assert file_cache[str(target)] == "mutated"


async def test_expand_reads_files_off_the_event_loop(settings_env, tmp_path, monkeypatch):
    """F11, mirrored for `expand`. `expand` reads its span via `_read_span`'s
    builtin `open` (Step 3), not `Path.read_text`, so the spy target follows."""
    target = tmp_path / "code.py"
    target.write_text("x = 1\ny = 2\ndef f():\n    return 1\nz = 3\n")
    hit_id = f"{target}:3-4"

    main_thread_id = threading.get_ident()
    read_thread_ids = _spy_on_open(monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": [hit_id]})

    assert not r.is_error
    assert r.structured_content["units"][0]["code"] == "def f():\n    return 1"
    assert read_thread_ids
    assert all(tid != main_thread_id for tid in read_thread_ids)


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
