# colgrep-mcp

An MCP server that exposes [colgrep](https://github.com/lightonai/next-plaid) — semantic, hybrid code search — as tools, resources and prompts so coding agents reach for semantic search natively instead of shelling out to `grep`.

Packaged as a Claude Code plugin and as an [Agent Plugins 1.0](https://agent-plugins.org) plugin.

Status: under construction. See `__roadmap__/colgrep_mcp/` and `__reports__/`.

## Packaging

The repository root is simultaneously:

- a [Claude Code](https://code.claude.com/docs/en/plugins-reference) plugin (`.claude-plugin/plugin.json`, `.mcp.json`) and a one-plugin marketplace (`.claude-plugin/marketplace.json`);
- an [Agent Plugins 1.0](https://agent-plugins.org/specification) plugin (`plugin.json`, `mcp.json`);
- a Codex plugin (`.codex-plugin/plugin.json`) and marketplace (`.agents/plugins/marketplace.json`).

All manifests launch the same server through `scripts/launch.sh`, which rebuilds a sane `PATH` (`$HOME/.local/bin`, `$HOME/.cargo/bin`, Homebrew) before running `uv run --quiet --directory <PLUGIN_ROOT>/server colgrep-mcp`. A script is used because plugin ecosystems expand only their own placeholders (`${CLAUDE_PLUGIN_ROOT}`, `${PLUGIN_ROOT}`, `${PLUGIN_DATA}`) inside MCP configs, never `$HOME` or `$PATH`, and GUI-launched clients often start without a login shell's `PATH`.
