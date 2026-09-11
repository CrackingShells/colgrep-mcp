# Verify

## Context
Depth 4, the last level. Validates the assembled server against the real colgrep binary on a real repository, records measurements, then cuts release 0.1.0.

## Goal
Prove the server works end-to-end and release it.

## Pre-conditions
- [x] `server_assembly` and `docs_readme` done and merged

## Success Gates
- ✅ [behavioral] Findings report with measured latencies exists under `__reports__/colgrep_mcp/`
- ✅ [static] `git tag v0.1.0` exists on the milestone branch after merge to main

## Status
```mermaid
graph TD
    e2e_validation[End-to-End Validation]:::done
    release_0_1_0[Release 0.1.0]:::done
    code_review[Code Review Pass]:::done
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `e2e_validation.md` | 📄 Leaf Task | ✅ Done |
| `release_0_1_0.md` | 📄 Leaf Task | ✅ Done |
| `code_review.md` | 📄 Leaf Task | ✅ Done |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|
| A02 | 2026-09-12 | PI recommendation | `code_review.md` | A reader should trace paths tests cannot easily prove (subprocess lifecycle, unit location, budget, guards) before release |

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
| `e2e_validation.md` | `task/e2e_validation` | 1 | median warm search 759 ms; cold build 16.2 s, 4 progress notifications; claude -p blocked by expired OAuth, `mcp list` shows Connected |
| `code_review.md` | `task/code_review` + `task/code_review_fixes` | 1 + 11 | 14 findings; F1-F6, F8, F9, F11-F14 fixed with regression tests; F7, F10 deferred |
| `release_0_1_0.md` | `milestone/colgrep_mcp` (lead) | 1 | changelog generated from conventional subjects; KT report; tag v0.1.0 on main |
