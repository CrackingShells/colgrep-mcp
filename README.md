# colgrep-mcp

Semantic and hybrid code search for coding agents, as an MCP server.

[colgrep](https://github.com/lightonai/next-plaid) indexes a repository into *code units* (functions, classes, methods, Markdown sections) and ranks them with a ColBERT late-interaction model fused with keyword search. It is fast and it understands meaning. It is also a CLI, and agents trained on `grep` rarely reach for it unprompted. `colgrep-mcp` puts the same capability in the agent's tool list, where it gets used.

This is an independent project. It is not affiliated with or supported by [LightOn](https://www.lighton.ai), who make colgrep. A problem with the search tools belongs in this repository's issues, a problem with colgrep itself in [next-plaid](https://github.com/lightonai/next-plaid/issues).

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
claude plugin install colgrep-mcp@cracking-shells
```

Add `--scope project` to the marketplace command to declare it in the repository's own `.claude/settings.json` instead of your user settings, so teammates who open this project pick it up too.

### Codex

```bash
codex plugin marketplace add CrackingShells/colgrep-mcp
```

```bash
codex plugin add colgrep-mcp@cracking-shells
```

The Codex manifests are `.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`.

### Agent Plugins 1.0 clients (Cursor, GitHub Copilot, VS Code, Kiro)

The [Agent Plugins 1.0 spec](https://agent-plugins.org/specification) defines the plugin package (`plugin.json`, `mcp.json`) and leaves installation, distribution and marketplaces to each client, so the install command is the client's own. Each of these clients can add a plugin straight from this repository; its plugin or extension docs name the command.

For example, in VS Code:

1. Open the Command Palette (`Cmd`+`Shift`+`P` on macOS, `Ctrl`+`Shift`+`P` elsewhere).
2. Run **Chat: Install Plugin from Source**.
3. Choose the git repository option and enter `CrackingShells/colgrep-mcp` (the full URL `https://github.com/CrackingShells/colgrep-mcp` works too).

A client without such a command takes a local clone as its plugin directory ([From a local clone](#from-a-local-clone)).

### Any MCP client

Each of these is a stdio MCP server; register whichever you prefer in the client's MCP config with `COLGREP_MCP_ROOT` set to the project to search by default (see [Configuration](#configuration)).

```bash
uvx colgrep-mcp
```

resolves and caches the latest release on first start, then reuses that cached environment on every later start — it does not upgrade by itself. `uvx colgrep-mcp@latest` re-resolves against PyPI on every start instead, so it always runs the newest release at the cost of a network round-trip per launch (and it fails offline). If you would rather not pay any per-start check, install once and run a plain executable, upgrading when you choose:

```bash
uv tool install colgrep-mcp   # or: pipx install colgrep-mcp
```

```bash
colgrep-mcp
```

```bash
uv tool upgrade colgrep-mcp   # later, on your own schedule
```

The plugin manifests use none of these: they pin `uvx colgrep-mcp==<plugin version>` so that upgrading the plugin is what upgrades the server, never a background resolution.

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
| `index_prune` | Remove orphaned, machine-state, shadowed and (opt-in) cold indexes. Dry run by default; `confirm=true` or elicitation to delete. |
| `list_indexes` | Every indexed project on this machine, with size, last use, whether the path still exists and who shadows it; `stale_only` filters. |
| `doctor` | Environment self-check: binary, version, settings, default root; hints at a stale index store. |

`search` defaults to hybrid mode. Pass `pattern` (a regex) to pre-filter units by text before semantic ranking, `include`/`exclude`/`exclude_dir` to scope, `limit` to size the result. Text output is capped by a character budget; the full result is always in `structured_content`.

### Resources

| URI | Content |
|:--|:--|
| `colgrep://guide` | The agent guide: how to compose queries, when to use which tool. |
| `colgrep://settings` | colgrep's current configuration. |
| `colgrep://indexes` | Indexed projects, with size, last use, path-exists and shadowing per index. |
| `colgrep://status/{+path}` | Index status for a path. |
| `colgrep://errors` | Error and hint codes with the next step for each. |

### Prompts

`explore` (knowledge-acquisition loop for a question), `locate` (where a symbol or behaviour lives), `impact` (what a change touches) — each takes an optional `path` — and `housekeeping` (review and prune the index store; optional `days`).

### Skill

`skills/colgrep-search/SKILL.md` teaches the agent when semantic search beats grep and how to sequence the tools. Claude Code loads it as `/colgrep-mcp:colgrep-search`.

### Hooks

The plugin also ships harness hooks (`hooks/`), so the policy the skill teaches is enforced rather than suggested. One dependency-free Python script, launched as `uv run --no-project python` (about 0.1 s per call, no requirement beyond the `uv` the server already needs), serves three events:

| Event | What it does |
|:--|:--|
| `SessionStart`, `SubagentStart` | Injects a short search policy (about 250 tokens) naming the MCP tools, what stays allowed, and the bypass. |
| `PreToolUse` on `Grep` and `Bash` | Denies the built-in Grep tool and shell corpus searches (`grep -r`, `rg`, `find -exec grep`, `xargs grep`) inside a source corpus, with a reason naming `search`, `find_files` and `expand`. Single-file grep, `cmd \| grep`, `grep -c`/`-v`/`-o`, `rg --files` and file-name lookup stay allowed. Targets that are machine state (hidden directories, `~/Library`, temp directories outside a git work tree) are never gated. Prefix `COLGREP_BYPASS=1` to a command colgrep cannot serve. |
| `WorktreeRemove` (Claude Code only) | Clears the colgrep index a removed worktree owned, never one it was folded into. |

`hooks/hooks.json` holds only events that Claude Code, Codex and Cursor all understand; `hooks/claude-code.json` holds the Claude-only event. Claude Code loads `hooks/hooks.json` on its own and reads the manifest's `hooks` field as additional files only, so the Claude Code manifest names just `hooks/claude-code.json`: a manifest that lists the default file too fails to load at install time with "Duplicate hooks file detected". Codex loads a plugin's `hooks/hooks.json` (its manifest names that file explicitly) and sets `CLAUDE_PLUGIN_ROOT` for it, but skips the hooks until you trust them once in `/hooks`. Cursor imports Claude Code hooks from `settings.json` files, not from plugins, so a Cursor project copies the three `hooks.json` entries into its `.claude/settings.json`. Agent Plugins 1.0 defines no hooks component and ignores the directory.

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
- **The plugin fails to connect right after an update.** `uv` caches PyPI's index page for a while, so a version published minutes ago can look nonexistent to it and the launch dies silently. Run `uvx --refresh colgrep-mcp==<version> --version` once (the version is in the plugin's `mcp.json`), then reconnect.
- **The first start is slow, or fails offline.** `uvx colgrep-mcp==<version>` downloads the package and its dependencies once per version, then runs from cache. On a machine without network at start, `uv tool install colgrep-mcp` beforehand and launch the `colgrep-mcp` executable instead (see [Any MCP client](#any-mcp-client)).
- **A search times out on a large repository.** Call `index_build` first; it streams progress and the following searches are fast. `index_status` says whether that is needed.
- **`doctor` reports a problem.** Its `problems` list names what is missing and how to fix it.
- **The hooks do not fire.** Plugin hooks are read when the plugin loads: after an install or update, run `/reload-plugins` or start a new session, then check `/hooks` for the entries under Plugin Hooks. In Codex, open `/hooks` and trust the plugin's hooks; they are skipped until then.
- **A shell command was denied.** That is the plugin's `PreToolUse` hook, not colgrep: the reason names the MCP tool to call instead. For a target colgrep cannot index (extensionless or lock files, an inverted match), prefix the command with `COLGREP_BYPASS=1`.
- **`index_clear` refuses.** colgrep folds a directory into the nearest already-indexed ancestor project. The tool tells you the project root it would clear; pass that root explicitly if that is really intended.
- **Line numbers.** colgrep 1.6 reports wrong `line`/`end_line` for most units. The server re-locates every unit from its source text and flags `location_verified` on each hit.

## For agents, by agents

Everyone who touches this repository is an LLM agent. Users reach it through the MCP tools, and the maintenance itself is handed to a coding agent, at present Claude Fable 5.1 in Claude Code: it reads the architecture reports, plans the work as a roadmap, implements in its own git worktree, writes the tests and the docs, and opens the pull request. The MCP server and the skill are the two layers made for the human and the agent to talk to each other; everything else, from the drift tests to the maintainer skills in `dev/`, is optimised for an agent picking the work up cold.

A change goes through an ordinary pull-request cycle. The agent commits with the vocabulary `cz check` enforces (`CONTRIBUTING.md`), pushes a branch and opens the PR; CI runs ruff, the test suite on Linux, macOS and Windows, the commit check and a build; the maintainer reads the diff and the PR body, then merges; a release is a `cz bump` on `main` and a tag push, which publishes to PyPI. Larger work runs as a campaign: an architecture report under `__reports__/`, a roadmap under `__roadmap__/`, one worktree per leaf, a read-only reviewer pass, and a retrospective whose lessons become the next revision of the `dev/` skills.

This holds because the agent is a frontier model and because the maintainer, who has built MCP servers before, reads every diff. The tests, the drift guards and the reports exist so that the trust placed in the agent is verified at each merge rather than assumed; the same process with a weaker model, or with merges nobody reads, would drift.

## Development

```bash
cd server && uv run pytest -q
```

If you are a coding agent maintaining this repository, start with `AGENTS.md`: repo map, gate commands, conventions and known traps.

Tests run against a fake `colgrep` (`server/tests/fake_colgrep.py`); set `COLGREP_MCP_REAL=1` to include the few that need the real binary. Architecture, findings and retrospectives live under `__reports__/`, one directory per campaign; the roadmaps under `__roadmap__/`; commit conventions in `CONTRIBUTING.md`.

`server/tests/e2e/run_e2e.py` is a separate, non-pytest script (no `test_` prefix, so `pytest` never collects it) that drives the assembled server over stdio against a **real** `colgrep` binary and a real repository, for measured end-to-end validation rather than fixture-driven unit tests:

```bash
cd server && uv run python tests/e2e/run_e2e.py --corpus /path/to/a/real/repo
cd server && uv run python tests/e2e/run_e2e.py --corpus /path/to/a/real/repo --dry-run  # print the call plan, exit 0
```

It refuses to run against this repository, its worktrees or anything under `/private/tmp`: colgrep folds such paths into whichever project already anchors that prefix, and the driver builds and clears indexes.

## Packaging

The repository root is simultaneously:

- a [Claude Code](https://code.claude.com/docs/en/plugins-reference) plugin (`.claude-plugin/plugin.json`, `.claude-plugin/mcp.json`) and a one-plugin marketplace (`.claude-plugin/marketplace.json`);
- an [Agent Plugins 1.0](https://agent-plugins.org/specification) plugin (`plugin.json`, `mcp.json`);
- a Codex plugin (`.codex-plugin/plugin.json`, `.codex-plugin/mcp.json`) and marketplace (`.agents/plugins/marketplace.json`).

The Claude Code and Codex plugins share the `hooks/` component ([Hooks](#hooks)); its commands carry the one placeholder both ecosystems expand, `${CLAUDE_PLUGIN_ROOT}`. Every MCP manifest launches the same argv, with no shell script and no root placeholder: `uvx colgrep-mcp==<version>`, where the pin is the plugin's own version — `cz bump` rewrites it with the manifests' `version` fields, so a plugin update always launches its matching server and never a stale cached one. The only placeholder left is `COLGREP_MCP_ROOT=${CLAUDE_PROJECT_DIR}` in the Claude Code manifest's `env`, the one client documented to expand it. `uvx` and `colgrep` must be on `PATH` (see Troubleshooting for GUI clients that start without one). CI runs the suite on Windows as well as macOS and Linux, builds the distribution and checks its metadata on every pull request; pushing a release tag runs `.github/workflows/publish.yml`, which uploads to PyPI through trusted publishing and creates the GitHub release.

## License

GNU Affero General Public License v3.0 or later — see `LICENSE`. Modified versions that are distributed, or run as a network service (for example the `streamable-http` transport offered to others), must be published under the same terms.
