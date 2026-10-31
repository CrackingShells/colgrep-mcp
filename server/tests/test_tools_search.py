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
from colgrep_mcp.tools_search import _read_units, _Wanted

_FAKE_RAW_HIT = {
    "unit": {
        "name": "parse_config",
        "qualified_name": "config.py::parse_config",
        "file": "/tmp/fake-corpus/src/config.py",
        "line": 1,
        "end_line": 2,
        "language": "python",
        "unit_type": "function",
        "signature": "def parse_config()",
        "code": "def parse_config():\n    return {}\n",
    },
    "score": 1.0,
}


class _StderrInjectingAdapter:
    """Stand-in for `get_adapter(ctx).with_stderr(...)` that emits synthetic
    stderr lines before returning a canned raw-hit list, entirely in-process.

    `fake_colgrep.py`'s `search` subcommand never writes to stderr at all
    (only `init` does, see its module docstring) — real colgrep's `search`
    auto-indexes and can emit the same cold-build chatter on stderr (R05 D2),
    but the fake doesn't replicate that, and `fake_colgrep.py` is owned by no
    one this cycle (report, don't edit). This stand-in exercises the
    `on_stderr` wiring the way that real chatter would, without touching the
    fake or the real subprocess pipeline.
    """

    def __init__(self, stderr_lines: list[str]) -> None:
        self._stderr_lines = stderr_lines
        self._on_stderr = None

    def with_stderr(self, on_stderr):
        self._on_stderr = on_stderr
        return self

    async def search(self, req: object) -> list[dict]:
        for line in self._stderr_lines:
            if self._on_stderr is not None:
                await self._on_stderr(line)
        return [_FAKE_RAW_HIT]


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
        search_task = asyncio.ensure_future(c.call_tool("search", {"query": "x", "paths": [str(proj_a), str(proj_b)]}))
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
    """R01 §C5: `find_files` never exposes `line`/`hit_id`, so `_do_search`
    must skip `_read_units` entirely — that used to cost up to 300 file reads
    (plus a `locate_unit` pass each) per call for output nothing downstream
    reads."""
    calls: list[None] = []
    real_read_units = tools_search._read_units

    async def spy(*args: object, **kwargs: object) -> dict:
        calls.append(None)
        return await real_read_units(*args, **kwargs)

    monkeypatch.setattr(tools_search, "_read_units", spy)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("find_files", {"query": "config parsing"})

    assert r.is_error is False
    assert calls == []


async def test_find_files_never_builds_search_hits(settings_env, monkeypatch):
    """R01 §C6: `find_files` folds raw hits straight into `FileHit`s; it must
    never call `hit_from_raw` (which builds a discarded `SearchHit`/`hit_id`
    and does a wasted `locate_unit` pass) at all — not once per hit, as the
    pre-restructure `_do_search` did for every path including `locate=False`."""
    calls: list[None] = []
    real_hit_from_raw = tools_search.hit_from_raw

    def spy(*args: object, **kwargs: object):
        calls.append(None)
        return real_hit_from_raw(*args, **kwargs)

    monkeypatch.setattr(tools_search, "hit_from_raw", spy)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("find_files", {"query": "config parsing"})

    assert r.is_error is False
    assert calls == []


# --- off-loop file I/O (F11) --------------------------------------------


def _spy_on_read_text(monkeypatch) -> list[Path]:
    """Record every `Path.read_text` call: a whole-file read."""
    reads: list[Path] = []
    real_read_text = Path.read_text

    def spy(self: Path, *args: object, **kwargs: object) -> str:
        reads.append(self)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    return reads


def _spy_on_open(monkeypatch) -> list[int]:
    """Record the thread identity the builtin `open` (what `_read_spans` uses) runs on."""
    thread_ids: list[int] = []
    real_open = builtins.open

    def spy(*args: object, **kwargs: object):
        thread_ids.append(threading.get_ident())
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    return thread_ids


