# Integrate

## Context
Runs after both depth-0 leaves are merged into the campaign branch. Documents the resulting commands for agents, wires CI around them, and has a reviewer read the merged diff for what the tests cannot prove. Produces the inputs the `release/` level needs.

## Goal
Document, guard and review the depth-0 result before releasing it.

## Pre-conditions
- [ ] `python_tooling.md` and `launcher.md` are `done` and merged into the campaign branch
- [ ] `cd server && uv run pytest` passes on the campaign branch

## Success Gates
- ✅ [static] `AGENTS.md` names every gate command that exists after depth 0 and no command that does not
- ✅ [static] `.github/workflows/ci.yml` parses (actionlint if available) and calls only commands that exist in the repo
- ✅ [static] `__reports__/repo_health/01-observation_review_v0.md` exists with confidence/urgency per finding

## Status
```mermaid
graph TD
    agent_docs[Agent Orientation Docs]:::planned
    ci_workflow[CI Workflow]:::planned
    review[Reviewer Pass]:::planned
    release[Release]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `agent_docs.md` | 📄 Leaf Task | ⬜ Planned |
| `ci_workflow.md` | 📄 Leaf Task | ⬜ Planned |
| `review.md` | 📄 Leaf Task | ⬜ Planned |
| `release/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
