# Index Tools

**Goal**: Implement `index_status`, `index_build` (with streamed progress), `index_clear` (guarded elicitation), `list_indexes` and `doctor`.
**Pre-conditions**:
- [ ] `build/colgrep_adapter` merged (`status`, `stats`, `settings`, `init`, `clear`, `version` work against the fake binary)
- [ ] `server/colgrep_mcp/tools_index.py` stub exists
**Success Gates**:
- ⬜ [run] `cd server && uv run pytest -q tests/test_tools_index.py` passes
- ⬜ [run] `index_build` through `Client(build())` with a `progress_callback` receives ≥ 1 progress notification driven by the fake binary's `Indexing i/3 files` stderr lines
- ⬜ [run] `index_clear` without `confirm` on a client that declares no elicitation capability raises a `ToolError` naming `confirm=true`; with a client whose `elicitation_callback` accepts, the fake `clear` runs; with a callback that declines, nothing runs and the result says `cleared=false`
- ⬜ [static] Annotations: `index_status`/`list_indexes`/`doctor` read-only; `index_build` `read_only_hint=False, destructive_hint=False, idempotent_hint=True`; `index_clear` `destructive_hint=True`
**References**: [R01 §Tools](../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R01 §Key Flows — Destructive operation](../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R02 Client-initiated table](../../../../__reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md) — elicitation adopt-guarded, roots defer, progress adopt-now

## Step 1: Read-only tools — index_status, list_indexes, doctor
**Goal**: Let an agent learn the index situation in one call before searching.
**Implementation Logic**:
`index_status(path: str | None, ctx)`: resolve one path with `paths.resolve_paths` (import from `colgrep_mcp.paths`; if that module is not yet merged when you start, create it with the exact signatures listed in `search_tools.md` Step 1 — the two leaves agree on it and the integrator resolves any duplicate), call `adapter.status(path)`, enrich `units_indexed`/`search_count` from `adapter.stats()` when a matching `project` is present (match on resolved absolute path). `list_indexes(ctx)` → `IndexList`. `doctor(ctx)`: `shutil.which(settings.binary)`; `adapter.version()` (catch `ColgrepNotFound` → `problems`); `adapter.settings()`; `default_root()` and its source; check `uv`? no — only colgrep concerns; `ok = not problems`. Text content for each is a short human table; `structured_content` the model dump. Return `CallToolResult` like the search tools.
**References**: [R03 §Text-format samples](../../../../__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md)
**Deliverables**: `server/colgrep_mcp/tools_index.py` (`register`, `index_status`, `list_indexes`, `doctor`, `_render_status`), `server/tests/test_tools_index.py` (status indexed / not indexed via `FAKE_COLGREP_INDEXED=0`; list_indexes count; doctor ok and doctor with bogus binary)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_tools_index.py -k "status or list or doctor"` (expected: PASS)
**Commit**: `feat(index): add index_status, list_indexes and doctor tools`

## Step 2: index_build with progress, index_clear with guarded elicitation
**Goal**: Cover the two mutating operations safely.
**Implementation Logic**:
`index_build(path, force_cpu=False, ctx)`: hold the per-project lock (import `project_lock(path)` from `colgrep_mcp/locks.py` — create it: module-level `dict[str, asyncio.Lock]` keyed by resolved path string, `asynccontextmanager project_lock(path)`), construct the adapter with `on_stderr` = coroutine that calls `parse_progress(line)`; when it yields `(n, total)` → `await ctx.report_progress(n, total, message=line.strip())`, else `await ctx.info(line.strip())` (rate-limit info to one per 0.5 s to avoid flooding). Return `IndexBuildResult`; afterwards `try: await ctx.notify_resource_updated("colgrep://indexes") except Exception: pass` (guarded). `index_clear(path, confirm=False, ctx)`: if not `confirm`: check `ctx.session.check_client_capability(ClientCapabilities(elicitation=ElicitationCapability()))`; if true → `class Confirm(BaseModel): confirm: bool`; `res = await ctx.elicit(f"Delete the colgrep index for {path}? This cannot be undone.", schema=Confirm)`; wrap in `try/except Exception` (covers `NoBackChannelError` on 2026-07-28 sessions) and treat failure as "no elicitation"; proceed only if `res.action == "accept" and res.data.confirm`; if elicitation unavailable → `ToolError("Refusing to delete without confirmation. Call again with confirm=true to delete the index for <path>.")`. On decline/cancel return `IndexClearResult(cleared=False)` with text "Not cleared (declined)". Both tools are `async`, return `CallToolResult`.
Tests: progress via `client.call_tool("index_build", {...}, progress_callback=cb)` collecting calls; elicitation via `Client(build(), elicitation_callback=...)` returning `ElicitResult(action="accept", content={"confirm": True})` and one returning `action="decline"`; a plain `Client(build())` (no callback → no capability) expecting `ToolError`/`is_error` result text containing `confirm=true`; assert fake `clear` was/wasn't invoked through `FAKE_COLGREP_ARGV_FILE`.
**References**: [R01 §Concurrency invariant](../../../../__reports__/colgrep_mcp/00-architecture_v0.md); SDK docs on `ctx.report_progress`, `ctx.elicit`, `check_client_capability` (context7 `/websites/py_sdk_modelcontextprotocol_io_v2`)
**Deliverables**: `server/colgrep_mcp/locks.py` (`project_lock`), `server/colgrep_mcp/tools_index.py` (`index_build`, `index_clear`, `_ProgressForwarder`), `server/tests/test_tools_index.py` (extended), `server/tests/test_locks.py`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_tools_index.py tests/test_locks.py` (expected: PASS)
**Commit**: `feat(index): add index_build with streamed progress and elicitation-guarded index_clear`
