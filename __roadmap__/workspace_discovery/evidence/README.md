# Harness evidence collection

## Context
Level 2 of `workspace_discovery`: run the probe driver against the reachable harnesses (`claude`, `codex`) and record raw JSONL evidence plus the consolidated signal matrix. Consumes the instrumentation merged from `probe_instrumentation` and R02's channel ids; produces `probe_data/harness/` artifacts for `synthesis/` to adjudicate.

## Goal
Every harness × signal cell carries a measured value or a recorded gap `—`; no cell is synthesized.

## Pre-conditions
- [ ] `probe_instrumentation` merged to the campaign branch (`git cat-file -e <branch>:server/tests/e2e/probe_workspace.py` exits 0)
- [ ] `__reports__/workspace_discovery/01-findings_protocol_survey_v0.md` exists on the campaign branch
- [ ] Hard stop honoured (campaign README §Gotchas): stop at the window close, commit green work

## Success Gates
- ✅ `__reports__/workspace_discovery/probe_data/harness/raw/` holds one artifact (raw JSONL or `{"error": ...}` gap record) per harness named in the leaf
- ✅ `matrix.md` exists with exactly one cell per R01 matrix column per harness row; every absent value is `—` with the gap record named in `Notes`

## Status
```mermaid
graph TD
    collect_harness_evidence[Collect harness probe artifacts]:::planned
    synthesis[Findings synthesis]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `collect_harness_evidence.md` | 📄 Leaf Task | ⬜ Planned |
| `synthesis/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
