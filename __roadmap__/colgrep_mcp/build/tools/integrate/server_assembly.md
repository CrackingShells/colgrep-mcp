# Server Assembly

**Goal**: Wire the three tool modules, resources and prompts into one server with a single adapter instance from a lifespan, unified path/lock helpers, a stdio round-trip test, and a working `colgrep-mcp` console script.
**Pre-conditions**:
- [ ] `build/tools/search_tools`, `index_tools`, `resources_prompts` merged; `cd server && uv run pytest -q` passes on the milestone branch
**Success Gates**:
- ✅ [run] `cd server && uv run pytest -q` passes, including `tests/test_stdio.py` which spawns `uv run colgrep-mcp` with `COLGREP_MCP_BINARY=<fake>` via `mcp.client` stdio transport, initializes, lists 8 tools / 3 resources / 1 template / 3 prompts and calls `search`
- ✅ [static] Exactly one `ColgrepAdapter` construction site (in `server.py` lifespan); `tools_search.py`, `tools_index.py`, `resources.py`, `prompts.py` obtain it through `get_adapter(ctx)`; no `# TODO(server_assembly)` markers remain
- ✅ [run] `cd server && uv run colgrep-mcp --help` exits 0 and documents `--transport`, `--host`, `--port`
- ✅ [run] `cd server && COLGREP_MCP_BINARY=/nonexistent uv run python -c "from colgrep_mcp.server import build; build()"` exits 0 (a missing binary must not prevent startup — `doctor` reports it)
**References**: [R01 §Server metadata](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R01 §Configuration](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R01 §Concurrency invariant](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md)

## Step 1: Lifespan-owned adapter and de-duplicated helpers
**Goal**: Remove the temporary per-module adapter construction and any duplicated `paths.py`/`locks.py` variants left by parallel leaves.
**Implementation Logic**:
In `server.py`: `@dataclass class AppContext: settings: Settings; adapter: ColgrepAdapter`; `@asynccontextmanager async def lifespan(server) -> AsyncIterator[AppContext]` building both from `Settings.from_env()`; `mcp = MCPServer("colgrep", instructions=INSTRUCTIONS, version=__version__, lifespan=lifespan)`; `def get_adapter(ctx: Context) -> ColgrepAdapter: return ctx.request_context.lifespan_context.adapter` and `get_settings(ctx)`. Because `index_build` needs a per-call `on_stderr`, give `ColgrepAdapter` a `with_stderr(cb) -> ColgrepAdapter` method returning a shallow copy sharing binary/timeout (add it in `adapter.py`). Replace every `_adapter()` helper and TODO marker. Reconcile `paths.py`/`locks.py` if two versions exist (keep one, update imports, keep both leaves' tests green). Ensure `search`/`find_files` also take the per-project lock (R01) — shared acquisition is fine (a plain `asyncio.Lock` serialises; accept it for v0.1 and note it in the docstring).
**References**: SDK lifespan docs (context7, "lifespan" + `ctx.request_context.lifespan_context`)
**Deliverables**: `server/colgrep_mcp/server.py` (`AppContext`, `lifespan`, `get_adapter`, `get_settings`, `build`), `server/colgrep_mcp/adapter.py` (`with_stderr`), updated imports in `tools_search.py`, `tools_index.py`, `resources.py`, `prompts.py`
**Consistency Checks**: `cd server && uv run pytest -q && ! grep -rn "TODO(server_assembly)" colgrep_mcp/` (expected: PASS)
**Commit**: `refactor(server): own the adapter in the lifespan and unify path and lock helpers`

## Step 2: stdio round-trip test and CLI polish
**Goal**: Prove the real transport works, not just the in-memory one.
**Implementation Logic**:
`tests/test_stdio.py`: use the SDK's stdio client (`from mcp.client.stdio import stdio_client, StdioServerParameters` or the v2 `Client` with a stdio transport — check context7 for the v2 idiom) to spawn `sys.executable -m colgrep_mcp` with env `COLGREP_MCP_BINARY=<fake>`, `COLGREP_MCP_ROOT=<tmp>`; initialize; assert `server_info.name == "colgrep"`, counts of tools/resources/templates/prompts, and one `search` call returns hits. Mark it `@pytest.mark.timeout(60)` if `pytest-timeout` is added, else guard with `anyio.fail_after(60)`. `__main__.py`: add `--version` flag; log the resolved settings (without env dump) at INFO on startup to stderr; ensure nothing ever prints to stdout except the protocol. Add `[tool.pytest.ini_options] markers = ["real_colgrep: needs the real binary"]`.
**References**: [R01 §Configuration](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md) — CLI flags
**Deliverables**: `server/tests/test_stdio.py`, `server/colgrep_mcp/__main__.py` (`--version`, startup log), `server/pyproject.toml` (markers)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_stdio.py` (expected: PASS)
**Commit**: `test(server): add stdio round-trip test and finish the colgrep-mcp CLI`
