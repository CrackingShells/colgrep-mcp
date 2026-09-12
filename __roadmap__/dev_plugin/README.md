# dev_plugin

## Context
Fourth campaign of this repository, after `colgrep_mcp` (0.1.0), `repo_health` (0.1.1) and `consistency` (0.1.2). Consumes R01 (`__reports__/dev_plugin/00-architecture_v0.md`); produces the `colgrep-mcp-dev` plugin of four maintainer skills, a thin `AGENTS.md`/`CONTRIBUTING.md` surface, and the consistency retrospective's measurable follow-ups (`FileHit`-only `find_files`, one summary log notification per `search`, a `list_indexes` text budget; the `ruff format` sweep landed first as `bdc029d`). Time-boxed: 3 h wall time from 18:23 CEST on 2026-09-12; campaign branch `claude/reverent-fermi-070f30`.

## Reference Documents
- [R01 dev_plugin architecture](../../__reports__/dev_plugin/00-architecture_v0.md) — contracts C1–C8, the content inventory (C4), ownership, risks
- [R05 colgrep_mcp architecture v1](../../__reports__/colgrep_mcp/02-architecture_v1.md) — D7 `index_updated`, the token-budget invariant

## Goal
Everything the last three cycles learned is loadable as a skill from the repository's own dev plugin, the surface files only point at it, and the product tools do the follow-up work with the schemas byte-identical.

## Pre-conditions
- [ ] `bdc029d` (format sweep) and `1ceaa95` (dev plugin scaffold, `test_dev_plugin.py`, version_files) on the campaign branch; `cd server && uv run pytest` 208 passed
- [ ] R01 committed; one worktree per depth-0 leaf created by the lead from the campaign branch at `/Users/hacker/Documents/tmp/claude-worktrees/colgrep_mcp/task-<leaf>`

## Success Gates
- ✅ [run] `cd server && uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run cz check --rev-range main..HEAD` green; `claude plugin validate .`, `claude plugin validate ./dev` pass; `claude --plugin-dir . mcp list` connects
- ✅ [static] `dev/skills/` holds `maintainer-policy`, `campaign-lead`, `landing-and-release`, `stack-traps`, each with a `SKILL.md` ≤ 150 lines and a `dev/evals/<name>-triggers/case.yaml`; every R01 §C4 bullet is in exactly one skill
- ✅ [static] `AGENTS.md` ≤ 130 lines and names every skill; `CONTRIBUTING.md` under 60 lines; `test_dev_plugin.py` green
- ✅ [behavioral] `Client.list_tools()` JSON identical between `main` and the campaign branch; the only client-visible deltas are the two R01 §C8 lists
- ✅ [static] `__reports__/dev_plugin/` holds the architecture, the stderr findings, the review observation and a knowledge-transfer report; released as v0.1.3 from the main checkout

## Gotchas
- File ownership is disjoint by construction (R01 §Roadmap Recommendation): a leaf edits only its own files and *reports* anything else in its final message, never edits it. `__reports__/dev_plugin/README.md` is touched at depth 0 only by `search_path`.
- Skills cite, they do not narrate: each fact once, with its report id; when a skill and the commitizen machinery disagree, the skill is wrong.
- Never run a real `colgrep` or the e2e driver against this repository or its worktrees; micro-benchmarks use synthetic inputs in the scratchpad; `perf` commits carry the numbers or become `refactor`.
- `Client.list_tools()` JSON is part of the oracle for both code leaves: dump before, dump after, diff empty.
- Eval cases are authored, not run: `claude -p` is unusable on this machine (expired OAuth).
- Hard stops: implementers stop and report at 19:35 CEST whatever their state; the reviewer at 20:05; the lead merges what is green.

## Status
```mermaid
graph TD
    skill_policy[Skill: Maintainer Policy]:::inprogress
    skill_campaign_lead[Skill: Campaign Lead]:::inprogress
    skill_landing_release[Skill: Landing and Release]:::inprogress
    skill_stack_traps[Skill: Stack Traps]:::inprogress
    search_path[Search Path: FileHit-Only find_files and Stderr Notifications]:::inprogress
    list_indexes_budget[list_indexes Text Budget]:::inprogress
    integrate[Integrate]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `skill_policy.md` | 📄 Leaf Task | 🔄 In Progress |
| `skill_campaign_lead.md` | 📄 Leaf Task | 🔄 In Progress |
| `skill_landing_release.md` | 📄 Leaf Task | 🔄 In Progress |
| `skill_stack_traps.md` | 📄 Leaf Task | 🔄 In Progress |
| `search_path.md` | 📄 Leaf Task | 🔄 In Progress |
| `list_indexes_budget.md` | 📄 Leaf Task | 🔄 In Progress |
| `integrate/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
