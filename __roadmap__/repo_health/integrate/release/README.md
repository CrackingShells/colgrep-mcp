# Release

## Context
Last level. Applies reviewer findings the lead accepts, removes the merged 0.1.0 branches, writes the retrospective, merges the campaign branch into `main` and cuts 0.1.1 with `cz bump` as the first end-to-end use of the new machinery.

## Goal
Land the campaign on `main` and release 0.1.1 through commitizen.

## Pre-conditions
- [ ] `integrate/` leaves are `done`
- [ ] The lead has triaged `01-observation_review_v0.md` (accept / defer per finding)

## Success Gates
- ✅ [run] `git -C <main checkout> log --oneline -1` shows the `release(colgrep-mcp): v0.1.1` commit and `git tag` lists `v0.1.1`
- ✅ [static] `__reports__/repo_health/02-knowledge_transfer_v0.md` exists and `__reports__/repo_health/README.md` indexes all rounds
- ✅ [run] `cd server && uv run pytest` passes on `main` after the bump

## Status
```mermaid
graph TD
    cleanup_and_release[Branch Cleanup, Retrospective and Release]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `cleanup_and_release.md` | 📄 Leaf Task | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
