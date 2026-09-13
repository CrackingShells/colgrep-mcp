"""colgrep's index store on disk, read and classified (index_housekeeping R01 §C1–C3).

The only module that knows the store's layout: one child directory per
index holding `project.json` and `state.json` (R02). `read_store` is the
I/O half (one `scandir` walk and two JSON reads per index, 40 ms for 165
indexes on the maintainer's machine); `classify` is the pure half, given
`now`, `home` and the machine-state roots explicitly so a test can pin a
verdict on any OS — the CI runners' temp directory sits under the home
directory on Windows and under a hidden tree on macOS, so an implicit
`Path.home()` would flip results between jobs (R01 risk 2). `index_list`
joins both with `colgrep --stats` for the tools and the resource.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .adapter import ColgrepAdapter
from .models import IndexInfo, IndexList

ORPHANED = "orphaned"
MACHINE_STATE = "machine_state"
SHADOWED = "shadowed"
COLD = "cold"

#: Classes that need no parameter; `list_indexes` reports them as `stale`.
STALE_CLASSES: tuple[str, ...] = (ORPHANED, MACHINE_STATE, SHADOWED)
#: Every class `index_prune` accepts; `cold` needs `days` and `max_searches`.
PRUNE_CLASSES: tuple[str, ...] = (*STALE_CLASSES, COLD)


@dataclass(frozen=True)
class StoreEntry:
    """One index directory as colgrep left it on disk (R01 §C2)."""

    index_dir: Path
    project: str
    model: str
    files: int | None
    search_count: int | None
    size_bytes: int
    last_modified: float


@dataclass(frozen=True)
class Classified:
    """A `StoreEntry` with its verdict (R01 §C3): `kind` is a class name or `None` for live."""

    entry: StoreEntry
    kind: str | None
    path_exists: bool
    shadowed_by: str | None


# --- I/O ------------------------------------------------------------------------


def _dir_size(path: Path) -> int:
    """Bytes under `path`: one `scandir` walk, no `Path.stat()` per file (`maintainer-policy` §Hardware-first)."""
    total = 0
    stack = [str(path)]
    while stack:
        try:
            with os.scandir(stack.pop()) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
        except OSError:
            continue
    return total


def _read_entry(index_dir: Path) -> StoreEntry | None:
    try:
        project = json.loads((index_dir / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    project_path = project.get("project_path")
    if not isinstance(project_path, str) or not project_path:
        return None
    files: int | None = None
    search_count: int | None = None
    last_modified = index_dir.stat().st_mtime
    state_file = index_dir / "state.json"
    try:
        # `state.json` is rewritten on every search (R02), so its mtime is the
        # last-use time; the directory mtime coincides and is the fallback.
        last_modified = state_file.stat().st_mtime
        state = json.loads(state_file.read_text(encoding="utf-8"))
        state_files = state.get("files")
        files = len(state_files) if isinstance(state_files, dict) else None
        sc = state.get("search_count")
        search_count = sc if isinstance(sc, int) else None
    except (OSError, ValueError):
        pass
    return StoreEntry(
        index_dir=index_dir,
        project=project_path,
        model=str(project.get("model", "")),
        files=files,
        search_count=search_count,
        size_bytes=_dir_size(index_dir),
        last_modified=last_modified,
    )


def read_store(root: Path) -> list[StoreEntry]:
    """Every index directory under `root` that carries a `project.json`; others are skipped, never an error."""
    entries: list[StoreEntry] = []
    try:
        children = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError:
        return entries
    for child in children:
        entry = _read_entry(child)
        if entry is not None:
            entries.append(entry)
    return entries


# --- classification (pure) -------------------------------------------------------


def machine_state_roots(home: str) -> list[str]:
    """The hook's `machine_state_roots` (`hooks/colgrep_policy.py`), restated: the hook
    is stdlib-only and ships outside this package, so it cannot be imported; a drift
    test pins the two lists equal (R01 D4)."""
    roots = [
        os.path.realpath(tempfile.gettempdir()),
        os.path.join(home, "Library"),
        os.path.join(home, "AppData"),
    ]
    # The per-user temp directory is not the only one: macOS puts it under
    # `/var/folders` while `/private/tmp` stays a system temp directory, and
    # the indexes under it (every session scratchpad) read as live projects
    # until it was listed here (index_housekeeping README §Status).
    if os.name == "posix":
        posix_tmp = os.path.realpath("/tmp")
        if posix_tmp not in roots:
            roots.append(posix_tmp)
    return roots


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _in_work_tree(path: str) -> bool:
    """Whether any ancestor of `path` (itself included) carries a `.git` entry.

    One `lstat` per path component, no `git` subprocess: it runs only for the
    few machine-state candidates, and it keeps Claude Code's own
    `.claude/worktrees/<name>` (a real work tree under a hidden directory)
    out of the machine-state class.
    """
    p = Path(path)
    for candidate in (p, *p.parents):
        try:
            if (candidate / ".git").exists():
                return True
        except OSError:
            return False
    return False


def is_machine_state(path: str, *, home: str, roots: list[str]) -> bool:
    """Application state, not authored material: the hook's `is_source_corpus` inverted for
    an indexed path (R01 §C3), minus the `git` subprocess."""
    if any(_under(path, root) for root in roots):
        hidden_or_state = True
    elif _under(path, home) and path != home:
        inner = path[len(home) :]
        hidden_or_state = any(part.startswith(".") for part in inner.split(os.sep) if part)
    else:
        return False
    return hidden_or_state and not _in_work_tree(path)


def shadowing_ancestor(project: str, live_projects: set[str]) -> str | None:
    """The nearest indexed, existing ancestor project of `project`, or `None`."""
    for parent in Path(project).parents:
        if str(parent) in live_projects:
            return str(parent)
    return None


def classify(
    entries: list[StoreEntry],
    *,
    now: float,
    home: str,
    machine_roots: list[str],
    days: int = 30,
    max_searches: int = 1,
) -> list[Classified]:
    """One class per entry, first rule wins: orphaned, machine_state, shadowed, cold, live (R01 §C3)."""
    exists = {e.project: os.path.exists(e.project) for e in entries}
    live_projects = {p for p, ok in exists.items() if ok}
    cutoff = now - days * 86400
    out: list[Classified] = []
    for e in entries:
        path_exists = exists[e.project]
        shadowed_by = shadowing_ancestor(e.project, live_projects) if path_exists else None
        if not path_exists:
            kind: str | None = ORPHANED
        elif is_machine_state(e.project, home=home, roots=machine_roots):
            kind = MACHINE_STATE
        elif shadowed_by is not None:
            kind = SHADOWED
        elif (e.search_count or 0) <= max_searches and e.last_modified <= cutoff:
            kind = COLD
        else:
            kind = None
        out.append(Classified(entry=e, kind=kind, path_exists=path_exists, shadowed_by=shadowed_by))
    return out


def classify_now(entries: list[StoreEntry], *, days: int = 30, max_searches: int = 1) -> list[Classified]:
    """`classify` against this machine: the real clock, home directory and machine-state roots."""
    home = os.path.realpath(os.path.expanduser("~"))
    roots = machine_state_roots(home)
    return classify(entries, now=time.time(), home=home, machine_roots=roots, days=days, max_searches=max_searches)


def iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat(timespec="seconds")


# --- removal --------------------------------------------------------------------------


class StoreError(Exception):
    """A removal guard refused (R01 §C5); the directory was left in place."""


def remove_index_dir(root: Path, index_dir: Path, project: str) -> None:
    """Delete `index_dir` only if it is a direct child of `root` whose `project.json`
    names `project` right now (index_housekeeping R01 §C5).

    Never `colgrep clear`: on a gone path it exits 1 (R02), and on a folded
    path it clears the ancestor project instead — the failure `index_clear`'s
    `PROJECT_ROOT_MISMATCH` exists to prevent. Re-reading `project.json` at
    deletion time means a candidate list from an earlier call, or a store
    that changed under us, can never point the delete at another project.
    """
    if index_dir.parent != root:
        raise StoreError(f"{index_dir} is not directly under the store root {root}")
    try:
        named = json.loads((index_dir / "project.json").read_text(encoding="utf-8")).get("project_path")
    except (OSError, ValueError) as exc:
        raise StoreError(f"{index_dir}/project.json unreadable: {exc}") from exc
    if named != project:
        raise StoreError(f"{index_dir}/project.json names {named!r}, not {project!r}")
    shutil.rmtree(index_dir)


# --- the joined view --------------------------------------------------------------


def _enrich(info: IndexInfo, verdict: Classified | None) -> IndexInfo:
    if verdict is None:
        return info
    return info.model_copy(
        update={
            "path_exists": verdict.path_exists,
            "size_bytes": verdict.entry.size_bytes,
            "last_modified": iso_utc(verdict.entry.last_modified),
            "shadowed_by": verdict.shadowed_by,
            "stale": verdict.kind if verdict.kind in STALE_CLASSES else None,
        }
    )


async def index_list(adapter: ColgrepAdapter, *, stale_only: bool = False) -> IndexList:
    """`colgrep --stats` joined with the store by project path (R01 §C4).

    The store read runs in a worker thread: 40 ms of blocking I/O on a
    165-index store must not stall other tool calls on the event loop. When
    the store root cannot be derived (no indexed project exists on disk, R01
    §C1) the four legacy fields are all a caller gets.
    """
    infos = await adapter.stats()
    root = await adapter.store_root(infos)
    total_bytes: int | None = None
    if root is not None:
        entries = await asyncio.to_thread(read_store, root)
        by_project = {c.entry.project: c for c in classify_now(entries)}
        infos = [_enrich(info, by_project.get(info.project)) for info in infos]
        total_bytes = sum(e.size_bytes for e in entries)
    total = len(infos)
    if stale_only:
        infos = [info for info in infos if info.stale is not None]
    return IndexList(indexes=infos, store_root=str(root) if root else None, total_bytes=total_bytes, total=total)
