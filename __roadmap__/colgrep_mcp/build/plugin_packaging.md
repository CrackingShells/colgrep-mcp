# Plugin Packaging

**Goal**: Make the repository root simultaneously a valid Claude Code plugin (+ one-plugin marketplace), an Agent Plugins 1.0 plugin, and a Codex plugin (+ marketplace), all launching the same `colgrep-mcp` stdio server through `uv`.
**Pre-conditions**:
- [ ] `scaffold_package` merged (`server/pyproject.toml` declares the `colgrep-mcp` script)
**Success Gates**:
- ✅ [run] `claude plugin validate .` prints `Validation passed` (warnings allowed, none about missing manifest fields)
- ✅ [run] `cd server && uv run pytest -q tests/test_manifests.py` passes: every manifest is valid JSON, versions all equal `colgrep_mcp.__version__`, Agent Plugins manifests carry the exact `$schema` URLs and only the ten permitted top-level fields, `mcp.json` server entry has `type: "stdio"`, `.mcp.json`/`mcp.json` reference the same command and args modulo `${CLAUDE_PLUGIN_ROOT}` ↔ `${PLUGIN_ROOT}`
- ✅ [behavioral] `claude --plugin-dir . -p "list your MCP tools"` (or `claude mcp list` inside a session started with `--plugin-dir .`) shows the `colgrep` server connected — record the exact command and output in the commit body; if it cannot be run non-interactively, say so
**References**: [R01 §Packaging layout](../../../__reports__/colgrep_mcp/00-architecture_v0.md) — file list and launch command; Agent Plugins spec `https://agent-plugins.org/specification` (v1.0.0) — permitted fields, `${PLUGIN_ROOT}`/`${PLUGIN_DATA}` expansion rules; Claude Code plugins reference `https://code.claude.com/docs/en/plugins-reference` — `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`; the user's own Codex/Claude dual plugin at `/Users/me/.claude/plugins/marketplaces/cell-marketplace/plugins/cell/` — mirror its `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` shapes

## Step 1: Author the manifests and MCP configs
**Goal**: Every target client can discover and launch the server from this directory.
**Implementation Logic**:
1. `.claude-plugin/plugin.json`: `name: "colgrep-mcp"`, `displayName: "colgrep"`, `version` = pyproject version, `description` (one sentence, agent-oriented: semantic + hybrid code search as MCP tools), `author` (Eliott Jacopin, eliott.jacopin@riken.jp), `repository`, `license: "MIT"`, `keywords`, `mcpServers: "./.mcp.json"`, `skills: "./skills/"`.
2. `.mcp.json` (Claude Code): server key `colgrep`, `command: "uv"`, `args: ["run","--quiet","--directory","${CLAUDE_PLUGIN_ROOT}/server","colgrep-mcp"]`, `env: {"UV_PROJECT_ENVIRONMENT": "${CLAUDE_PLUGIN_DATA}/venv", "COLGREP_MCP_ROOT": "${CLAUDE_PROJECT_DIR}", "PATH": "/opt/homebrew/bin:/usr/local/bin:${HOME}/.cargo/bin:${HOME}/.local/bin:${PATH}"}`. Verify from the plugins reference whether `${HOME}` and `${PATH}` are expanded inside plugin `.mcp.json` env values; if not, use `$HOME`-free absolute fallbacks and document the limitation in a comment-bearing sibling `README` (JSON has no comments).
3. `plugin.json` (Agent Plugins 1.0): exactly `$schema: "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"`, `name: "colgrep-mcp"`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords` — nothing else.
4. `mcp.json` (Agent Plugins 1.0): `$schema: "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"`, `mcpServers.colgrep = {type: "stdio", command: "uv", args: ["run","--quiet","--directory","${PLUGIN_ROOT}/server","colgrep-mcp"], env: {"UV_PROJECT_ENVIRONMENT": "${PLUGIN_DATA}/venv"}}` — no `COLGREP_MCP_ROOT` (the spec offers no project-dir placeholder; the server falls back to cwd), no `PLUGIN_ROOT`/`PLUGIN_DATA` keys in env (forbidden by spec).
5. `.codex-plugin/plugin.json`: mirror the cell plugin's shape (`name`, `version`, `description`, `author`, `repository`, `keywords`, `skills: "./skills/"`, `mcpServers: "./.mcp.json"`, `interface{displayName, shortDescription, longDescription, developerName, category: "Developer Tools", capabilities: ["Read"], defaultPrompt: [...]}`).
6. `.claude-plugin/marketplace.json` (`name: "colgrep-mcp"`, owner, one plugin with `source: "./"`) and `.agents/plugins/marketplace.json` (mirror cell's, `source: {source: "local", path: "./"}`). If `claude plugin validate` rejects a marketplace whose plugin source is the repo root, use `source: "."` or move nothing — record what worked.
7. `skills/` must exist for the manifests to validate: create `skills/colgrep-search/.gitkeep` only if the `agent_skill` leaf has not landed yet (it is a sibling; do not write SKILL.md here).
Run `claude plugin validate .` and iterate until it passes.
**References**: [R01 §Packaging layout](../../../__reports__/colgrep_mcp/00-architecture_v0.md) — launch command and env variables
**Deliverables**: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`, `plugin.json`, `mcp.json`, `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`
**Consistency Checks**: `claude plugin validate .` (expected: PASS)
**Commit**: `build(plugin): add Claude Code, Agent Plugins 1.0 and Codex manifests launching colgrep-mcp via uv`

## Step 2: Manifest consistency tests
**Goal**: Keep the seven JSON files from drifting apart on version bumps.
**Implementation Logic**:
`server/tests/test_manifests.py` locates the repo root (`Path(__file__).parents[2]`), loads each manifest, and asserts: all `version` fields equal `colgrep_mcp.__version__`; Agent Plugins `plugin.json` keys ⊆ the ten permitted; `$schema` values exact; `mcp.json` `$schema` version segment equals `plugin.json`'s; both MCP configs launch `uv run ... colgrep-mcp` with the same args after substituting `${CLAUDE_PLUGIN_ROOT}`→`${PLUGIN_ROOT}`; no env key named `PLUGIN_ROOT`/`PLUGIN_DATA` in `mcp.json`; `.codex-plugin/plugin.json.name == .claude-plugin/plugin.json.name == plugin.json.name`.
**References**: Agent Plugins spec `https://agent-plugins.org/specification` — field whitelist
**Deliverables**: `server/tests/test_manifests.py` (`test_versions_aligned`, `test_agent_plugin_fields_whitelist`, `test_mcp_configs_equivalent`, `test_names_aligned`)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_manifests.py` (expected: PASS)
**Commit**: `test(plugin): guard manifest version and field consistency`
