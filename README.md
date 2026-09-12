# colgrep-mcp

Semantic and hybrid code search for coding agents, as an MCP server.

[colgrep](https://github.com/lightonai/next-plaid) indexes a repository into *code units* (functions, classes, methods, Markdown sections) and ranks them with a ColBERT late-interaction model fused with keyword search. It is fast and it understands meaning. It is also a CLI, and agents trained on `grep` rarely reach for it unprompted. `colgrep-mcp` puts the same capability in the agent's tool list, where it gets used.

One directory installs as a **Claude Code plugin**, an **[Agent Plugins 1.0](https://agent-plugins.org) plugin** (Codex, Cursor, GitHub Copilot, VS Code, Kiro) and a **Codex plugin**.

## Requirements

| Dependency | Why | Install |
|:--|:--|:--|
| `colgrep` ≥ 1.6 | does the indexing and ranking | `cargo install colgrep` or see the [next-plaid README](https://github.com/lightonai/next-plaid) |
| `uv` | creates the server's Python environment on first launch | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Python ≥ 3.11 | fetched automatically by `uv` if missing | — |

The first `colgrep` run downloads the embedding model (a few hundred MB) and the first index of a repository takes seconds to minutes depending on size. Everything after that is incremental.

## Install

### Claude Code

Try it without installing:

```bash
claude --plugin-dir /path/to/colgrep-mcp
```

Install from this repository acting as its own marketplace:

```bash
claude plugin marketplace add /path/to/colgrep-mcp
```

```bash
claude plugin install colgrep-mcp@colgrep-mcp
```

Or register only the MCP server, without the plugin's skill:

```bash
claude mcp add colgrep -- uv run --quiet --directory /path/to/colgrep-mcp/server colgrep-mcp
```

### Codex

Add the marketplace at `.agents/plugins/marketplace.json` from this repository, then install the `colgrep-mcp` plugin. The Codex manifest lives in `.codex-plugin/plugin.json`.

### Agent Plugins 1.0 clients (Cursor, Copilot, VS Code, Kiro, …)

Point the client at this directory. `plugin.json` and `mcp.json` at the root follow the 1.0.0 schemas; the server is declared as a `stdio` server launched by `uv run --quiet --directory ${PLUGIN_ROOT}/server colgrep-mcp`.

### Any MCP client

```bash
uv run --quiet --directory /path/to/colgrep-mcp/server colgrep-mcp
```

is a stdio MCP server. Set `COLGREP_MCP_ROOT` to the project you want searched by default. Windows is supported by this launch path (`uv`, `colgrep` and Python all ship for it), though the server itself is untested there until CI says otherwise.

## What the agent gets

### Tools

| Tool | Purpose |
|:--|:--|
| `search` | Ranked semantic or hybrid search over code units. Compact listing plus structured hits with self-describing `hit_id`s. |
| `find_files` | Which files are about a topic, ranked and de-duplicated. |
| `expand` | Full source of hits already returned, by `hit_id`, without reading whole files. |
| `index_status` | Whether a path is indexed, with which model, where, how big. |
| `index_build` | Build or refresh an index now, with progress notifications. |
| `index_clear` | Delete a project's index. Asks for confirmation (elicitation) or requires `confirm=true`. |
| `list_indexes` | Every indexed project on this machine. |
| `doctor` | Environment self-check: binary, version, settings, default root. |

`search` defaults to hybrid mode. Pass `pattern` (a regex) to pre-filter units by text before semantic ranking, `include`/`exclude`/`exclude_dir` to scope, `limit` to size the result. Text output is capped by a character budget; the full result is always in `structured_content`.

### Resources

| URI | Content |
|:--|:--|
| `colgrep://guide` | The agent guide: how to compose queries, when to use which tool. |
| `colgrep://settings` | colgrep's current configuration. |
| `colgrep://indexes` | Indexed projects. |
| `colgrep://status/{+path}` | Index status for a path. |
| `colgrep://errors` | Error and hint codes with the next step for each. |

### Prompts

`explore` (knowledge-acquisition loop for a question), `locate` (where a symbol or behaviour lives), `impact` (what a change touches). Each takes an optional `path`.

### Skill

`skills/colgrep-search/SKILL.md` teaches the agent when semantic search beats grep and how to sequence the tools. Claude Code loads it as `/colgrep-mcp:colgrep-search`.

## Configuration

| Variable | Default | Meaning |
|:--|:--|:--|
| `COLGREP_MCP_BINARY` | `colgrep` | Path to the colgrep binary |
| `COLGREP_MCP_ROOT` | unset | Default project root when a tool call gives no path (the Claude Code plugin sets it to the project directory) |
| `COLGREP_MCP_TIMEOUT` | `600` | Seconds allowed per colgrep invocation |
| `COLGREP_MCP_TEXT_BUDGET` | `12000` | Maximum characters of text content per tool result |
| `COLGREP_MCP_LOG_LEVEL` | `INFO` | Server log level (stderr) |
| `UV_PROJECT_ENVIRONMENT` | unset | Where `uv` keeps the server's virtualenv (plugins point it at their data directory) |

Without `COLGREP_MCP_ROOT` the server falls back to the client's first root, if the client offers roots, then to its working directory.

## Troubleshooting

- **The server does not start under a GUI client.** GUI-launched clients may start without your shell's `PATH`, so `uv` (and `colgrep`) may not resolve by bare name. Name `uv` by its absolute path in the client's MCP config (find it with `which uv` on macOS/Linux or `where uv` on Windows), and set `COLGREP_MCP_BINARY` to the absolute path of `colgrep` if it isn't found either.
- **A search times out on a large repository.** Call `index_build` first; it streams progress and the following searches are fast. `index_status` says whether that is needed.
- **`doctor` reports a problem.** Its `problems` list names what is missing and how to fix it.
- **`index_clear` refuses.** colgrep folds a directory into the nearest already-indexed ancestor project. The tool tells you the project root it would clear; pass that root explicitly if that is really intended.
- **Line numbers.** colgrep 1.6 reports wrong `line`/`end_line` for most units. The server re-locates every unit from its source text and flags `location_verified` on each hit.

## Development

```bash
cd server && uv run pytest -q
```

Tests run against a fake `colgrep` (`server/tests/fake_colgrep.py`); set `COLGREP_MCP_REAL=1` to include the few that need the real binary. Architecture, measured behaviour and decisions live in `__reports__/colgrep_mcp/`; the execution plan in `__roadmap__/colgrep_mcp/`; commit conventions in `CONTRIBUTING.md`.

`server/tests/e2e/run_e2e.py` is a separate, non-pytest script (no `test_` prefix, so `pytest` never collects it) that drives the assembled server over stdio against a **real** `colgrep` binary and a real repository, for measured end-to-end validation rather than fixture-driven unit tests:

```bash
cd server && uv run python tests/e2e/run_e2e.py --corpus /path/to/a/real/repo
cd server && uv run python tests/e2e/run_e2e.py --corpus /path/to/a/real/repo --dry-run  # print the call plan, exit 0
```

It refuses to run against this repository/its worktrees or anything under `/private/tmp` (colgrep folds such paths into whichever project already anchors that prefix — see `__reports__/colgrep_mcp/02-architecture_v1.md` D3). Findings from the latest run live in `__reports__/colgrep_mcp/02-findings_e2e_validation_v0.md`.

## Packaging

The repository root is simultaneously:

- a [Claude Code](https://code.claude.com/docs/en/plugins-reference) plugin (`.claude-plugin/plugin.json`, `.claude-plugin/mcp.json`) and a one-plugin marketplace (`.claude-plugin/marketplace.json`);
- an [Agent Plugins 1.0](https://agent-plugins.org/specification) plugin (`plugin.json`, `mcp.json`);
- a Codex plugin (`.codex-plugin/plugin.json`) and marketplace (`.agents/plugins/marketplace.json`).

All manifests launch the same argv directly, with no shell script in between: `uv run --quiet --directory <ROOT>/server colgrep-mcp`, where `<ROOT>` is the launching ecosystem's own root placeholder (`${CLAUDE_PLUGIN_ROOT}` for the Claude Code manifest at `.claude-plugin/mcp.json`, `${PLUGIN_ROOT}` for the Agent Plugins 1.0 `mcp.json`), placed in `args` only — plugin ecosystems forbid placeholder expansion in `command`, and a bare `uv` there resolves the same way in every context, including when this repository is opened as a plain project rather than loaded as a plugin. `uv` and `colgrep` must be on `PATH` (see Troubleshooting for GUI clients that start without one); this is true on Windows as well as macOS and Linux. Once `colgrep-mcp` is published to PyPI, every manifest's `args` collapses to a one-line `uvx colgrep-mcp`.

## License

MIT — see `LICENSE`.
