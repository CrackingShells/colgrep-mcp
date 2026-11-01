# Verification

## Context
Runs after `unit_pipeline`. It is the named adversarial review for this campaign, because the change touches the persisted `hit_id` and `location_verified` contract, where failures are silent. Its findings go back to the implementer of `unit_pipeline`.

## Goal
Either break the pipeline's location and trust rules or show, probe by probe, that they hold.

## Pre-conditions
- [x] `unit_pipeline` has reported, with its gates green

## Success Gates
- ✅ Every attack in `adversarial_review` is marked broken or held, and each broken one is fixed or explicitly accepted by the coordinator [behavioral]

## Status
```mermaid
graph TD
    adversarial_review[Adversarial Review]:::done
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `adversarial_review.md` | 📄 Leaf Task | ✅ Done |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
