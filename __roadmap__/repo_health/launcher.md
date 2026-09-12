# Cross-Platform Launch via uv

**Goal**: Launch the server from every plugin manifest with `uv run --quiet --directory <ROOT>/server colgrep-mcp`, delete the POSIX-only shell launcher, and make sure the repo's own `.mcp.json` does not break Claude Code when this repository is the project.
**Pre-conditions**:
- [ ] Branch `task/launcher` created from the campaign branch `claude/mcp-server-repo-health-e13188`
- [ ] `cd server && uv run pytest` passes before any change
- [ ] `claude --plugin-dir . mcp list` run from the repo root shows the colgrep server connected with the current `launch.sh` (baseline)
**Success Gates**:
- ✅ [static] `scripts/launch.sh` no longer exists; no file outside `__reports__/` and `__roadmap__/` mentions `launch.sh`
- ✅ [static] `.mcp.json` and `mcp.json` name `uv` as `command` and put the ecosystem placeholder only in `args`
- ✅ [behavioral] `claude --plugin-dir . mcp list` from the repo root shows the colgrep server `✔ Connected`
- ✅ [behavioral] `claude mcp list` from the repo root either shows colgrep connected or does not list it at all — never a spawn error
- ✅ [run] `cd server && uv run pytest -q tests/test_manifests.py` passes with assertions updated to the new contract
- ✅ [static] README Install, Any-MCP-client, Troubleshooting and Packaging sections describe the `uv` launch and the PATH recipe
**References**: [R01 §C3, Risks 1 and 3](../../__reports__/repo_health/00-architecture_v0.md) — launch contract; [Agent Plugins 1.0 spec](https://agent-plugins.org/specification) — where placeholders may appear; Claude Code plugins reference (https://code.claude.com/docs/en/plugins-reference) — `.mcp.json` placeholders and the `mcpServers` manifest field; [0.1.0 retrospective, Open Questions](../../__reports__/colgrep_mcp/03-knowledge_transfer_v0.md) — Codex placeholder expansion unverified

## Step 1: Verify the placeholder rules before changing anything
**Goal**: Know, from the specs, where `${CLAUDE_PLUGIN_ROOT}` / `${PLUGIN_ROOT}` may legally appear and how Claude Code treats a root `.mcp.json` in project versus plugin context.
**Implementation Logic**:
Read the Agent Plugins 1.0 specification (WebFetch) for `mcp.json`: is a placeholder allowed in `args`? in `env` values? what is the process cwd? Read the Claude Code plugins reference for `.mcp.json` placeholder expansion and for whether `mcpServers` in `.claude-plugin/plugin.json` may point at a file outside the plugin root's default location. Check whether Claude Code's project-level `.mcp.json` supports `${VAR:-default}` env expansion (it is documented for project configs). Record the answers, with the URL and the quoted sentence for each, in `__reports__/repo_health/00-findings_launch_placeholders_v0.md` (findings report, ≤ 1 page: a table `Ecosystem | Field | Placeholder allowed? | Source`). Decide and write down which of these two options the next step will implement: (a) keep the root `.mcp.json` and make it valid in both contexts, e.g. `--directory` `${CLAUDE_PLUGIN_ROOT:-.}/server` if the docs support the fallback syntax in both contexts; (b) move the Claude Code MCP config to `.claude-plugin/mcp.json` (or inline it into the two plugin manifests) so a project-level load no longer happens. Prefer (a) only if both contexts are documented to expand it; otherwise (b).
**Deliverables**: `__reports__/repo_health/00-findings_launch_placeholders_v0.md` (front matter per the findings template, table of placeholder rules, chosen option with rationale)
**Consistency Checks**: `test -f __reports__/repo_health/00-findings_launch_placeholders_v0.md` (expected: PASS)
**Commit**: `docs(reports): record where plugin ecosystems expand root placeholders before changing the launcher`

## Step 2: Launch through uv in every manifest and delete the shell launcher
**Goal**: One cross-platform launch argv, no shell.
**Implementation Logic**:
`.mcp.json` (Claude Code plugin): `"command": "uv"`, `"args": ["run", "--quiet", "--directory", "${CLAUDE_PLUGIN_ROOT}/server", "colgrep-mcp"]`, keep the `env` block. `mcp.json` (Agent Plugins 1.0): same shape with `${PLUGIN_ROOT}` if Step 1 found placeholders allowed in `args`; otherwise the documented fallback from Step 1, recorded as a DEVIATION in the commit body. Apply the Step 1 decision for the project-context problem; if option (b), update `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` `mcpServers` paths accordingly (these two files are otherwise untouched: their `version` stays `0.1.0`). `git rm scripts/launch.sh` (remove the directory if empty). Update `server/tests/test_manifests.py::test_mcp_configs_equivalent`: assert both configs use `command == "uv"`, that `args` end with `["--directory", "<placeholder>/server", "colgrep-mcp"]`, that no `command` contains a placeholder, and drop the executable-bit assertion; keep the other tests unchanged. Then run the two behavioural gates from the repo root: `claude --plugin-dir . mcp list` (must show connected) and `claude mcp list` (must not show a spawn error for colgrep). Paste both outputs into the commit body.
**Deliverables**: `.mcp.json`, `mcp.json` (`command: uv`, args with placeholder), possibly `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (`mcpServers` path), `scripts/launch.sh` deleted, `server/tests/test_manifests.py` (`test_mcp_configs_equivalent` rewritten; new helper `_launch_args`)
**Consistency Checks**: `cd server && uv run pytest -q tests/test_manifests.py` (expected: PASS); `claude plugin validate .` (expected: PASS); `claude --plugin-dir . mcp list 2>&1 | grep -i colgrep` (expected: contains "Connected"); `test ! -e scripts/launch.sh` (expected: PASS)
**Commit**: `fix(plugin): launch the server with uv run from every manifest so it works without a POSIX shell`

## Step 3: Update the README for the new launch path
**Goal**: Keep the human-facing landing page truthful.
**Implementation Logic**:
In `README.md`: Install → "register only the MCP server" becomes `claude mcp add colgrep -- uv run --quiet --directory /path/to/colgrep-mcp/server colgrep-mcp`; "Agent Plugins 1.0 clients" and "Any MCP client" describe the `uv run` command; Troubleshooting → replace the `launch.sh` PATH bullet with: GUI-launched clients may start without your shell's PATH — name `uv` by absolute path in the client config (`which uv` / `where uv`) and set `COLGREP_MCP_BINARY` to the absolute colgrep path; Packaging → all manifests run `uv run --quiet --directory <ROOT>/server colgrep-mcp` with the ecosystem's own root placeholder, and once the package is on PyPI this becomes `uvx colgrep-mcp`. Mention Windows explicitly once (uv, colgrep and Python are all available there; the server itself is untested on Windows until CI says otherwise). Do not touch the Tools table (a drift test parses it).
**Deliverables**: `README.md` (§Install, §Any MCP client, §Troubleshooting, §Packaging updated)
**Consistency Checks**: `COLGREP_BYPASS=1 grep -rn 'launch.sh' README.md .mcp.json mcp.json plugin.json .claude-plugin .codex-plugin skills server/colgrep_mcp server/tests CONTRIBUTING.md` (expected: no output); `cd server && uv run pytest -q tests/test_readme.py` (expected: PASS)
**Commit**: `docs(docs): describe the uv launch path, the PATH recipe for GUI clients and the PyPI follow-up`