async def test_search_reads_hit_files_off_the_event_loop(settings_env, tmp_path, monkeypatch):
    """F11: a hit's file is read via `asyncio.to_thread`, not directly on the
    event loop thread that is also running the rest of the server. With colgrep's
    own range exact, the one span read is the whole of it (`open`, as `expand`)."""
    target = tmp_path / "real_source.py"
    target.write_text("def real_func():\n    return 42\n")

    fixture = [
        {
            "unit": {
                "name": "real_func",
                "qualified_name": "real_source.py::real_func",
                "file": str(target),
                "line": 1,
                "end_line": 2,
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
    read_thread_ids = _spy_on_open(monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "real func"})

    assert not r.is_error
    assert r.structured_content["hits"][0]["location_verified"] is True
    assert read_thread_ids  # the file was actually read
    assert all(tid != main_thread_id for tid in read_thread_ids)


async def test_read_units_reads_each_distinct_file_once_for_all_its_spans(tmp_path, monkeypatch):
    """F11: `_read_units` is the one async step before the pure builders: a file
    is opened once however many spans (and leaders) of it are wanted."""
    target = tmp_path / "config.py"
    target.write_text("def parse_config(path: str) -> dict:\n    return {}\n\nclass Settings:\n    k: int = 15\n")
    other = tmp_path / "other.py"
    other.write_text("x = 1\n")

    opened: list[str] = []
    real_open = builtins.open

    def spy(file: object, *args: object, **kwargs: object):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)

    wanted = _Wanted(
        spans={(1, 2), (4, 5)}, leaders=[((1, 2), ["def parse_config(path: str) -> dict:", "    return {}"])]
    )
    reads = await _read_units({str(target): wanted, str(other): _Wanted(spans={(1, 1)})})

    assert opened.count(str(target)) == 1
    assert reads[str(target)].spans == {
        (1, 2): ["def parse_config(path: str) -> dict:\n", "    return {}\n"],
        (4, 5): ["class Settings:\n", "    k: int = 15\n"],
    }
    assert reads[str(target)].text is None  # the leader held, so no whole-file read
    assert reads[str(other)].spans == {(1, 1): ["x = 1\n"]}


async def test_search_verifies_a_leader_by_its_span_without_reading_the_whole_file(settings_env, monkeypatch, tmp_path):
    notes, _ = _matches_corpus(tmp_path, monkeypatch)
    whole_reads = _spy_on_read_text(monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation"})

    assert all(h["location_verified"] for h in r.structured_content["hits"])
    assert whole_reads == []


async def test_search_reads_an_edited_file_whole_once_to_relocate_its_leader(settings_env, monkeypatch, tmp_path):
    notes, _ = _matches_corpus(tmp_path, monkeypatch, notes_text="new\nlines\n" + _NOTES)
    whole_reads = _spy_on_read_text(monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation"})

    assert f"{notes}:5-6" in [h["hit_id"] for h in r.structured_content["hits"]]
    assert whole_reads == [notes]


async def test_search_cut_reads_and_builds_only_the_surviving_units(settings_env, monkeypatch, tmp_path):
    notes, tools = _matches_corpus(tmp_path, monkeypatch)
    spans_read: list[set] = []
    real_read_spans = tools_search._read_spans

    def spy(file: str, spans):
        spans = list(spans)
        spans_read.append({(Path(file).name, *s) for s in spans})
        return real_read_spans(file, spans)

    monkeypatch.setattr(tools_search, "_read_spans", spy)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation", "limit": 2})

    assert [h["hit_id"] for h in r.structured_content["hits"]] == [f"{notes}:3-4", f"{tools}:1-2"]
    # Only the two survivors' ranges were read: the cut units' (6-7, 9-10) never were.
    assert sorted(span for group in spans_read for span in group) == [("notes.md", 3, 4), ("tools.py", 1, 2)]


async def test_expand_reads_files_off_the_event_loop(settings_env, tmp_path, monkeypatch):
    """F11, mirrored for `expand`. `expand` reads its span via `_read_spans`'s
    builtin `open`, not `Path.read_text`, so the spy target follows."""
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


async def test_expand_reads_a_file_once_for_all_its_ids_and_answers_in_input_order(settings_env, tmp_path, monkeypatch):
    target = tmp_path / "ten.txt"
    target.write_text("".join(f"line {n}\n" for n in range(1, 11)))
    opened: list[str] = []
    real_open = builtins.open

    def spy(file: object, *args: object, **kwargs: object):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)

    # Out of order, one span overlapping another, one not touching the rest.
    ids = [f"{target}:6-8", f"{target}:2-3", f"{target}:7-9", f"{target}:10-10"]
    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": ids})

    units = r.structured_content["units"]
    assert [u["hit_id"] for u in units] == ids
    assert [u["code"] for u in units] == [
        "line 6\nline 7\nline 8",
        "line 2\nline 3",
        "line 7\nline 8\nline 9",
        "line 10",
    ]
    assert opened.count(str(target)) == 1


async def test_expand_errors_stay_per_id_when_ids_share_a_file(settings_env, tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("only\n")
    missing = tmp_path / "missing.txt"
    ids = [f"{missing}:1-2", "not a hit id", f"{missing}:3-4", f"{real}:1-1"]

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": ids})

    units = r.structured_content["units"]
    assert [u["hit_id"] for u in units] == ids
    assert units[0]["error"].startswith(f"could not read {missing}")
    assert units[2]["error"].startswith(f"could not read {missing}")
    assert units[1]["error"].startswith(f"[{Code.BAD_HIT_ID}]")
    assert (units[3]["code"], units[3]["error"]) == ("only", None)


async def test_expand_returns_lines_without_their_terminators(settings_env, tmp_path):
    target = tmp_path / "crlf.txt"
    target.write_bytes(b"a\r\n\r\nb\r\nlast")

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("expand", {"hit_ids": [f"{target}:1-2", f"{target}:3-9"]})

    assert [u["code"] for u in r.structured_content["units"]] == ["a\n", "b\nlast"]


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


# --- colgrep 1.8.x `matches`: one hit per matched unit ----------------------

_NOTES = (
    "# Wave 05\n\n## Logistics\nRoutine scheduling.\n\n"
    "## Escalation\n- **PI decision:** switch to a subagent.\n\n## Closing\nWave closed.\n"
)


def _unit(file: Path, name: str, line: int, end_line: int, code: str, unit_type: str = "section") -> dict:
    return {
        "name": name,
        "qualified_name": f"{file.name}::{name}",
        "file": str(file),
        "line": line,
        "end_line": end_line,
        "language": "markdown" if unit_type == "section" else "python",
        "unit_type": unit_type,
        "signature": None,
        "code": code,
    }


def _match(line: int, end_line: int, name: str, score: float) -> dict:
    return {"line": line, "end_line": end_line, "name": name, "score": score}


def _matches_corpus(
    tmp_path: Path, monkeypatch, notes_text: str = _NOTES, notes_matches: list[dict] | None = None
) -> tuple[Path, Path]:
    """Literal colgrep 1.8.4+ results (one per file, best first): `notes.md` led by
    its `Logistics` section with `unit` widened over the three matched sections
    and `matches` listing each, then `tools.py` with its one function."""
    notes = tmp_path / "notes.md"
    notes.write_text(notes_text)
    tools = tmp_path / "tools.py"
    tools.write_text('def escalate():\n    return "subagent"\n')
    leader = _unit(notes, "Logistics", 3, 10, "## Logistics\nRoutine scheduling.\n")
    fixture = [
        {
            "unit": leader,
            "score": 1.2,
            "matches": notes_matches
            or [
                _match(3, 4, "Logistics", 1.2),
                _match(6, 7, "Escalation", 0.9),
                _match(9, 10, "Closing", 0.1),
            ],
        },
        {
            "unit": _unit(tools, "escalate", 1, 2, 'def escalate():\n    return "subagent"\n', "function"),
            "score": 1.0,
        },
    ]
    fixture_path = tmp_path / "matches_hits.json"
    fixture_path.write_text(json.dumps(fixture))
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(fixture_path))
    return notes, tools


async def test_search_yields_every_matched_unit_ranked_across_files(settings_env, monkeypatch, tmp_path):
    notes, tools = _matches_corpus(tmp_path, monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "PI decision on the escalation"})
        hits = r.structured_content["hits"]
        e = await c.call_tool("expand", {"hit_ids": [hits[2]["hit_id"]]})

    assert [h["hit_id"] for h in hits] == [f"{notes}:3-4", f"{tools}:1-2", f"{notes}:6-7", f"{notes}:9-10"]
    assert [h["score"] for h in hits] == pytest.approx([1.2, 1.0, 0.9, 0.1])
    assert all(h["location_verified"] for h in hits)
    assert r.structured_content["total"] == 4
    assert r.structured_content["truncated"] is False
    second = hits[2]
    assert (second["name"], second["unit_type"], second["language"]) == ("Escalation", "", "markdown")
    assert "PI decision" in second["snippet"]
    assert f"{notes}:6-7  score=0.90  Escalation\n" in r.content[0].text
    assert e.structured_content["units"][0]["code"] == "## Escalation\n- **PI decision:** switch to a subagent."


async def test_search_limit_counts_units_not_files(settings_env, monkeypatch, tmp_path):
    notes, tools = _matches_corpus(tmp_path, monkeypatch)
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "PI decision on the escalation", "limit": 2})

    argv = json.loads(argv_file.read_text())
    assert argv[argv.index("-k") + 1] == "2"
    assert [h["hit_id"] for h in r.structured_content["hits"]] == [f"{notes}:3-4", f"{tools}:1-2"]
    assert r.structured_content["truncated"] is True


