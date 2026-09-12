# Claude Code plugin loader traps

## A freshly opened repo shows a pending colgrep entry or `spawn ENOENT` {#root-mcp-json}

**Symptom**: opening this repository (or a clone of it) as a plain project
in Claude Code shows a second, pending `colgrep` MCP entry, or a
`spawn '${CLAUDE_PLUGIN_ROOT}/...'` / `posix_spawn` ENOENT error, even
though the plugin itself connects fine when loaded as a plugin.

**Cause**: a root-level `.mcp.json` is read by Claude Code as *project*
scope MCP config — a completely different loading path from the plugin
loader, one that has no notion of `CLAUDE_PLUGIN_ROOT` and so leaves the
placeholder unexpanded, tried literally as a path. This is why this
repository's MCP config lives at `.claude-plugin/mcp.json` instead: a
root-level project open then discovers no `mcpServers.colgrep` entry at
all. Placeholders belong only in `args`/`env` (never `command` — no
ecosystem expands placeholders there); `${VAR:-default}` fallback syntax is
documented only for *project*-scope `.mcp.json`, not for the plugin
substitution path, so don't rely on it there. Agent Plugins 1.0 goes
further and forbids any fallback syntax outright — "unrecognized
placeholder-like text MUST remain literal." Whether Codex expands
`${CLAUDE_PLUGIN_ROOT}` in the shared `.mcp.json` it also points at is still
unverified (no Codex CLI on this machine). (`PH`.)

**What to do**: never add or restore a root-level `.mcp.json` to this
repository. If a manifest needs to reference the server config, point it at
`.claude-plugin/mcp.json`. If you need a fallback value in a plugin-scope
manifest, don't assume `${VAR:-default}` works — treat it as unverified and
either hardcode or make the field required.

## The install/list command reads oddly or fails to resolve {#namespaces}

**Symptom**: `claude plugin install colgrep-mcp@colgrep-mcp` looks like a
typo (same name on both sides of the `@`), or a plugin/marketplace name
collision seems like it should fail but doesn't — or conversely, an install
command copied from Claude Code's convention doesn't work verbatim for
Codex.

**Cause**: marketplace names and plugin names live in separate namespaces.
`colgrep-mcp@colgrep-mcp` parses unambiguously as `<plugin>@<marketplace>`
even though both happen to be named `colgrep-mcp` — a naming coincidence,
not a bug. Codex's own marketplace file names itself `colgrep-mcp-marketplace`
(not `colgrep-mcp`), so the equivalent Codex command is
`codex plugin add colgrep-mcp@colgrep-mcp-marketplace` — the two
ecosystems' install commands don't mirror each other syntactically. A
`source` field of `"./"` or `"./dev"` in a marketplace manifest resolves
relative to the marketplace root, which works for a marketplace added from
a git source or local directory (confirmed end-to-end for this repo's own
`.claude-plugin/marketplace.json`) but not for a direct URL to the
`marketplace.json` file itself. (`RI`.)

**What to do**: don't "fix" the `colgrep-mcp@colgrep-mcp` string as if it
were a typo. When writing install instructions for a second ecosystem,
copy that ecosystem's own marketplace `name`, not Claude Code's.

## `claude -p` / `claude plugin eval` fails with an OAuth error {#oauth}

**Symptom**: `claude -p` fails with something like `Failed to authenticate:
OAuth session expired`; `claude plugin eval` or skill-creator's
`run_loop.py`/`run_eval.py` fail the same way.

**Cause**: all of these need an authenticated `claude -p` session; on this
machine that OAuth session is expired, and none of them have a working
fallback. (`KT-B`; this campaign.)

**What to do**: don't treat this as a bug in the plugin or the skill.
Degrade the plugin-connectivity gate to `claude --plugin-dir . mcp list`
(non-interactive, shows `✔ Connected` without needing `-p`) instead of
trying to force `claude -p` to work. Eval cases in `dev/evals/*/case.yaml`
are authored to the documented schema and left unrun this cycle for the
same reason — the first session with a working authenticated `claude -p`
should run them, not this one.
