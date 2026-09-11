# colgrep-mcp

An MCP server that exposes [colgrep](https://github.com/lightonai/next-plaid) — semantic, hybrid code search — as tools, resources and prompts so coding agents reach for semantic search natively instead of shelling out to `grep`.

Packaged as a Claude Code plugin and as an [Agent Plugins 1.0](https://agent-plugins.org) plugin.

Status: under construction. See `__roadmap__/colgrep_mcp/` and `__reports__/`.

## Packaging

The repository root is simultaneously:

- a [Claude Code](https://code.claude.com/docs/en/plugins-reference) plugin (`.claude-plugin/plugin.json`, `.mcp.json`) and a one-plugin marketplace (`.claude-plugin/marketplace.json`);
- an [Agent Plugins 1.0](https://agent-plugins.org/specification) plugin (`plugin.json`, `mcp.json`);
- a Codex plugin (`.codex-plugin/plugin.json`) and marketplace (`.agents/plugins/marketplace.json`).

All four manifests launch the same server: `uv run --quiet --directory <PLUGIN_ROOT>/server colgrep-mcp`.

**PATH limitation**: neither the Claude Code plugin docs nor the Agent Plugins 1.0 spec document expansion of arbitrary host environment variables (`${HOME}`, `${PATH}`) inside a stdio MCP server's `env` values — only each ecosystem's own placeholders (`${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_DATA}`/`${CLAUDE_PROJECT_DIR}` for Claude Code; `${PLUGIN_ROOT}`/`${PLUGIN_DATA}` for Agent Plugins, with unrecognized placeholders required to stay literal) are expanded. So `.mcp.json` and `mcp.json` fall back to a **literal, `$HOME`-free `PATH`** so GUI-launched clients that don't inherit a login shell's `PATH` can still find `uv`:

```
/opt/homebrew/bin:/usr/local/bin:/Users/me/.local/bin:/Users/me/.cargo/bin
```

The last two entries are this development machine's actual install locations (`uv` lives at `/Users/me/.local/bin/uv`) and are **not portable** — since neither manifest format lets us express "the invoking user's home directory," installing this plugin on another machine where `uv`/`colgrep` live outside `/opt/homebrew/bin` or `/usr/local/bin` requires editing this literal list (or symlinking `uv` into one of the two portable entries) until the plugin ecosystems document host-env expansion.
