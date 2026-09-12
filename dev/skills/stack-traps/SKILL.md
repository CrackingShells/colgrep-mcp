---
name: stack-traps
description: Lists what colgrep, the MCP Python SDK v2, and Claude Code's plugin loader silently do behind a maintainer's back in this repository, so a symptom is recognised before it burns an hour. Load this before running `colgrep` by hand, before running the e2e driver or `colgrep init`, before adding or changing a tool/resource/prompt handler, before touching any plugin manifest or `.claude-plugin/mcp.json`, whenever a plugin fails to connect, whenever `claude -p` or `claude plugin eval` errors, whenever a Windows CI job is the only red one, or whenever a Bash command gets blocked for no obvious reason.
---

# stack-traps

Four layers hide behind this repository's day-to-day commands, and each one
has already bitten a maintaining agent at least once. This skill is the
symptom index; each fact lives in exactly one `references/*.md` file, cited
back to the report or docstring that established it — read the linked
section, don't re-derive the trap from scratch.

## Symptom index

| Symptom you see | Layer | Reference |
|:--|:--|:--|
| a subcommand run with a trailing global flag turned into a search / reindexed the cwd | colgrep | `references/colgrep.md#flag-order` |
| you're about to run the e2e driver or `colgrep init` against this repo or a worktree | colgrep | `references/colgrep.md#ancestor-folding` |
| a hit's `line`/`end_line` doesn't bound the code you can see | colgrep | `references/colgrep.md#location` |
| a tool description shows stray leading whitespace to a client | mcp-sdk | `references/mcp-sdk.md#docstring-verbatim` |
| a `functools.cache`-wrapped resource handler raises at registration | mcp-sdk | `references/mcp-sdk.md#validate-call` |
| a static resource or the completion callback needs the adapter/settings but has no `ctx` | mcp-sdk | `references/mcp-sdk.md#no-context` |
| `roots/list`/elicitation do nothing, or deprecation warnings appear at startup | mcp-sdk | `references/mcp-sdk.md#protocol-deprecation` |
| a Windows client's root path won't resolve | mcp-sdk | `references/mcp-sdk.md#windows-roots` |
| opening this repo as a plain project shows a pending colgrep entry or a `spawn ENOENT` | claude-code | `references/claude-code.md#root-mcp-json` |
| an install/list command's plugin and marketplace names look mismatched or don't carry to another ecosystem | claude-code | `references/claude-code.md#namespaces` |
| `claude -p` or `claude plugin eval` fails with an OAuth error | claude-code | `references/claude-code.md#oauth` |
| a Bash command is blocked, including inside a heredoc that only mentions the search pattern | machine | `references/machine.md#shell-hook` |
| CI is red only on windows-latest, or only a `setup-uv` step fails | machine | `references/machine.md#windows-ci` |
| `git worktree add` on `main` fails because it's checked out elsewhere | machine | `references/machine.md#worktree-main` |

## How to use this

1. Match your symptom to a row above (or scan the reference file for your
   layer if nothing matches exactly — each entry gives symptom, cause, and
   what to do, in that order).
2. Open only the reference file the row names; the other three files are
   for different symptoms and not worth loading.
3. Do what "what to do" says before trying anything else — every trap here
   already cost someone real time working around the wrong layer (fixing
   the server for what was actually a test-harness bug, treating a naming
   coincidence as an error, adding a root `.mcp.json` back, etc.).
4. If you hit a stack trap not listed here, it belongs in a future revision
   of the matching `references/*.md` file, cited to its source — don't
   leave it as tribal knowledge in a commit message or a private aside.

## References

- `references/colgrep.md` — flag ordering, ancestor-project index folding
  and the e2e/`colgrep init` ban, wrong `line`/`end_line`.
- `references/mcp-sdk.md` — verbatim docstrings, `validate_call` vs
  `functools.cache`, no `Context` for static resources/completions,
  2026-07-28 protocol deprecations and legacy-mode sessions, Windows root
  URIs.
- `references/claude-code.md` — root `.mcp.json` vs plugin-scope
  `.claude-plugin/mcp.json`, marketplace vs plugin namespaces, `claude -p`
  on an expired OAuth session.
- `references/machine.md` — the shell-search hook and `COLGREP_BYPASS=1`,
  Windows CI's two known causes, the detached-worktree trick for `main`.
