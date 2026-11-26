# Verify

## Context
Runs after `mirror_and_guards` and `docs_and_naming` merge. It is this campaign's named loader probe: the Claude Code marketplace install is the only oracle exercising the rule `plugin validate` cannot see, and the Copilot session is the only oracle for the mirror itself. Findings land in `__reports__/hook_namespace/01-findings_loader_probes_v0.md` and go back to the lead.

## Goal
Break the shipped hook shape with each loader's own rules, or record, probe by probe, that it holds.

## Pre-conditions
- [ ] `mirror_and_guards` and `docs_and_naming` have reported, with gates green on the integration branch

## Success Gates
- ✅ Every probe in `loader_probes` is marked broken or held in the report, and each broken one is fixed or explicitly accepted before the cycle closes

## Status
```mermaid
graph TD
    loader_probes[Loader Probes]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `loader_probes.md` | 📄 Leaf Task | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
