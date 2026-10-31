# Match Units

## Context
PR #18 (commit c4c291a on `claude/happy-hamilton-e15dcd`) made `search` yield one hit per unit in colgrep 1.8's `matches`. A review found the shape right but the construction not idiomatic: three readers of the wire shape, three location bugs, and work proportional to colgrep's input rather than the output. This campaign reworks it on the same branch, sets colgrep 1.8.4 as the soft minimum, and edits the docs in place instead of appending to them.

## Reference Documents
- [R01 Approved plan](~/.claude/plans/now-switching-you-to-tidy-glade.md) — verdict table (rows 1–9), target design, execution model
- [R02 Observation OBS-M](../../__reports__/match_lines/00-observation_markdown_match_lines_v0.md) — why a hidden section makes agents read whole files

## Goal
`search` builds only the units it returns, from one normaliser of colgrep's results. Every unit keeps its own verified range and name, and the docs state that rule without accretion.

## Pre-conditions
- [ ] `claude/happy-hamilton-e15dcd` is at c4c291a or later, with the gates green
- [ ] `colgrep --version` reports 1.8.4 or newer on this machine (for the verifier's real-binary probe)

## Success Gates
- ⬜ `cd server && uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run cz check --rev-range main..HEAD` passes on the integration branch [run]
- ⬜ Only `adapter.py` reads `matches`: within `server/colgrep_mcp/`, only `adapter.py` contains the string `"matches"` [run]
- ⬜ `git diff main..HEAD -- skills/` is empty [run]
- ⬜ The verifier's real-binary probe passes: the wave-05 105-156 hit is verified and expands to line 138 [behavioral]
- ⬜ PR #18 CI is green [run]

## Status
```mermaid
graph TD
    unit_pipeline[Unit Pipeline]:::planned
    doctor_and_docs[Doctor and Docs]:::planned
    verify[Verification]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `unit_pipeline.md` | 📄 Leaf Task | ⬜ Planned |
| `doctor_and_docs.md` | 📄 Leaf Task | ⬜ Planned |
| `verify/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
