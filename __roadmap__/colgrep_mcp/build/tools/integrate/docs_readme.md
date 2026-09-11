# User Documentation

**Goal**: Write the repository README a human installs from, covering Claude Code, Codex and Agent Plugins 1.0 clients, configuration, the tool surface, and troubleshooting.
**Pre-conditions**:
- [ ] `build/plugin_packaging` and all `build/tools/*` leaves merged (tool names final)
**Success Gates**:
- ⬜ [static] `README.md` has sections: What it is; Requirements (colgrep ≥ 1.6, uv, Python ≥ 3.11 fetched by uv); Install — Claude Code (`claude plugin marketplace add <repo>` + `claude plugin install colgrep-mcp`, and `claude --plugin-dir .`), Codex, Agent Plugins clients, plain `claude mcp add` fallback; Tools table (8 rows, matching `list_tools()` names and one-line purposes); Resources & prompts; Configuration (env table from R01); Troubleshooting (`doctor`, PATH under GUI apps, cold index, `index_build`); Development (`uv run pytest`, roadmap/reports pointers); License
- ⬜ [run] Every tool name in the README's Tools table appears in `cd server && uv run python -c "import asyncio; from mcp import Client; from colgrep_mcp.server import build; print(asyncio.run(_ls()))"`-style listing (write the check as `server/tests/test_readme.py`)
**References**: [R01 §Tools](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R01 §Configuration](../../../../../__reports__/colgrep_mcp/00-architecture_v0.md); `build/plugin_packaging.md` commit bodies — the exact install commands that were verified

## Step 1: Write README and the drift test
**Goal**: Documentation that cannot silently rot.
**Implementation Logic**:
Write `README.md` (repo root) in plain, short paragraphs; install commands in `bash` fenced blocks, one command per block; the Tools table generated once by hand from `list_tools()` and then protected by `server/tests/test_readme.py` which parses the README table rows (regex on `| \`name\` |`) and asserts set equality with the live tool names. Keep the server-side `server/README.md` as a two-line pointer. Apply R05 D5/D11 to `server/colgrep_mcp/guide.md` and `skills/colgrep-search/SKILL.md`: `limit=None` is exhaustive only when `pattern` is set; for pure semantic queries colgrep caps at its runtime default of 15, so pass a larger `limit` explicitly. Also add R05 D1's `location_verified` to the guide's 'Reading results' section, and R05 D3's project-root behaviour to the index section. Do not duplicate the agent guide — link `skills/colgrep-search/SKILL.md` and mention `colgrep://guide`.
**References**: Claude Code plugin install docs `https://code.claude.com/docs/en/discover-plugins`
**Deliverables**: `README.md`, `server/colgrep_mcp/guide.md` (D1/D3/D5 corrections), `skills/colgrep-search/SKILL.md` (D5 correction), `server/tests/test_readme.py` (`test_tools_table_matches_server`)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_readme.py` (expected: PASS)
**Commit**: `docs(docs): write installation and usage README with a tool-table drift test`
