# Integrate

## Context
Depth 3. After the three tool leaves land, assemble the server (path resolution, locks, lifespan, CLI), and write user documentation. `verify/` then validates against the real colgrep.

## Goal
Ship a runnable `colgrep-mcp` binary with documentation a human can install from.

## Pre-conditions
- [ ] All `build/tools/*.md` leaves done and merged

## Success Gates
- ⬜ [run] `cd server && uv run colgrep-mcp --help` exits 0
- ⬜ [run] stdio round-trip test (`tests/test_stdio.py`) passes using the fake colgrep
- ⬜ [static] README.md documents installation for Claude Code, Codex and Agent Plugins clients

## Status
```mermaid
graph TD
    server_assembly[Server Assembly]:::planned
    docs_readme[User Documentation]:::planned
    verify[Verify]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `server_assembly.md` | 📄 Leaf Task | ⬜ Planned |
| `docs_readme.md` | 📄 Leaf Task | ⬜ Planned |
| `verify/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
