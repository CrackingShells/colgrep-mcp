"""Tests for ColgrepAdapter (R01 §Adapter contract, R05 deltas).

Step 2 covers `_run`, `build_search_argv` and `version`. Step 3 extends this
file with `search`/`status`/`stats`/`settings`/`init`/`clear`.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from colgrep_mcp.adapter import (
    ColgrepAdapter,
    ColgrepError,
    ColgrepFailed,
    ColgrepNotFound,
    ColgrepParseError,
    ColgrepTimeout,
    SearchRequest,
)

pytestmark = pytest.mark.anyio


# --- build_search_argv (pure, no subprocess) --------------------------------


def _base_request(**overrides) -> SearchRequest:
    defaults = dict(query="x", paths=[Path("/tmp/proj")])
    defaults.update(overrides)
    return SearchRequest(**defaults)


def test_argv_base_shape():
    adapter = ColgrepAdapter()
    argv = adapter.build_search_argv(_base_request())

    assert argv[:3] == ["search", "--json", "-y"]
    assert argv[-2:] == ["x", "/tmp/proj"]


@pytest.mark.parametrize(
    "field, value, expected_fragment",
    [
        ("pattern", "def .*parse", ["-e", "def .*parse"]),
        ("fixed_string", True, ["-F"]),
        ("whole_word", True, ["-w"]),
        ("case_sensitive", True, ["-s"]),
        ("code_only", True, ["--code-only"]),
        ("semantic_only", True, ["--semantic-only"]),
        ("alpha", 0.75, ["--alpha", "0.75"]),
        ("skip_index_update", True, ["--no-update"]),
    ],
)
def test_argv_scalar_flags_present_when_set(field, value, expected_fragment):
    adapter = ColgrepAdapter()
    req = _base_request(**{field: value})
    argv = adapter.build_search_argv(req)

    joined = " ".join(argv)
    assert " ".join(expected_fragment) in joined


@pytest.mark.parametrize(
    "field, falsy_value",
    [
        ("pattern", None),
        ("fixed_string", False),
        ("whole_word", False),
        ("case_sensitive", False),
        ("code_only", False),
        ("semantic_only", False),
        ("alpha", None),
        ("skip_index_update", False),
    ],
)
def test_argv_scalar_flags_absent_when_unset(field, falsy_value):
    adapter = ColgrepAdapter()
    req = _base_request(**{field: falsy_value})
    argv = adapter.build_search_argv(req)

    flag_tokens = {"-e", "-F", "-w", "-s", "--code-only", "--semantic-only", "--alpha", "--no-update"}
    used_flags = set(argv) & flag_tokens
    # Only flags for fields not set in this parametrisation may appear (none
    # of them are set here besides the field under test, which is falsy).
    assert used_flags == set()


@pytest.mark.parametrize(
    "field, cli_flag",
    [
        ("include", "--include"),
        ("exclude", "--exclude"),
        ("exclude_dir", "--exclude-dir"),
    ],
)
def test_argv_repeated_flags(field, cli_flag):
    adapter = ColgrepAdapter()
    req = _base_request(**{field: ["a", "b"]})
    argv = adapter.build_search_argv(req)

    # Each value gets its own flag occurrence, in order.
    idx = [i for i, tok in enumerate(argv) if tok == cli_flag]
    assert len(idx) == 2
    assert argv[idx[0] + 1] == "a"
    assert argv[idx[1] + 1] == "b"


def test_argv_limit_present_when_set():
    adapter = ColgrepAdapter()
    argv = adapter.build_search_argv(_base_request(limit=7))
    i = argv.index("-k")
    assert argv[i + 1] == "7"


def test_argv_limit_omitted_when_none():
    adapter = ColgrepAdapter()
    argv = adapter.build_search_argv(_base_request(limit=None))
    assert "-k" not in argv


def test_argv_query_omitted_when_none_and_pattern_set():
    adapter = ColgrepAdapter()
    req = _base_request(query=None, pattern="def parse_args")
    argv = adapter.build_search_argv(req)

    assert "def parse_args" in argv  # the pattern value itself
    # No bare positional query token beyond the pattern's own value and the path.
    assert argv[-1] == "/tmp/proj"
    assert argv.count("/tmp/proj") == 1


def test_argv_multiple_paths_appended_in_order():
    adapter = ColgrepAdapter()
    req = _base_request(paths=[Path("/a"), Path("/b")])
    argv = adapter.build_search_argv(req)
    assert argv[-2:] == ["/a", "/b"]


def test_argv_full_flag_order_smoke():
    """From the spec example: query='x', pattern='y', include=['*.py'], limit=None."""
    adapter = ColgrepAdapter()
    req = _base_request(query="x", pattern="y", include=["*.py"], limit=None)
    argv = adapter.build_search_argv(req)

    assert argv == ["search", "--json", "-y", "-e", "y", "--include", "*.py", "x", "/tmp/proj"]


def test_argv_rejects_query_starting_with_dash():
    adapter = ColgrepAdapter()
    req = _base_request(query="-rf")
    with pytest.raises(ColgrepError):
        adapter.build_search_argv(req)


# --- version() / _run() over the fake binary --------------------------------


async def test_version_via_fake_binary(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    version = await adapter.version()
    assert version == "colgrep 1.6.2"


async def test_run_prepends_color_never(fake_colgrep_bin, tmp_path, monkeypatch):
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    await adapter.version()

    seen_argv = json.loads(argv_file.read_text())
    assert seen_argv == ["--version", "--color", "never"]


async def test_colgrep_not_found_for_bogus_binary():
    adapter = ColgrepAdapter(binary="/no/such/colgrep-binary-xyz", timeout_s=5)
    with pytest.raises(ColgrepNotFound):
        await adapter.version()


async def test_colgrep_failed_on_nonzero_exit(fake_colgrep_bin, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_EXIT", "2")
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    with pytest.raises(ColgrepFailed) as exc_info:
        await adapter.version()

    err = exc_info.value
    assert err.returncode == 2
    assert "forced failure" in err.stderr_tail
    assert err.argv[0] == "--version"


async def test_colgrep_timeout_leaves_no_zombie(fake_colgrep_bin, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_SLEEP", "5")
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=0.5)
    with pytest.raises(ColgrepTimeout):
        await adapter.version()

    assert adapter._last_proc is not None
    assert adapter._last_proc.returncode is not None


async def test_cancel_leaves_no_zombie(fake_colgrep_bin, monkeypatch):
    """F1: a client-cancelled tool call (not a timeout) must still reap the child.

    `wait_for`'s *timeout* path was already handled (see
    `test_colgrep_timeout_leaves_no_zombie` above); this exercises the other
    abnormal exit, `asyncio.CancelledError`, which `except TimeoutError`
    never catches.
    """
    monkeypatch.setenv("FAKE_COLGREP_SLEEP", "5")
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=30)

    task = asyncio.ensure_future(adapter.version())
    await asyncio.sleep(0.2)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert adapter._last_proc is not None
    assert adapter._last_proc.returncode is not None


async def test_with_stderr_shallow_copy(fake_colgrep_bin):
    seen: list[str] = []

    async def cb(line: str) -> None:
        seen.append(line)

    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    forwarding = adapter.with_stderr(cb)

    assert forwarding is not adapter
    assert forwarding.binary == adapter.binary
    assert forwarding.timeout_s == adapter.timeout_s
    assert forwarding.on_stderr is cb
    assert adapter.on_stderr is None


# --- search() ----------------------------------------------------------


async def test_search_returns_raw_hits(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    hits = await adapter.search(SearchRequest(query="config parsing", paths=[Path(".").resolve()]))

    assert isinstance(hits, list)
    assert len(hits) >= 1
    assert {"unit", "score"} <= hits[0].keys()


async def test_search_zero_hits_returns_empty_list(fake_colgrep_bin, monkeypatch, tmp_path):
    empty_fixture = tmp_path / "empty_hits.json"
    empty_fixture.write_text("[]")
    monkeypatch.setenv("FAKE_COLGREP_HITS", str(empty_fixture))

    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    hits = await adapter.search(SearchRequest(query="no such thing", paths=[Path(".").resolve()]))

    assert hits == []


async def test_search_raises_parse_error_on_bad_json(fake_colgrep_bin, monkeypatch, tmp_path):
    bad_output = tmp_path / "not_json.txt"
    bad_output.write_text("not json at all")
    monkeypatch.setenv("FAKE_COLGREP_RAW_STDOUT", str(bad_output))

    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    with pytest.raises(ColgrepParseError):
        await adapter.search(SearchRequest(query="x", paths=[Path(".").resolve()]))


async def test_search_rejects_relative_paths(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    with pytest.raises(ColgrepError):
        await adapter.search(SearchRequest(query="x", paths=[Path("relative")]))


async def test_search_forced_failure_raises_colgrep_failed_with_tail(fake_colgrep_bin, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_EXIT", "1")
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)

    with pytest.raises(ColgrepFailed) as exc_info:
        await adapter.search(SearchRequest(query="x", paths=[Path(".").resolve()]))

    assert exc_info.value.returncode == 1
    assert "forced failure" in exc_info.value.stderr_tail


async def test_search_timeout_leaves_no_zombie(fake_colgrep_bin, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_SLEEP", "5")
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=0.5)

    with pytest.raises(ColgrepTimeout):
        await adapter.search(SearchRequest(query="x", paths=[Path(".").resolve()]))

    assert adapter._last_proc is not None
    assert adapter._last_proc.returncode is not None


# --- status() ------------------------------------------------------------


async def test_status_indexed(fake_colgrep_bin, tmp_path):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    status = await adapter.status(tmp_path)

    assert status.indexed is True
    assert status.project == str(tmp_path)
    assert status.requested_path == str(tmp_path)
    assert status.model == "lightonai/LateOn-Code-edge"


async def test_status_not_indexed(fake_colgrep_bin, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_INDEXED", "0")
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    status = await adapter.status(tmp_path)

    assert status.indexed is False
    assert status.requested_path == str(tmp_path)


async def test_status_requires_absolute_path(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    with pytest.raises(ColgrepError):
        await adapter.status(Path("relative/path"))


# --- stats() / settings() ------------------------------------------------


async def test_stats_via_fake_binary(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    infos = await adapter.stats()

    assert len(infos) == 2
    assert infos[0].project == "/tmp/fake-corpus"
    assert infos[0].units_indexed == 3
    assert infos[0].search_count == 7


async def test_settings_via_fake_binary(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    settings = await adapter.settings()

    assert settings["model"] == "lightonai/LateOn-Code-edge (default)"
    assert settings["k"] == "25 (default)"
    assert settings["n"] == "6 (default)"


# --- init() ----------------------------------------------------------------


async def test_init_cold_build_summary(fake_colgrep_bin, tmp_path):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    result = await adapter.init(tmp_path)

    assert result.project == str(tmp_path)
    assert result.added == 155
    assert result.changed == 1
    assert result.deleted == 199
    assert result.unchanged == 0
    assert result.up_to_date is False
    assert result.elapsed_ms >= 0
    assert any("Building index" in line for line in result.log_tail)


async def test_init_up_to_date(fake_colgrep_bin, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COLGREP_UPTODATE", "1")
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    result = await adapter.init(tmp_path)

    assert result.up_to_date is True
    assert result.added is None
    assert result.changed is None
    assert result.project == str(tmp_path)


async def test_init_streams_stderr_to_on_stderr(fake_colgrep_bin, tmp_path):
    seen: list[str] = []

    async def cb(line: str) -> None:
        seen.append(line)

    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10, on_stderr=cb)
    await adapter.init(tmp_path)

    assert any("Building index" in line for line in seen)


async def test_init_requires_absolute_path(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    with pytest.raises(ColgrepError):
        await adapter.init(Path("relative/path"))


# --- clear() ---------------------------------------------------------------


async def test_clear_via_fake_binary(fake_colgrep_bin, tmp_path):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    result = await adapter.clear(tmp_path)

    assert result is None


async def test_clear_requires_absolute_path(fake_colgrep_bin):
    adapter = ColgrepAdapter(binary=fake_colgrep_bin, timeout_s=10)
    with pytest.raises(ColgrepError):
        await adapter.clear(Path("relative/path"))


# --- real colgrep smoke test (opt-in) ---------------------------------------


@pytest.mark.real_colgrep
@pytest.mark.skipif(
    os.environ.get("COLGREP_MCP_REAL") != "1",
    reason="set COLGREP_MCP_REAL=1 (and have a real `colgrep` on PATH) to run this",
)
async def test_real_colgrep_version_and_stats():
    adapter = ColgrepAdapter(binary=os.environ.get("COLGREP_MCP_BINARY", "colgrep"), timeout_s=30)

    version = await adapter.version()
    assert version.startswith("colgrep ")

    infos = await adapter.stats()
    assert isinstance(infos, list)
