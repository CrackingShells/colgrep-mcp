"""Tests for `colgrep_mcp.store` (index_housekeeping R01 §C1–C3): the store read, the
ordered classification with injected clock/home/roots, and the drift guard that keeps
the server's machine-state roots equal to the hook's.
"""

from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import pytest

from colgrep_mcp import store
from colgrep_mcp.adapter import ColgrepAdapter
from colgrep_mcp.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_SCRIPT = REPO_ROOT / "hooks" / "colgrep_policy.py"

pytestmark = pytest.mark.anyio


NOW = 1_800_000_000.0


def _entry(project: str, *, search_count: int = 5, age_days: float = 0, now: float = NOW) -> store.StoreEntry:
    return store.StoreEntry(
        index_dir=Path("/store") / (Path(project).name or "root"),
        project=project,
        model="m",
        files=3,
        search_count=search_count,
        size_bytes=1024,
        last_modified=now - age_days * 86400,
    )


def _classify(entries, *, home: str, roots: list[str] | None = None, **kw):
    verdicts = store.classify(entries, now=NOW, home=home, machine_roots=roots or [], **kw)
    return {c.entry.project: c for c in verdicts}


# --- read_store -----------------------------------------------------------------------


def test_read_store_reads_project_state_size_and_state_mtime(fake_store, tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    fake_store("live-0001", live, search_count=4, files=7, age_days=40)
    (fake_store.root / "not-an-index").mkdir()  # no project.json: skipped, not an error
    (fake_store.root / "stray-file").write_text("x")

    entries = store.read_store(fake_store.root)

    assert [e.project for e in entries] == [str(live)]
    e = entries[0]
    assert e.files == 7
    assert e.search_count == 4
    assert e.size_bytes > 1024  # the blob plus the two JSON files
    assert time.time() - e.last_modified > 39 * 86400  # `state.json` mtime, back-dated by the fixture


def test_read_store_missing_root_is_empty(tmp_path):
    assert store.read_store(tmp_path / "nowhere") == []


# --- classify ---------------------------------------------------------------------------


def test_classify_orphaned_wins_over_everything(tmp_path):
    gone = str(tmp_path / "gone")
    verdict = _classify([_entry(gone, search_count=0, age_days=400)], home=str(tmp_path), roots=[str(tmp_path)])
    assert verdict[gone].kind == store.ORPHANED
    assert verdict[gone].path_exists is False


def test_classify_machine_state_under_a_root_and_under_a_hidden_home_dir(tmp_path):
    home = tmp_path / "home"
    temp = tmp_path / "temp"
    under_temp = temp / "scratch"
    hidden = home / ".cache" / "uv" / "archive"
    for d in (under_temp, hidden):
        d.mkdir(parents=True)
    verdict = _classify([_entry(str(under_temp)), _entry(str(hidden))], home=str(home), roots=[str(temp)])
    assert verdict[str(under_temp)].kind == store.MACHINE_STATE
    assert verdict[str(hidden)].kind == store.MACHINE_STATE


def test_classify_hidden_work_tree_is_not_machine_state(tmp_path):
    """Claude Code's own `.claude/worktrees/<name>` is a real work tree under a hidden
    directory: a `.git` entry anywhere up the path keeps it out of `machine_state`."""
    home = tmp_path / "home"
    wt = home / ".claude" / "worktrees" / "feature"
    wt.mkdir(parents=True)
    (wt / ".git").write_text("gitdir: elsewhere\n")
    verdict = _classify([_entry(str(wt))], home=str(home))
    assert verdict[str(wt)].kind is None


def test_classify_shadowed_names_the_nearest_live_ancestor(tmp_path):
    root = tmp_path / "repo"
    mid = root / "pkg"
    leaf = mid / "sub"
    leaf.mkdir(parents=True)
    verdict = _classify([_entry(str(root)), _entry(str(mid)), _entry(str(leaf))], home=str(tmp_path / "home"))
    assert verdict[str(root)].kind is None
    assert verdict[str(mid)].kind == store.SHADOWED and verdict[str(mid)].shadowed_by == str(root)
    assert verdict[str(leaf)].kind == store.SHADOWED and verdict[str(leaf)].shadowed_by == str(mid)


def test_classify_child_of_an_orphaned_ancestor_is_not_shadowed(tmp_path):
    child = tmp_path / "gone" / "child"
    child.mkdir(parents=True)
    gone = str(tmp_path / "gone-other")
    verdict = _classify([_entry(gone), _entry(str(child))], home=str(tmp_path / "home"))
    assert verdict[str(child)].kind is None
    assert verdict[str(child)].shadowed_by is None


def test_classify_cold_needs_both_few_searches_and_age(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    p = str(live)
    home = str(tmp_path / "home")
    assert _classify([_entry(p, search_count=1, age_days=31)], home=home)[p].kind == store.COLD
    assert _classify([_entry(p, search_count=2, age_days=31)], home=home)[p].kind is None
    assert _classify([_entry(p, search_count=0, age_days=29)], home=home)[p].kind is None
    assert _classify([_entry(p, search_count=3, age_days=31)], home=home, max_searches=3)[p].kind == store.COLD
    assert _classify([_entry(p, search_count=0, age_days=10)], home=home, days=7)[p].kind == store.COLD


# --- the hook convention is the server convention ----------------------------------------


def test_machine_state_roots_match_the_hook():
    """R01 D4: the hook is stdlib-only and ships outside the PyPI package, so the
    roots are restated in `store.py`; this pins the two lists equal."""
    spec = importlib.util.spec_from_file_location("colgrep_policy", HOOK_SCRIPT)
    hook = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(hook)
    home = os.path.realpath(os.path.expanduser("~"))
    assert store.machine_state_roots(home) == hook.machine_state_roots(home)


# --- store_root ----------------------------------------------------------------------------


async def test_store_root_is_the_index_line_parent_and_is_cached(fake_store, settings_env, tmp_path, monkeypatch):
    live = tmp_path / "live"
    live.mkdir()
    fake_store("gone-0001", tmp_path / "gone")  # `status` on it exits 1 (R02): skipped
    fake_store("live-0001", live)
    argv_file = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_COLGREP_ARGV_FILE", str(argv_file))

    settings = Settings.from_env()
    adapter = ColgrepAdapter(binary=settings.binary, timeout_s=30)
    assert await adapter.store_root() == fake_store.root
    argv_file.unlink()
    assert await adapter.store_root() == fake_store.root
    assert not argv_file.exists()  # cached: no second spawn


async def test_store_root_is_none_when_no_indexed_project_exists(fake_store, settings_env, tmp_path):
    fake_store("gone-0001", tmp_path / "gone")
    settings = Settings.from_env()
    adapter = ColgrepAdapter(binary=settings.binary, timeout_s=30)
    assert await adapter.store_root() is None


# --- remove_index_dir --------------------------------------------------------------------


def test_remove_index_dir_removes_a_matching_child(fake_store, tmp_path):
    d = fake_store("gone-0001", tmp_path / "gone")
    store.remove_index_dir(fake_store.root, d, str(tmp_path / "gone"))
    assert not d.exists()


def test_remove_index_dir_refuses_a_project_mismatch(fake_store, tmp_path):
    d = fake_store("live-0001", tmp_path / "live")
    with pytest.raises(store.StoreError, match="names"):
        store.remove_index_dir(fake_store.root, d, str(tmp_path / "gone"))
    assert d.is_dir()


def test_remove_index_dir_refuses_a_directory_outside_the_root(fake_store, tmp_path):
    d = fake_store("live-0001", tmp_path / "live")
    with pytest.raises(store.StoreError, match="not directly under"):
        store.remove_index_dir(tmp_path / "elsewhere", d, str(tmp_path / "live"))
    with pytest.raises(store.StoreError, match="not directly under"):
        store.remove_index_dir(fake_store.root, d / "index", str(tmp_path / "live"))
    assert d.is_dir()


def test_remove_index_dir_refuses_a_missing_project_json(fake_store, tmp_path):
    d = fake_store("live-0001", tmp_path / "live")
    (d / "project.json").unlink()
    with pytest.raises(store.StoreError, match="unreadable"):
        store.remove_index_dir(fake_store.root, d, str(tmp_path / "live"))
    assert d.is_dir()
