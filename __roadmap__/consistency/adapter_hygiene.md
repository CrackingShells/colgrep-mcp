# Adapter and Locks: Per-Spawn Waste

**Goal**: Remove the small per-call costs the adapter and lock layer pay for state they already hold: the environment copy on every spawn, four hand-written absolute-path guards, a double `splitlines` on init stderr, and a `Path.resolve()` on every lock acquisition for a path callers already resolved.
**Pre-conditions**:
- [ ] Working in worktree `/Users/hacker/Documents/tmp/claude-worktrees/colgrep_mcp/task-adapter_hygiene` on branch `task/adapter_hygiene` (created by the lead from the campaign branch); this file exists there — if it does not, stop and report
- [ ] `cd server && uv run pytest` passes before any change (199 passed, 1 skipped)
**Success Gates**:
- ✅ [run] `cd server && uv run pytest` passes; `uv run ruff check` clean
- ✅ [static] `adapter.py` has one `_require_absolute` guard and no `os.environ` access inside `_run`
- ✅ [static] `locks.py` documents that callers pass resolved absolute paths and does not call `.resolve()`
**References**: [R01 §Executive Summary, §C5](../../__reports__/consistency/00-architecture_v0.md) — hardware-friendliness rule; [`__reports__/colgrep_mcp/02-observation_code_review_v0.md` F14](../../__reports__/colgrep_mcp/02-observation_code_review_v0.md) — the guards were once bare `assert`s; keep them raising

## Step 1: Compute per-adapter state once
**Goal**: `_run` builds `{**os.environ, "NO_COLOR": "1"}` for every spawn and every `with_stderr` copy; four methods repeat the same `is_absolute` check; `init` splits the same stderr twice.
**Implementation Logic**:
(1) `ColgrepAdapter.__init__` computes `self._env = {**os.environ, "NO_COLOR": "1"}` once; `with_stderr` passes the same dict to the copy (add a private `env` keyword to `__init__` for that, defaulting to a fresh computation). Tests that monkeypatch `os.environ` *after* constructing an adapter would break — check `test_adapter.py` for such a pattern and, if one exists, construct the adapter after the monkeypatch in that test (that is the only permitted test edit). (2) `_require_absolute(path: Path, what: str) -> None` raising the same `ColgrepError(f"{what}() requires an absolute path, got {path!r}")`; `search`, `status`, `init`, `clear` call it. (3) `init`: `lines = stderr.splitlines()` once; summary from `lines`, `log_tail = lines[-20:]`. (4) `locks._lock_for`: key on `str(path)`; docstring states the contract that callers pass the resolved absolute path `resolve_paths` returns (every current caller does). Add `test_locks.py::test_lock_key_is_the_path_string` asserting two `Path` objects with equal string share one lock and that `_lock_for` does not touch the filesystem for a non-existent path.
**Deliverables**: `server/colgrep_mcp/adapter.py` (`_env` attribute, `_require_absolute`, single split in `init`), `server/colgrep_mcp/locks.py` (`_lock_for` without `resolve`; docstring), `server/tests/test_locks.py` (`test_lock_key_is_the_path_string`)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_adapter.py tests/test_locks.py tests/test_tools_search.py tests/test_tools_index.py` (expected: PASS); `cd server && ! grep -n 'os.environ' colgrep_mcp/adapter.py | grep -v __init__` (expected: PASS); `cd server && uv run ruff check` (expected: PASS)
**Commit**: `refactor(adapter): compute the spawn environment once and stop re-resolving lock keys`
