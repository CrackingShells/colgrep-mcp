# Resolution ladder (solution)

## Context
Depth-ordered after `probe_hardening` (calibration oracle first) and in parallel with the `evidence/` harness census — disjoint files (`paths.py` + resolution tests here, `probe.py` there). Executes the sponsor fold of 2026-11-13: the ladder `paths > dynamic (_meta + per-call roots) > COLGREP_MCP_ROOT > fail+guidance`, grounded in R03b's live wire measurements.

## Goal
The default root resolves per call from what the harness actually sent, degrades through the `COLGREP_MCP_ROOT` pin, and fails with actionable guidance only when nothing mentions the workspace.

## Pre-conditions
- [ ] `probe_hardening` reaches `done` (its calibration oracle backs these rungs' tests)
- [ ] R03b (`03-findings_live_probe_v0.md`) is merged and cited by both leaf steps

## Success Gates
- ✅ Ladder tests pin each rung's precedence; the silence rung's error names the `paths` remedy verbatim
- ✅ Post-rebase `uv run pytest -q` green on the campaign branch after this level integrates

## Gotchas
- The probe hook line in `paths.py` belongs to `probe_hardening`; this level owns resolution logic and its tests only — landing `probe_hardening` first (level order) keeps the writes from racing.
- The `ROOT_UNRESOLVED` guidance wording is client-visible contract: copy it from the leaf, never improvise.

## Status
```mermaid
graph TD
    per_call_resolution[Per-call workspace resolution ladder (meta, roots, pin, fail+guidance)]:::amendment
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `per_call_resolution.md` | 📄 Leaf Task | 🔵 Amendment |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
