# harness_wiring — reports

Sixth campaign of this repository (2026-09-13, after `pypi_publication` 0.3.1): move the maintainer's harness wiring for colgrep — search policy at session start, denial of the built-in Grep tool and recursive shell greps, worktree index reaping — out of one machine's `~/.claude/settings.json` and into the product plugin as a `hooks/` component, rewritten to name the MCP tools instead of CLI flags. Single-agent, no roadmap tree: step commits on `claude/colgrep-harness-mcp-5c6a5a`.

## Round 00
- `00-architecture_v0.md` — R01 (harness_wiring): the portable `hooks.json` contract shared by Claude Code, Codex and Cursor (C1), the Claude-only file (C2), the `uv run --no-project python` launcher with its latency measurements (C3), the hook script's I/O table (C4), the carried-over corpus-search detector (C5), the harness-side retirement (C6); decisions D1–D9; risk register.

## Status
Implemented on the campaign branch, verified live with `claude --plugin-dir . -p` (the SessionStart policy arrives; a `grep -rn` is denied with the plugin's reason). Pinned by `server/tests/test_hooks.py` (39 tests: behaviour through `sys.executable`, drift guards on the manifests). Not verified: Codex (no CLI on this machine) and Cursor (documented from its third-party-hooks page only). The maintainer's `~/.claude/settings.json` retired its three colgrep hooks the same day (R01 §C6).
