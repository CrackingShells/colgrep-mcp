# Integrate

## Context
Runs after the six depth-0 leaves merge into the campaign branch. Consumes the merged skills and code; produces the reviewer's observation report, the thin surface files, and (one level deeper) the retrospective and the release.

## Goal
The merged result is reviewed for what the tests cannot prove, the surface files point at the skills, and the campaign closes with a release.

## Pre-conditions
- [ ] All six depth-0 leaves merged with `--no-ff`; `cd server && uv run pytest` green on the campaign branch

## Success Gates
- ✅ [static] `__reports__/dev_plugin/02-observation_review_v0.md` exists; every confirmed finding routed to a fix or the knowledge-transfer report
- ✅ [run] `test_dev_plugin.py` green after `AGENTS.md`/`CONTRIBUTING.md` are rewritten

## Status
```mermaid
graph TD
    review[Read-Only Review]:::done
    surface[Surface: AGENTS.md, CLAUDE.md, CONTRIBUTING.md]:::done
    close[Close]:::done
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `review.md` | 📄 Leaf Task | ✅ Done |
| `surface.md` | 📄 Leaf Task | ✅ Done |
| `close/` | 📁 Directory | ✅ Done |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
| `surface.md` | campaign branch | 2 | lead, landed 18:41 before the skill merges (drift-test ordering); loader gate added 18:45 |
| `review.md` | `task/review` | 1 | Sonnet, ~13 min (18:52 -> 19:05); 2 low findings (F1 duplicate bullet, F2 probe sizing), schema diff empty, perf 5.6x reproduced |
