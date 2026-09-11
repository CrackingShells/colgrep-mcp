# colgrep-mcp 0.1.0 — Knowledge Transfer (v0)

Date: 2026-09-12

## Executive Summary
- **What shipped**: `colgrep-mcp` 0.1.0 — a stdio MCP server (Python SDK v2.2, `MCPServer`) wrapping colgrep 1.6.2 with 8 tools, 4 resources + 1 template, 3 prompts, completions, coded errors, and one directory that is simultaneously a Claude Code plugin/marketplace, an Agent Plugins 1.0 plugin and a Codex plugin. 194 tests against a fake colgrep; one real-binary e2e run (median warm search 759 ms, cold build 16 s with heartbeat progress).
- **Primary outcomes**: the campaign ran in ~4 h wall time with one lead and eleven Sonnet 5 subagents in isolated worktrees; every leaf shipped against a written contract (R01/R05) and the review pass found 14 issues, 12 fixed before release.

## Wins
- **Contract before code.** Writing the architecture report and every leaf spec before dispatching let three implementers build tool modules in parallel with zero merge conflicts on code.
- **Measure before assuming.** The colgrep behaviour probe (R03) overturned three assumptions the architecture had made (line numbers unreliable, no per-file progress, project-root folding) before a line of adapter code existed; the v1 delta cost one report, not a rewrite.
- **Fake binary + in-memory `Client(mcp)`.** The whole surface is testable in ~8 s without a model download; the real binary is exercised by one opt-in test and the e2e driver.
- **Reviewer pass paid for itself.** Two confirmed resource leaks on client cancellation and a false-positive path in `locate_unit` would not have been caught by the mechanical tests.
- **Lead did the mechanical glue itself** (scaffold, shared helpers, lifespan, README, launcher script), which removed three coordination points the agents would otherwise have collided on.

## Pain Points
- A generic `build/` rule in `.gitignore` silently hid the roadmap's `build/` directory; two agents were dispatched with leaf files that did not exist in their worktrees (they recovered by reading the main checkout).
- Merge commits twice landed with conflict markers in `__reports__/colgrep_mcp/README.md` because the lead ran `git add -A && git commit` after a conflicting merge; caught and amended both times, but it is a trap.
- `claude -p` was unusable all night (expired OAuth session), so the behavioural plugin gate degraded to `claude --plugin-dir . mcp list`.
- The SDK's modern-protocol dispatch has no back-channel: elicitation only works on legacy sessions, and every `ctx.info` triggers a deprecation warning that had to be filtered at startup.
- One agent ran `colgrep --color never settings`, which clap parsed as a search and indexed its worktree; the flag-ordering surprise cost a stray index (cleared by the lead).

## Root Causes
- Ignore rules were written for the Python package, not for a repo whose roadmap directory happens to be named `build/`.
- Worktrees are created from HEAD; anything not committed is invisible to the agent. The lead committed specs a beat too late twice.
- The protocol is mid-transition (2026-07-28 deprecates roots, sampling, logging, and the handshake); v2 SDK behaviour differs between `mode="legacy"` and modern sessions and the docs are thin on this.

## Next-cycle Changes
- **Instruction changes**: dispatch prompts must state "if the leaf file is missing from your worktree, stop and report" rather than letting agents read the main checkout; add "never place `--color` before the subcommand" to the adapter's docstring (done) and to the guide.
- **Workflow changes**: a pre-dispatch checklist for the lead: leaf committed? gitignore checked? shared helpers created? Resolve merge conflicts with an explicit conflict-marker grep before committing.
- **Review process changes**: run the reviewer pass after every level that merges more than two parallel branches, not only before release; give it the fixer's branch afterwards for a second, shorter pass.
- **Product follow-ups** (roadmap for 0.2): publish to PyPI so manifests can use `uvx colgrep-mcp`; budget `list_indexes` text (24 kB on this machine — it is machine-global); F7 symlink canonicalisation vs colgrep's project key; F10 completion cache lock; `INDEX_COLD` code emitted from `index_status`-aware logic; icons if a GUI client becomes a target; streamable-http behind a flag is already there but untested.

## Artifacts to Preserve
- `__reports__/colgrep_mcp/00-architecture_v0.md`, `02-architecture_v1.md` — the contract and its measured deltas.
- `__reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md` — 38-row MCP feature decision table; reusable for any future MCP server.
- `__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md` + `evidence/colgrep/` — raw colgrep 1.6.2 behaviour; re-run when colgrep updates.
- `__reports__/colgrep_mcp/02-observation_code_review_v0.md` — review checklist worth reusing for subprocess-wrapping servers.
- `server/tests/e2e/run_e2e.py` — the real-binary driver; `__reports__/colgrep_mcp/evidence/e2e/` its three runs.
- `__roadmap__/colgrep_mcp/` — the full BFS tree with per-leaf progress and two amendments.

## Open Questions
- Does Claude Code negotiate a legacy-protocol session with plugin MCP servers today (so elicitation actually prompts the user for `index_clear`)? Verify interactively once `claude` is authenticated.
- Is colgrep's wrong `line`/`end_line` tied to `--pool-factor 2`? A `--no-pool` re-probe would tell whether `locate_unit` can be retired upstream.
- Should `list_indexes`/`--stats` be exposed at all on shared machines (path leakage)? Fine for a single-user laptop; revisit for team installs.
- Will Codex expand `${CLAUDE_PLUGIN_ROOT}` in the shared `.mcp.json`? The Codex manifest points at it unverified; a Codex-specific config may be needed.
