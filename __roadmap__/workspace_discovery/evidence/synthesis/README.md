# Findings synthesis

## Context
Level 3 of `workspace_discovery`, the terminal level: adjudicate the resolution ladder from what the fleet actually delivered. Consumes `probe_data/harness/matrix.md`, the raw JSONL artifacts, R01's rung ids and R02's verdicts; produces the batch-01 findings report whose `Decision` defines the next campaign's scope.

## Goal
One findings report where each harness gets a `Resolution Picks` rung string-matching R01, dead cells stay `—`, and every `—` carries the fail+guidance fallback (error naming `paths` with an absolute directory).

## Pre-conditions
- [ ] All level-1 and level-2 leaves `done` per `dirtree-rdm ls` (not memory)
- [ ] Matrix and raw artifacts present under `probe_data/harness/`

## Success Gates
- ✅ `01-findings_harness_probe_v0.md` exists with valid findings front matter and a `## Headline Result` block
- ✅ `Resolution Picks` per harness matches an R01 rung id; every matrix `—` reappears as `—` in the report

## Status
```mermaid
graph TD
    findings_report[Findings report from the probe fleet]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `findings_report.md` | 📄 Leaf Task | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
