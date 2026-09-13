# colgrep-mcp

Semantic and hybrid code search for coding agents, as a stdio MCP server wrapping the [colgrep](https://github.com/lightonai/next-plaid) CLI. colgrep indexes a repository into code units (functions, classes, methods, Markdown sections) and ranks them with a ColBERT late-interaction model fused with keyword search; this package puts that in the agent's tool list, where it gets used instead of `grep`.

The full landing page — plugin installs for Claude Code, Codex and Agent Plugins 1.0 clients, troubleshooting, development — is the [repository README](https://github.com/CrackingShells/colgrep-mcp#readme).

## Requirements

- `colgrep` ≥ 1.6 on `PATH` (`cargo install colgrep`, or see the [next-plaid README](https://github.com/lightonai/next-plaid)); the first run downloads the embedding model.
- Python ≥ 3.11. With [`uv`](https://docs.astral.sh/uv/) nothing else: `uvx` fetches Python if needed.

## Run

One-off, resolved and cached by `uvx` on first start:

```bash
uvx colgrep-mcp
```

Installed once as a plain executable, with no per-start resolution:

```bash
uv tool install colgrep-mcp   # or: pipx install colgrep-mcp
colgrep-mcp
```

Either command is a stdio MCP server; register it in your client as such:

```json
{
  "mcpServers": {
    "colgrep": {
      "command": "uvx",
      "args": ["colgrep-mcp"],
      "env": { "COLGREP_MCP_ROOT": "/path/to/the/repo/to/search" }
    }
  }
}
```

`COLGREP_MCP_ROOT` is the project searched when a tool call names no path; without it the server falls back to the client's first root, then to its working directory. `COLGREP_MCP_BINARY` names the `colgrep` binary when it is not on `PATH`. The other variables (`COLGREP_MCP_TIMEOUT`, `COLGREP_MCP_TEXT_BUDGET`, `COLGREP_MCP_LOG_LEVEL`) are documented in the repository README.

## What the agent gets

### Tools

| Tool | Purpose |
|:--|:--|
| `search` | Ranked semantic or hybrid search over code units, with self-describing `hit_id`s. |
| `find_files` | Which files are about a topic, ranked and de-duplicated. |
| `expand` | Full source of hits already returned, by `hit_id`. |
| `index_status` | Whether a path is indexed, with which model, where, how big. |
| `index_build` | Build or refresh an index now, with progress notifications. |
| `index_clear` | Delete a project's index, after confirmation. |
| `index_prune` | Remove orphaned, machine-state, shadowed and (opt-in) cold indexes; dry run by default. |
| `list_indexes` | Every indexed project on this machine, with size, last use, path-exists and shadowing. |
| `doctor` | Environment self-check: binary, version, settings, default root. |

Resources (`colgrep://guide`, `colgrep://settings`, `colgrep://indexes`, `colgrep://status/{+path}`, `colgrep://errors`) and prompts (`explore`, `locate`, `impact`) come with it; the guide resource teaches the agent how to compose queries.

## License

GNU Affero General Public License v3.0 or later.