async def test_search_other_units_unverified_when_file_moved_since_indexing(settings_env, monkeypatch, tmp_path):
    # Two lines added on top since indexing: the leader is re-located at 5-6,
    # so colgrep's ranges for the other sections no longer fit the file.
    notes, _ = _matches_corpus(tmp_path, monkeypatch, notes_text="new\nlines\n" + _NOTES)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "PI decision on the escalation"})

    by_id = {h["hit_id"]: h for h in r.structured_content["hits"]}
    assert by_id[f"{notes}:5-6"]["location_verified"] is True
    assert by_id[f"{notes}:6-7"]["location_verified"] is False
    assert by_id[f"{notes}:9-10"]["location_verified"] is False
    assert any(n.startswith(f"[{Code.LOCATION_UNVERIFIED}]") for n in r.structured_content["notes"])


async def test_find_files_counts_each_matched_unit(settings_env, monkeypatch, tmp_path):
    notes, tools = _matches_corpus(tmp_path, monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("find_files", {"query": "PI decision on the escalation"})

    files = r.structured_content["files"]
    assert [f["file"] for f in files] == [str(notes), str(tools)]
    assert (files[0]["hits"], files[0]["top_units"]) == (3, ["Logistics", "Escalation", "Closing"])
    assert (files[1]["hits"], files[1]["top_units"]) == (1, ["escalate"])


async def test_search_unit_after_an_edit_below_the_leader_is_unverified_without_text(
    settings_env, monkeypatch, tmp_path
):
    # A line added under the best section: the leader still sits at its own range,
    # but every later section has moved, so colgrep's ranges for them hold other lines.
    text = _NOTES.replace("Routine scheduling.\n", "Routine scheduling.\nAdded.\n")
    notes, _ = _matches_corpus(tmp_path, monkeypatch, notes_text=text)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation", "include_code": True})

    by_id = {h["hit_id"]: h for h in r.structured_content["hits"]}
    assert by_id[f"{notes}:3-4"]["location_verified"] is True
    for stale in (f"{notes}:6-7", f"{notes}:9-10"):
        assert by_id[stale]["location_verified"] is False
        assert by_id[stale]["snippet"] is None and by_id[stale]["code"] is None


async def test_search_unlocatable_leader_keeps_its_own_range(settings_env, monkeypatch, tmp_path):
    notes, _ = _matches_corpus(tmp_path, monkeypatch, notes_text="nothing\nof the\nindexed text\n")

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation"})

    leader, *others = [h for h in r.structured_content["hits"] if h["file"] == str(notes)]
    # colgrep's `unit` spans 3-10 over every matched section; the leader's own range is 3-4.
    assert (leader["hit_id"], leader["location_verified"]) == (f"{notes}:3-4", False)
    assert [h["hit_id"] for h in others] == [f"{notes}:6-7", f"{notes}:9-10"]


async def test_search_unit_without_a_name_is_never_verified(settings_env, monkeypatch, tmp_path):
    # colgrep names no document or raw-code unit, so nothing ties its range to the file.
    notes, _ = _matches_corpus(
        tmp_path, monkeypatch, notes_matches=[_match(3, 4, "Logistics", 1.2), _match(6, 7, "", 0.9)]
    )

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation", "include_code": True})

    nameless = next(h for h in r.structured_content["hits"] if h["hit_id"] == f"{notes}:6-7")
    assert nameless["location_verified"] is False
    assert nameless["snippet"] is None and nameless["code"] is None


async def test_search_include_code_returns_a_verified_units_own_lines(settings_env, monkeypatch, tmp_path):
    notes, _ = _matches_corpus(tmp_path, monkeypatch)

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation", "include_code": True})

    by_id = {h["hit_id"]: h for h in r.structured_content["hits"]}
    assert by_id[f"{notes}:6-7"]["code"] == "## Escalation\n- **PI decision:** switch to a subagent."
    assert by_id[f"{notes}:3-4"]["code"] == "## Logistics\nRoutine scheduling.\n"


async def test_search_one_entry_matches_is_a_lone_unit(settings_env, monkeypatch, tmp_path):
    notes, _ = _matches_corpus(tmp_path, monkeypatch, notes_matches=[_match(3, 4, "Logistics", 1.2)])

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "escalation"})

    assert [h["hit_id"] for h in r.structured_content["hits"] if h["file"] == str(notes)] == [f"{notes}:3-4"]


