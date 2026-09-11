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
    server_assembly[Server Assembly]:::done
    docs_readme[User Documentation]:::done
    verify[Verify]:::planned
    error_taxonomy[Error and Hint Taxonomy]:::inprogress
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `server_assembly.md` | 📄 Leaf Task | ✅ Done |
| `docs_readme.md` | 📄 Leaf Task | ✅ Done |
| `verify/` | 📁 Directory | ⬜ Planned |
| `error_taxonomy.md` | 📄 Leaf Task | 🔄 In Progress |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|
| A01 | 2026-09-12 | PI (mid-run question) | `error_taxonomy.md` | Agents should recover from failures by stable machine-readable codes that name the next usage pattern, not by parsing prose |

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
