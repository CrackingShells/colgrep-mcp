# Integrate

## Context
Runs after the four depth-0 leaves have merged into the campaign branch. Two parallel, file-disjoint leaves: a cross-cutting docstring pass (which had to wait for every module to settle) and a read-only reviewer whose findings the lead routes to fixes or to the knowledge-transfer report.

## Reference Documents
- [R01 §C6](../../../__reports__/consistency/00-architecture_v0.md) — the docstring contract
- [R02 0.1.0 code review](../../../__reports__/colgrep_mcp/02-observation_code_review_v0.md) — the shape and probe style for the review

## Goal
Docstrings that explain why with a legend for their report ids, and an observation report that says what the tests could not.

## Pre-conditions
- [ ] All four depth-0 leaves are `done` and merged with `--no-ff`; `cd server && uv run pytest` passes on the campaign branch
- [ ] Worktrees `task-docstrings` and `task-review` created by the lead from the merged campaign branch

## Success Gates
- ✅ [run] `cd server && uv run pytest` passes after the docstring merge; `git diff` of the docstring branch shows no executable line changed
- ✅ [static] `__reports__/consistency/01-observation_review_v0.md` exists and is listed in `__reports__/consistency/README.md`
- ✅ [static] `AGENTS.md` carries the report-id legend and the four idiom rules

## Status
```mermaid
graph TD
    docstrings[Docstrings: Why, Not Roadmap Narration]:::planned
    review[Read-Only Review]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `docstrings.md` | 📄 Leaf Task | ⬜ Planned |
| `review.md` | 📄 Leaf Task | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