async def test_search_heading_with_a_dot_stays_verified(settings_env, monkeypatch, tmp_path):
    text = "# Wave 05\n\n## Logistics\nRoutine scheduling.\n\n## v1.8 notes\nShip it.\n"
    notes, _ = _matches_corpus(
        tmp_path,
        monkeypatch,
        notes_text=text,
        notes_matches=[_match(3, 4, "Logistics", 1.2), _match(6, 7, "v1.8 notes", 0.9)],
    )

    async with Client(build(), raise_exceptions=True) as c:
        r = await c.call_tool("search", {"query": "release notes"})

    dotted = next(h for h in r.structured_content["hits"] if h["hit_id"] == f"{notes}:6-7")
    assert dotted["location_verified"] is True
    assert dotted["snippet"] == "## v1.8 notes\nShip it."


async def test_duplicate_ranges_in_matches_count_once(settings_env, monkeypatch, tmp_path):
    notes, _ = _matches_corpus(
        tmp_path,
        monkeypatch,
        notes_matches=[
            _match(3, 4, "Logistics", 1.2),
            _match(6, 7, "Escalation", 0.9),
            _match(6, 7, "Escalation", 0.4),
        ],
    )

    async with Client(build(), raise_exceptions=True) as c:
        searched = await c.call_tool("search", {"query": "escalation"})
        found = await c.call_tool("find_files", {"query": "escalation"})

    hits = [h for h in searched.structured_content["hits"] if h["file"] == str(notes)]
    assert [(h["hit_id"], h["score"]) for h in hits] == [(f"{notes}:3-4", 1.2), (f"{notes}:6-7", 0.9)]
    first = found.structured_content["files"][0]
    assert (first["hits"], first["top_units"]) == (2, ["Logistics", "Escalation"])


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


