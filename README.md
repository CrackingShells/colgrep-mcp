# colgrep-mcp

Semantic and hybrid code search for coding agents, as an MCP server.

[colgrep](https://github.com/lightonai/next-plaid) indexes a repository into *code units* (functions, classes, methods, Markdown sections) and ranks them with a ColBERT late-interaction model fused with keyword search. It is fast and it understands meaning. It is also a CLI, and agents trained on `grep` rarely reach for it unprompted. `colgrep-mcp` puts the same capability in the agent's tool list, where it gets used.

One directory installs as a **Claude Code plugin**, an **[Agent Plugins 1.0](https://agent-plugins.org) plugin** (Codex, Cursor, GitHub Copilot, VS Code, Kiro) and a **Codex plugin**.

## Requirements

| Dependency | Why | Install |
|:--|:--|:--|
| `colgrep` ≥ 1.6 | does the indexing and ranking | `cargo install colgrep` or see the [next-plaid README](https://github.com/lightonai/next-plaid) |
| `uv` | `uvx` fetches the server from PyPI and caches it on first launch | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Python ≥ 3.11 | fetched automatically by `uv` if missing | — |

The first `colgrep` run downloads the embedding model (a few hundred MB) and the first index of a repository takes seconds to minutes depending on size. Everything after that is incremental.

## Install

The server is the [`colgrep-mcp` package on PyPI](https://pypi.org/project/colgrep-mcp/); every plugin manifest launches it as `uvx colgrep-mcp==<version>`, pinned to the plugin's own version. The repository is public, so every ecosystem can add it as a remote marketplace/plugin source directly from GitHub — no clone required. Two other paths are first class: an installed executable with no per-start resolution ([Any MCP client](#any-mcp-client)), and a clone, for a tree you edit or a machine that must not fetch from PyPI at start ([From a local clone](#from-a-local-clone)).

### Claude Code

```bash
claude plugin marketplace add CrackingShells/colgrep-mcp
```

```bash
claude plugin install colgrep-mcp@colgrep-mcp
```

Add `--scope project` to the marketplace command to declare it in the repository's own `.claude/settings.json` instead of your user settings, so teammates who open this project pick it up too.

### Codex

```bash
codex plugin marketplace add CrackingShells/colgrep-mcp
```

```bash
codex plugin add colgrep-mcp@colgrep-mcp-marketplace
```

The Codex manifests are `.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`. These commands follow the Codex plugin documentation and have not yet been exercised end to end; a report of a working (or failing) install is welcome as an issue.

### Agent Plugins 1.0 clients (Cursor, GitHub Copilot, VS Code, Kiro)

The [Agent Plugins 1.0 spec](https://agent-plugins.org/specification) defines the plugin package (`plugin.json`, `mcp.json`) but explicitly leaves installation, distribution and marketplaces to each client — there is no spec-defined command for installing straight from a git URL. Check that client's own plugin or extension docs for how it adds a plugin from a repository; until then, point it at a local clone the way it expects a plugin directory (below).

### Any MCP client

Each of these is a stdio MCP server; register whichever you prefer in the client's MCP config with `COLGREP_MCP_ROOT` set to the project to search by default (see [Configuration](#configuration)).

```bash
uvx colgrep-mcp
```

resolves and caches the latest release on first start, then reuses the cached environment. If you would rather not pay that per-start check, install once and run a plain executable:

```bash
uv tool install colgrep-mcp   # or: pipx install colgrep-mcp
```

```bash
colgrep-mcp
```

For Claude Code without the plugin's skill: `claude mcp add colgrep -- uvx colgrep-mcp` (or `-- colgrep-mcp` after `uv tool install`). Windows is supported: no launch path needs a shell, and the test suite runs green on Windows in CI.

### From a local clone

```bash
git clone https://github.com/CrackingShells/colgrep-mcp.git
```

The clone is the tree you edit, and the way to run the server on a machine that must not fetch from PyPI at start. Install it once as an executable (re-run after `git pull`):

```bash
uv tool install /path/to/colgrep-mcp/server
```

Or run the tree directly, picking up edits without reinstalling:

```bash
claude mcp add colgrep -- uv run --quiet --directory /path/to/colgrep-mcp/server colgrep-mcp
```

`uvx --from /path/to/colgrep-mcp/server colgrep-mcp` is the one-off equivalent. Note that `claude --plugin-dir /path/to/colgrep-mcp` loads the clone's *skill* but launches the manifest's PyPI pin, not the clone's code — use one of the commands above to test a change.

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

Without `COLGREP_MCP_ROOT` the server falls back to the client's first root, if the client offers roots, then to its working directory.

## Troubleshooting

- **The server does not start under a GUI client.** GUI-launched clients may start without your shell's `PATH`, so `uvx` (and `colgrep`) may not resolve by bare name. Name `uvx` by its absolute path in the client's MCP config (find it with `which uvx` on macOS/Linux or `where uvx` on Windows), and set `COLGREP_MCP_BINARY` to the absolute path of `colgrep` if it isn't found either.
- **The first start is slow, or fails offline.** `uvx colgrep-mcp==<version>` downloads the package and its dependencies once per version, then runs from cache. On a machine without network at start, `uv tool install colgrep-mcp` beforehand and launch the `colgrep-mcp` executable instead (see [Any MCP client](#any-mcp-client)).
- **A search times out on a large repository.** Call `index_build` first; it streams progress and the following searches are fast. `index_status` says whether that is needed.
- **`doctor` reports a problem.** Its `problems` list names what is missing and how to fix it.
- **`index_clear` refuses.** colgrep folds a directory into the nearest already-indexed ancestor project. The tool tells you the project root it would clear; pass that root explicitly if that is really intended.
- **Line numbers.** colgrep 1.6 reports wrong `line`/`end_line` for most units. The server re-locates every unit from its source text and flags `location_verified` on each hit.

## Development

```bash
cd server && uv run pytest -q
```

If you are a coding agent maintaining this repository, start with `AGENTS.md`: repo map, gate commands, conventions and known traps.

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
- a Codex plugin (`.codex-plugin/plugin.json`, `.codex-plugin/mcp.json`) and marketplace (`.agents/plugins/marketplace.json`).

Every MCP manifest launches the same argv, with no shell script and no root placeholder: `uvx colgrep-mcp==<version>`, where the pin is the plugin's own version — `cz bump` rewrites it with the manifests' `version` fields, so a plugin update always launches its matching server and never a stale cached one. The only placeholder left is `COLGREP_MCP_ROOT=${CLAUDE_PROJECT_DIR}` in the Claude Code manifest's `env`, the one client documented to expand it. `uvx` and `colgrep` must be on `PATH` (see Troubleshooting for GUI clients that start without one). CI runs the suite on Windows as well as macOS and Linux, builds the distribution and checks its metadata on every pull request; pushing a release tag runs `.github/workflows/publish.yml`, which uploads to PyPI through trusted publishing and creates the GitHub release.

## License

GNU Affero General Public License v3.0 or later — see `LICENSE`. Modified versions that are distributed, or run as a network service (for example the `streamable-http` transport offered to others), must be published under the same terms.
