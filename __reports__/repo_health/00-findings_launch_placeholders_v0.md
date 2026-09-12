---
type: findings
topic: repo_health
date: 2026-09-12
version: v0
prior-version: none
key-metric: contexts-verified: 3 (prior: N/A, delta: N/A)
decision-required: confirm
---

# Launch placeholder rules across the three plugin ecosystems

## Headline Result

`command` must never carry a placeholder in any ecosystem, so Step 2 puts a
bare `uv` there and moves `${CLAUDE_PLUGIN_ROOT}` / `${PLUGIN_ROOT}` into
`args`. That alone does not close the observed bug: Claude Code's
plugin-substitution mechanism for `${CLAUDE_PLUGIN_ROOT}` is documented only
as a bare placeholder — the docs are silent on whether `${VAR:-default}`
fallback syntax (confirmed for *project*-scope `.mcp.json`) also applies
inside the *plugin*-loading substitution path. Since both contexts are not
documented to expand the same fallback syntax, this report chooses **option
(b)**: move the Claude Code manifest to `.claude-plugin/mcp.json` so the root
is never auto-discovered as project config in the first place, rather than
relying on an unverified `${CLAUDE_PLUGIN_ROOT:-.}` fallback (option a).

## Results table

| Ecosystem | Field | Placeholder allowed? | Source |
|:--|:--|:--|:--|
| Agent Plugins 1.0 `mcp.json` | `command` | **No** — "Clients MUST NOT perform placeholder expansion in `command`." | [spec §7.2.1](https://agent-plugins.org/specification) |
| Agent Plugins 1.0 `mcp.json` | `args` | **Yes** — "Expansion applies to every string element of `args`, every string value in `env`, and the `cwd` string." | [spec §9.2](https://agent-plugins.org/specification) |
| Agent Plugins 1.0 `mcp.json` | `env` values | Yes (same §9.2 sentence); env **keys** `PLUGIN_ROOT`/`PLUGIN_DATA` are forbidden (existing test) | [spec §9.2](https://agent-plugins.org/specification) |
| Agent Plugins 1.0 `mcp.json` | any field, `${VAR:-default}` fallback | **No** — "Unrecognized placeholder-like text MUST remain literal. Clients MUST NOT perform any other placeholder or environment-variable expansion." | [spec §9.2](https://agent-plugins.org/specification) |
| Claude Code plugin `.mcp.json` (loaded via `.claude-plugin/plugin.json`) | `command`, `args`, `env` | **Yes**, bare placeholder only — "Which fields substitute them inline depends on the plugin component... MCP `stdio` servers: `command`, `args`, `env`" | [plugins-reference §Environment variables](https://code.claude.com/docs/en/plugins-reference) |
| Claude Code plugin `.mcp.json`, `${CLAUDE_PLUGIN_ROOT:-default}` fallback | — | **Undocumented** — the docs show only bare-placeholder substitution; no example or statement covers `:-default` in the plugin substitution path | [plugins-reference §Environment variables](https://code.claude.com/docs/en/plugins-reference) |
| Claude Code **project-scope** `.mcp.json`, `${VAR:-default}` fallback | `command`, `args`, `env`, `url`, `headers` | **Yes** — "`${VAR:-default}`: expands to `VAR` if set, otherwise uses `default`" | [docs §Environment variable expansion in .mcp.json](https://code.claude.com/docs/en/mcp) |
| `.claude-plugin/plugin.json` `mcpServers` field | path | Can point anywhere via a relative path (e.g. `"./.claude-plugin/mcp.json"`); project auto-discovery only ever looks for a root-level `.mcp.json`, so a relocated file is invisible to it | [plugins-reference §File locations reference](https://code.claude.com/docs/en/plugins-reference) |

## Observations

- The observed failure (`ENOENT ... posix_spawn '${CLAUDE_PLUGIN_ROOT}/scripts/launch.sh'`) happened because the root `.mcp.json` put the placeholder in `command`, and Claude Code's project-scope loader — which has no notion of `CLAUDE_PLUGIN_ROOT` — left the string unexpanded and tried to execute it literally as a path.
- Putting the placeholder only in `args` and a bare `uv` in `command` (Step 2) removes the spawn-level crash even in the *project* context: `uv` resolves on `PATH`, the process spawns, and only the `--directory` argument would be a stale/literal string. That downgrades the failure mode from a spawn exception to (at worst) an ordinary connection failure — satisfying the leaf's gate — but still means the project-scope colgrep entry does something confusing if the repo is ever opened directly as a project.
- Relocating the file (option b) removes that residual confusion entirely: a root-level project open no longer discovers any `mcpServers.colgrep` entry at all, matching the Success Gate "does not list it at all — never a spawn error".
- Codex's `.codex-plugin/plugin.json` currently points at the same `./.mcp.json` the Claude Code plugin uses. Whether Codex expands `${CLAUDE_PLUGIN_ROOT}` at all is the open question already on record (see Pointers) and is out of this leaf's scope; moving the shared file to `.claude-plugin/mcp.json` and repointing both `mcpServers` fields keeps today's (already-unverified) Codex behavior unchanged rather than fixing or breaking it further.

## Steering Questions

- Is the silence on `${VAR:-default}` inside the plugin-substitution path worth an upstream doc/behavior request to Claude Code, given it would let option (a) work uniformly later?
- Should the shared `.claude-plugin/mcp.json` eventually be split per-ecosystem once the Codex placeholder question (see Pointers) is answered, instead of three manifests pointing at one file?

## Pointers

- Chosen option for Step 2: **(b)** — move the Claude Code MCP manifest to `.claude-plugin/mcp.json`; update `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` `mcpServers` paths to match; root `.mcp.json` is deleted.
- Unverified Codex question carried over unresolved: `__reports__/colgrep_mcp/03-knowledge_transfer_v0.md` §Open Questions — "Will Codex expand `${CLAUDE_PLUGIN_ROOT}` in the shared `.mcp.json`?"
- Contract this implements: `__reports__/repo_health/00-architecture_v0.md` §C3, Risks 1 and 3.
