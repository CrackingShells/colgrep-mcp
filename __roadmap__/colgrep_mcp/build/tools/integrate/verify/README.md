# Verify

## Context
Depth 4, the last level. Validates the assembled server against the real colgrep binary on a real repository, records measurements, then cuts release 0.1.0.

## Goal
Prove the server works end-to-end and release it.

## Pre-conditions
- [ ] `server_assembly` and `docs_readme` done and merged

## Success Gates
- ⬜ [behavioral] Findings report with measured latencies exists under `__reports__/colgrep_mcp/`
- ⬜ [static] `git tag v0.1.0` exists on the milestone branch after merge to main

## Status
```mermaid
graph TD
    e2e_validation[End-to-End Validation]:::planned
    release_0_1_0[Release 0.1.0]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `e2e_validation.md` | 📄 Leaf Task | ⬜ Planned |
| `release_0_1_0.md` | 📄 Leaf Task | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
