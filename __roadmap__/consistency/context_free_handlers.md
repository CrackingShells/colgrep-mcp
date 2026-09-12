# Resources and Prompts: Share the Lifespan Adapter

**Goal**: Stop `resources.py` and `prompts.py` each building their own `ColgrepAdapter` from a fresh `Settings.from_env()` on every call — the lifespan already owns one and `server.get_adapter()` now hands it out without a `Context` — and stop re-reading packaged static text per request.
**Pre-conditions**:
- [ ] Working in worktree `/Users/me/worktrees/colgrep-mcp/task-context_free_handlers` on branch `task/context_free_handlers` (created by the lead from the campaign branch); this file exists there — if it does not, stop and report
- [ ] `cd server && uv run pytest` passes before any change (199 passed, 1 skipped)
- [ ] R01 §C1, §C3 read; `server/colgrep_mcp/server.py` read (`get_app(ctx=None)`, `_app`, lifespan)
**Success Gates**:
- ✅ [run] `cd server && uv run pytest` passes; `uv run ruff check` clean
- ✅ [static] `Settings.from_env()` is called nowhere under `server/colgrep_mcp/` except `server.lifespan` and `__main__.main` (`grep -rn "Settings.from_env" server/colgrep_mcp` shows exactly those two)
- ✅ [static] no `_standalone_adapter` symbol remains
- ✅ [behavioral] `colgrep://guide`, `colgrep://settings`, `colgrep://indexes`, `colgrep://status/{+path}`, `colgrep://errors` and `completion/complete` return the same content through `Client(build())` as before (existing tests are the oracle)
**References**: [R01 §C1, §C3, Alternatives row 1, Risk 2](../../__reports__/consistency/00-architecture_v0.md) — why a module-global app handle; [F10 in the 0.1.0 code review](../../__reports__/colgrep_mcp/02-observation_code_review_v0.md) — the completion-cache refill race this leaf also closes

## Step 1: Resources read the lifespan adapter and cache static text
**Goal**: One adapter per server; packaged text read once.
**Implementation Logic**:
(1) Delete `resources._standalone_adapter`; `settings_resource` and `indexes_resource` call `get_adapter()` (no argument). (2) `guide()` and `errors_resource()` are pure functions of package data / `HINTS` — decorate both with `functools.cache` so the file read and the table render happen once per process (the resource decorator wraps the function object; verify with a test that calls the resource twice and asserts one file read via `monkeypatch` on `importlib.resources.files` or by timing — a counter is fine). (3) Rewrite the module docstring: it currently *explains* why static resources cannot reach the adapter; that reasoning is now false. Say instead that static handlers get the adapter from `server.get_app()`'s lifespan handle, and that `status_resource` still takes `ctx` because the template can. (4) `_map_adapter_error` stays (it wraps into `ResourceError`, a different class), but say so in one line. Tests: `test_resources.py` may need to stop monkeypatching `_standalone_adapter`; any test that called a resource function **directly** outside a running `Client` must now either go through `Client(build())` or set `server._app` in a fixture — prefer the client. Add `test_guide_is_read_once` (counter on the underlying read).
**Deliverables**: `server/colgrep_mcp/resources.py` (no `_standalone_adapter`; `guide`/`errors_resource` under `functools.cache`; docstring rewritten), `server/tests/test_resources.py` (`test_guide_is_read_once`; `_standalone_adapter` references removed)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_resources.py tests/test_stdio.py` (expected: PASS); `cd server && ! grep -n '_standalone_adapter\|Settings.from_env' colgrep_mcp/resources.py` (expected: PASS); `cd server && uv run ruff check` (expected: PASS)
**Commit**: `refactor(resources): serve static resources from the lifespan adapter and cache the packaged text`

## Step 2: Completions read the lifespan adapter behind a locked cache
**Goal**: Same adapter as everything else; and two completions racing past the 30 s TTL must not both spawn `colgrep --stats` (F10).
**Implementation Logic**:
(1) Delete `prompts._standalone_adapter`; `_cached_project_paths` uses `get_adapter()`. (2) Guard the refill with a module-level `asyncio.Lock`: check the TTL, and if stale `async with _stats_lock:` re-check the TTL (another completion may have refilled while we waited) before calling `stats()`. Keep `_stats_cache`'s shape so `test_prompts.py`'s existing cache assertions hold. (3) Trim the module docstring's paragraph about building a short-lived adapter; keep the part about *why* the completion callback has no request `Context`. Add `test_completion_cache_refill_is_serialised`: monkeypatch the adapter's `stats` with a slow coroutine that counts calls, fire two `complete/complete` requests concurrently through the client after expiring the cache, assert one call.
**Deliverables**: `server/colgrep_mcp/prompts.py` (`_stats_lock`, `_cached_project_paths` double-checked; no `_standalone_adapter`), `server/tests/test_prompts.py` (`test_completion_cache_refill_is_serialised`)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_prompts.py` (expected: PASS); `cd server && ! grep -n '_standalone_adapter\|Settings.from_env' colgrep_mcp/prompts.py` (expected: PASS); `cd server && uv run ruff check` (expected: PASS)
**Commit**: `refactor(prompts): complete paths from the lifespan adapter behind a locked stats cache`
