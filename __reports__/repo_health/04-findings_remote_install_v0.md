---
type: findings
topic: repo_health
date: 2026-09-12
version: v0
prior-version: none
key-metric: ecosystems-with-remote-install-verified: 1 of 3 (prior: N/A, delta: N/A)
decision-required: confirm
---

# Remote install from GitHub, per plugin ecosystem

## Headline Result

Now that `CrackingShells/colgrep-mcp` is public, Claude Code's remote install
path works exactly as documented and was verified end-to-end on this
machine: `claude plugin marketplace add CrackingShells/colgrep-mcp` clones the
repo, resolves the marketplace's `"source": "./"` entry against that clone,
and `claude plugin install colgrep-mcp@colgrep-mcp` connects the bundled
server. Codex has an equivalent `plugin marketplace add <owner/repo>` /
`plugin add <plugin>@<marketplace>` pair, grounded in the Codex CLI's own
source, but there is no Codex CLI on this machine to exercise it — documented
only. Agent Plugins 1.0 (Cursor, GitHub Copilot, VS Code, Kiro) has no
remote-install mechanism at all: the spec explicitly puts distribution and
installation outside its scope, so each client's own docs are the only place
a git-based install could be described, and none was found. The one thing
worth a second look before calling this done: our marketplace `name` and
plugin `name` are both `colgrep-mcp`, which is why the working install
command reads `colgrep-mcp@colgrep-mcp` — functional, confirmed by the
verification run below, but visually redundant.

## Results table

