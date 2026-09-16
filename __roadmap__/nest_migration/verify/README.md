# Verification

## Context
Sits below both leaves as verification after parallel siblings: it needs the marketplace gone *and*
the manifests reshaped. Exercises the real marketplace-install path, which is the only one that
reproduces the hooks-duplicate class of failure. Produces the evidence that this repo's migration is
complete.

## Goal
Prove colgrep-mcp installs from Nest with its server connected and its hooks firing.

## Pre-conditions
- [ ] `relinquish_marketplace` and `regenerate_manifests` are both done and pushed
- [ ] The local `cracking-shells` registration already points at Nest

## Success Gates
- ✅ `claude plugin list` shows `colgrep-mcp` with no `failed to load` line [run]
- ✅ `claude mcp list` reports the colgrep server connected [run]
- ✅ The search policy hook fires in a fresh session [behavioral]

## Status
```mermaid
graph TD
    install_check[Install Check]:::blocked
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `install_check.md` | 📄 Leaf Task | 🚫 Blocked |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
