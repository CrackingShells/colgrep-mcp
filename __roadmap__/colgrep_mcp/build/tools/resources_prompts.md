# Resources, Prompts, Completions

**Goal**: Expose the guide, settings, index list and per-path status as MCP resources; ship the `explore`/`locate`/`impact` prompts; complete `path` arguments from the indexed projects.
**Pre-conditions**:
- [ ] `build/colgrep_adapter` merged; `build/agent_skill` merged (`server/colgrep_mcp/guide.md` exists)
- [ ] `server/colgrep_mcp/resources.py` and `prompts.py` stubs exist
**Success Gates**:
- ✅ [run] `cd server && uv run pytest -q tests/test_resources.py tests/test_prompts.py` passes
- ✅ [run] `Client(build()).list_resources()` returns `colgrep://guide` (text/markdown), `colgrep://settings`, `colgrep://indexes` (application/json); `list_resource_templates()` returns `colgrep://status/{+path}`; reading `colgrep://status/Users/x/proj` yields `IndexStatus` JSON for `/Users/x/proj`
- ✅ [run] `list_prompts()` returns `explore`, `locate`, `impact`, each with a required first argument and optional `path`; `get_prompt("explore", {"question": "…"})` returns one user message whose text names the tools `search`, `expand` and forbids shell grep
- ✅ [run] `complete()` for the template's `path` argument and for a prompt's `path` argument returns indexed project paths from the fake `--stats` (prefix-filtered)
**References**: [R01 §Resources and completions](../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R01 §Prompts](../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R02 Resources / Prompts tables](../../../../__reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md) — adopt-guarded: resources must never be load-bearing (every fact they expose is also reachable by a tool); [R05 D5, D11](../../../../__reports__/colgrep_mcp/02-architecture_v1.md) — prompt text must say `limit=None` is exhaustive only together with `pattern`, and that colgrep's runtime default is 15

## Step 1: Resources and the status template
**Goal**: Browsable, cheap-to-read state for clients that render resources.
**Implementation Logic**:
`register(mcp)` in `resources.py`: `@mcp.resource("colgrep://guide", mime_type="text/markdown", title="colgrep usage guide")` returning `importlib.resources.files("colgrep_mcp").joinpath("guide.md").read_text()`; `@mcp.resource("colgrep://settings", mime_type="application/json")` returning `await adapter.settings()`; `@mcp.resource("colgrep://indexes", mime_type="application/json")` returning `IndexList(...).model_dump()`; template `@mcp.resource("colgrep://status/{+path}", mime_type="application/json", security=ResourceSecurity(reject_path_traversal=True, reject_absolute_paths=False, reject_null_bytes=True))` — verified: the default `ResourceSecurity` rejects a leading `/`, and `{+path}` keeps inner slashes — the handler accepts `path` with or without a leading `/` and normalises to an absolute `Path`. Adapter failures inside resources raise `ResourceError` (from `mcp.server.mcpserver.exceptions`) with the same messages as the tools' `ToolError`s. Get the adapter the same way `tools_search.py` does (`_adapter()` helper; the integrator unifies).
**References**: SDK URI-template docs (context7 `/websites/py_sdk_modelcontextprotocol_io_v2`, "uri-templates" and "ResourceSecurity")
**Deliverables**: `server/colgrep_mcp/resources.py` (`register`, `guide`, `settings_resource`, `indexes_resource`, `status_resource`), `server/tests/test_resources.py`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_resources.py` (expected: PASS)
**Commit**: `feat(resources): expose guide, settings, indexes and per-path status resources`

## Step 2: Prompts and completions
**Goal**: One-keystroke workflows and argument autocompletion.
**Implementation Logic**:
`prompts.py`: three `@mcp.prompt(title=...)` functions returning a single user-role message string (SDK wraps `str` into a user message; confirm with a quick in-memory test). Text per R01 §Prompts, written imperatively for the agent, ≤ 25 lines each, naming tools and arguments exactly (`search(query=..., limit=25, paths=[path])`, `pattern` for identifiers, `expand(hit_ids=[...])`, `find_files`), and ending with an output contract (answer with `file:line` citations). `path` argument optional; when given, the text scopes every call with `paths=[path]`. `@mcp.completion()` handler: when `ref` is a `ResourceTemplateReference` for `colgrep://status/{+path}` or a `PromptReference` and `argument.name == "path"` → values = indexed project paths from `adapter.stats()` filtered by `startswith(argument.value)` (strip a leading `/` for the template variant), `Completion(values=..., has_more=False)`; else `None`. Cache the stats for 30 s to keep completions snappy.
**References**: [R01 §Prompts](../../../../__reports__/colgrep_mcp/00-architecture_v0.md); SDK completions docs (context7)
**Deliverables**: `server/colgrep_mcp/prompts.py` (`register`, `explore`, `locate`, `impact`, `complete_path`), `server/tests/test_prompts.py`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_prompts.py` (expected: PASS)
**Commit**: `feat(prompts): add explore, locate and impact prompts with path completions`