| Ecosystem | Remote install mechanism | Verified here? | Source |
|:--|:--|:--|:--|
| Claude Code | `claude plugin marketplace add owner/repo` (clones repo, resolves relative `source` paths against the clone) then `claude plugin install <plugin>@<marketplace>` | **Yes** — see Verification below | [plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces): "Add a marketplace from a GitHub repository, git URL, remote URL, or local path." and "Claude Code resolves relative paths against a local copy of the marketplace, so they work when users add your marketplace from a git source or a local directory." |
| Codex | `codex plugin marketplace add <SOURCE>` where `SOURCE` accepts `owner/repo[@ref]` or an HTTPS/SSH git URL, then `codex plugin add <plugin-name>@<marketplace-name>` | No — documented only, no Codex CLI on this machine | [`codex-rs/cli/src/marketplace_cmd.rs`](https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs): `"Marketplace source: a local path, owner/repo[@ref], HTTPS Git URL, or SSH Git URL."`; [`installing-and-updating.md`](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/references/installing-and-updating.md): `"codex plugin add <plugin-name>@<marketplace-name-from-marketplace-json>"` |
| Agent Plugins 1.0 (Cursor, Copilot, VS Code, Kiro) | None defined by the spec | No — no mechanism exists to verify | [agent-plugins.org/plugin-authors](https://agent-plugins.org/plugin-authors): "The portable plugin specification does not cover client-managed processes such as installation, distribution, enablement, updates, or user interface implementation." and [agent-plugins.org](https://agent-plugins.org/): "aspects such as distribution, installation, permissions, and user experience remain under the control of individual clients." |

## Observations

- **`source: "./"` is valid for a GitHub-fetched marketplace.** The docs say relative paths in `marketplace.json` "resolve relative to the marketplace root" and work "when users add your marketplace from a git source or a local directory" — they fail only for "a direct URL to the `marketplace.json` file" itself, which is not how our README tells anyone to install. The verification run below (GitHub shorthand → clone → install → connected server) confirms this for our exact `.claude-plugin/marketplace.json`.
- **The `colgrep-mcp@colgrep-mcp` syntax is a naming coincidence, not a bug.** Marketplace names and plugin names live in separate namespaces (`claude plugin marketplace list` shows the marketplace; `claude plugin list` shows `<plugin>@<marketplace>`), so `colgrep-mcp@colgrep-mcp` parses unambiguously and installed cleanly in the verification run. It reads oddly to a human, though — see Steering Questions.
- **Codex's own marketplace name differs from Claude's.** `.agents/plugins/marketplace.json`'s `name` field is `colgrep-mcp-marketplace` (not `colgrep-mcp`), so the Codex install command is `codex plugin add colgrep-mcp@colgrep-mcp-marketplace` — no collision there, but it does mean the two ecosystems' commands don't mirror each other syntactically, which the README now states explicitly rather than implying parity.
- **Agent Plugins 1.0 genuinely has no cross-client answer.** The spec (`agent-plugins.org/specification`) defines the plugin package format and a minimal client conformance bar — "Can load a plugin from a directory path" — but is silent on marketplaces, registries, or git-based install for any client. Neither the spec pages nor a client-listing page (`agent-plugins.org/clients`, which 404s) named a per-client git-install flow for Cursor, Copilot, VS Code, or Kiro specifically. The honest README claim is "consult that client's own docs," not a fabricated command.
- **Reference shape borrowed from Rikyu-Agent.** Its README leads Install with `/plugin marketplace add <owner/repo>` → `/plugin install <plugin>@<marketplace>` → `/reload-plugins` for Claude Code, and `codex plugin marketplace add <owner/repo>` → "open `/plugins`, install `<plugin>`" for Codex, both ahead of a "Manual (any MCP-compatible client)" fallback. Our rewritten Install section follows the same shape (remote-first, ecosystem by ecosystem, manual/local last) without copying its prose.

## Verification (Claude Code, this machine)

```
$ claude plugin marketplace add CrackingShells/colgrep-mcp
✔ Successfully added marketplace: colgrep-mcp (declared in user settings)

$ claude plugin marketplace list
  ...
  ❯ colgrep-mcp
    Source: GitHub (CrackingShells/colgrep-mcp)

$ claude plugin install colgrep-mcp@colgrep-mcp
✔ Successfully installed plugin: colgrep-mcp@colgrep-mcp (scope: user)

$ claude plugin list
  ❯ colgrep-mcp@colgrep-mcp
    Version: 0.1.1
    Scope: user
    Status: ✔ enabled

$ claude mcp list
  ...
  plugin:colgrep-mcp:colgrep: uv run --quiet --directory /Users/hacker/.claude/plugins/cache/colgrep-mcp/colgrep-mcp/0.1.1/server colgrep-mcp - ✔ Connected
```

Cleanup, confirmed afterward:

```
$ claude plugin uninstall colgrep-mcp@colgrep-mcp
✔ Successfully uninstalled plugin: colgrep-mcp (scope: user)

$ claude plugin marketplace remove colgrep-mcp
✔ Successfully removed marketplace: colgrep-mcp

$ claude plugin marketplace list
  # same 10 marketplaces present before this session started, lightonai-colgrep included, colgrep-mcp gone
```

Note: the task brief expected six pre-existing marketplaces; this machine
actually had ten (`claude-plugins-official`, `life-sciences`,
`claude-scientific-skills`, `svelte`, `anthropic-agent-skills`,
`lightonai-colgrep`, `rust-conventions`, `lbc-llm-agents`,
`octopus-marketplace`, `cell-marketplace`) both before adding `colgrep-mcp`
and after removing it — the count matches before and after, which is the
property that matters; the absolute number in the brief was stale.
`--scope project` was not used, per instructions, so this repository's own
`.claude/settings.json` was never touched.

## Steering Questions

- Should the marketplace be renamed away from `colgrep-mcp` (e.g. to
  `colgrep-mcp-marketplace`, matching Codex's convention) purely for
  readability of `plugin@marketplace`, even though the current name causes no
  functional collision? Out of scope for this task by instruction — flagging
  for a maintainer decision.
- Is a Codex-specific MCP config needed beyond what's already at
  `.claude-plugin/mcp.json` (which `.codex-plugin/plugin.json` also points
  at), or does today's shared file suffice once Codex is actually exercised?
  This report only documents the install-time commands; it does not verify
  that Codex's `${CLAUDE_PLUGIN_ROOT}`-style placeholder expands the way
  `.claude-plugin/mcp.json` expects — that question is already on record in
  `__reports__/repo_health/00-findings_launch_placeholders_v0.md`.

## Pointers

- README changes: `README.md` §Install, restructured to remote-first per
  ecosystem with a `### From a local clone` subsection for the try-it/develop
  path; `### Tools` and all other sections untouched.
- Prior placeholder-expansion findings, still open for Codex:
  `__reports__/repo_health/00-findings_launch_placeholders_v0.md`.
- Reference shape: [RIKEN-RCCS/Rikyu-Agent README](https://github.com/RIKEN-RCCS/Rikyu-Agent/blob/main/README.md).
