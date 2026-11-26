# Hook Namespace

## Context
Copilot/VS Code reads the hooks of an Agent Plugins v1 plugin only from `com.github.copilot/hooks/hooks.json`, so for this repo — which ships them at `hooks/` — the session shows "Some hook files could not be loaded" and no hook fires there. This campaign mirrors the portable hook file into the reverse-DNS directory, pins the two copies together, teaches every reader where each loader looks, and probes the loaders' behaviour. It fixes this branch and records the evidence in `__reports__/hook_namespace/`; making the mirror reproducible in the Pinion generator is a later cycle.

## Reference Documents
- [R01 Architecture](../../__reports__/hook_namespace/00-architecture_v0.md) — contracts (token-per-loader, per-event pin), the evidence chain, file ownership, risk register

## Goal
Every hook-capable harness loads the same policy from the path its own loader reads: a `${PLUGIN_ROOT}` mirror at `com.github.copilot/hooks/hooks.json` beside the unchanged `${CLAUDE_PLUGIN_ROOT}` `hooks/hooks.json`, with drift guards proving the two files are one policy modulo the token.

## Pre-conditions
- [x] The evidence chain is pinned in `R01` §Evidence: VS Code's `pluginParsers.ts` hardcodes the reverse-DNS hook path and its `sessionCustomizationDiscovery.ts` emits the warning; Codex resolves `extensions["com.openai"].hooks`; a third party verified Copilot CLI 1.0.82 behaves the same way
- [x] `cd server && uv run pytest -q && uv run ruff check && uv run ruff format --check` is green on the campaign branch before the first leaf
- [ ] The campaign branch sits on the latest `main` (fetch and rebase first if `origin/main` moved)

## Success Gates
- ✅ `cd server && uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run cz check --rev-range main..HEAD` passes on the integration branch [run]
- ✅ `com.github.copilot/hooks/hooks.json` is byte-identical to `hooks/hooks.json` modulo `${PLUGIN_ROOT}` ↔ `${CLAUDE_PLUGIN_ROOT}` (the `hooks` blocks, description keys free), every event it names is in the portable set, and removing it turns the suite red [run]
- ✅ `plugin.json` gains no `hooks` key and `extensions["com.openai"].hooks` still names `./hooks/hooks.json` — Codex's contract is untouched [static]
- ✅ `claude plugin validate . && claude plugin validate ./dev` pass, and the scratch-marketplace install probe in `verify/` ends green [run]
- ⬜ A Copilot/VS Code session lists the three portable hooks for colgrep-mcp (a legacy notice about the root file may remain and is accepted) [behavioral]

## Gotchas
- File ownership is disjoint and absolute: `mirror_and_guards` owns `com.github.copilot/**` and the hook pins in `server/tests/test_hooks.py`; `docs_and_naming` owns `README.md`, `AGENTS.md` and `dev/skills/stack-traps/**`; `verify/` is read-only apart from its report under `__reports__/hook_namespace/`. Anything else noticed is reported in the final message, never edited.
- Never move `hooks/hooks.json` or `hooks/worktree-remove.json`, and never name `./hooks/hooks.json` in `.claude-plugin/plugin.json`: Claude Code auto-loads that file and rejects a manifest naming it again ("Duplicate hooks file detected") on every marketplace install while `plugin validate` stays green (stack-traps `claude-code.md#hooks-manifest-duplicate`).
- The mirror carries `${PLUGIN_ROOT}` and never `${CLAUDE_PLUGIN_ROOT}`: the two loader families interpolate disjoint token sets, and the swap is the only byte difference the drift guards tolerate.
- `WorktreeRemove` has no mirror: a v1 loader must never meet an event only Claude Code knows, which is also why `hooks/worktree-remove.json` stays a per-event file.
- Every commit subject, merge commits included, is checked by `cz check` against `CONTRIBUTING`; probe subjects with `uv run cz check --message "<subject>"` and run `cz check --rev-range main..HEAD` before pushing (KT-D §Pain Points).
- `AGENTS.md` is capped at 130 lines by `test_dev_plugin.py::test_agents_md_stays_under_the_line_cap` (127 today): detail belongs in a dev skill, not in the surface.
- Hard stop at the cycle's end (one to four hours, KT-C/KT-H): the lead merges whatever is green; the rest seeds the next cycle.

## Status
```mermaid
graph TD
    mirror_and_guards[Mirror and Guards]:::done
    docs_and_naming[Docs and Naming]:::done
    verify[Verify]:::done
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `mirror_and_guards.md` | 📄 Leaf Task | ✅ Done |
| `docs_and_naming.md` | 📄 Leaf Task | ✅ Done |
| `verify/` | 📁 Directory | ✅ Done |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