# --- stderr notifications (R01 §C6) ----------------------------------------


async def test_search_sends_at_most_one_log_notification(settings_env, monkeypatch):
    """R01 §C6: a `search` call must cost the client at most one
    `notifications/message` frame, never one per colgrep stderr line.
    Three synthetic stderr lines (the cold-build banner shape `init` emits,
    R05 D2) must still collapse to a single summary notification once
    `index_updated` is true."""
    fake_adapter = _StderrInjectingAdapter(
        [
            "\U0001f916 Model: lightonai/LateOn-Code-edge (CPU)",
            "\U0001f4c2 Building index...",
            "Indexed /tmp (added: 1, changed: 0, deleted: 0, unchanged: 0)",
        ]
    )
    monkeypatch.setattr(tools_search, "get_adapter", lambda ctx=None: fake_adapter)

    notifications: list[object] = []

    async def logging_callback(params: object) -> None:
        notifications.append(params)

    # `notifications/message` is a deprecated-capability back channel, only
    # negotiated by a legacy-mode session under the 2026-07-28 protocol (same
    # reason `test_doctor_reports_client_root_when_env_root_unset` uses it
    # for `roots/list`).
    async with Client(build(), raise_exceptions=True, logging_callback=logging_callback, mode="legacy") as c:
        r = await c.call_tool("search", {"query": "config parsing"})

    assert r.is_error is False
    assert r.structured_content["index_updated"] is True
    assert len(notifications) <= 1


async def test_search_sends_zero_log_notifications_when_index_already_current(settings_env, monkeypatch):
    """R01 §C6: no stderr chatter at all (index already current) must cost
    zero notifications, not a summary sent unconditionally."""
    fake_adapter = _StderrInjectingAdapter([])
    monkeypatch.setattr(tools_search, "get_adapter", lambda ctx=None: fake_adapter)

    notifications: list[object] = []

    async def logging_callback(params: object) -> None:
        notifications.append(params)

    async with Client(build(), raise_exceptions=True, logging_callback=logging_callback, mode="legacy") as c:
        r = await c.call_tool("search", {"query": "config parsing"})

    assert r.is_error is False
    assert r.structured_content["index_updated"] is False
    assert len(notifications) == 0
