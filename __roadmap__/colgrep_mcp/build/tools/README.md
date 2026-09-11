# Tools

## Context
Depth 2. Three parallel leaves register handlers on the shared `MCPServer` through per-module `register(mcp)` functions, each in its own file, all consuming `ColgrepAdapter`. `integrate/` wires them and verifies the whole.

## Goal
Implement the complete MCP surface defined in R01: search/find_files/expand, index_*/list_indexes/doctor, resources+prompts+completions.

## Pre-conditions
- [ ] `build/colgrep_adapter` done and merged into the milestone branch

## Success Gates
- ⬜ [run] `cd server && uv run pytest -q` passes with all three modules registered
- ⬜ [run] In-memory `Client(build())` lists 8 tools, 3 static resources, 1 resource template, 3 prompts

## Status
```mermaid
graph TD
    search_tools[Search Tools]:::planned
    index_tools[Index Tools]:::planned
    resources_prompts[Resources, Prompts, Completions]:::planned
    integrate[Integrate]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `search_tools.md` | 📄 Leaf Task | ⬜ Planned |
| `index_tools.md` | 📄 Leaf Task | ⬜ Planned |
| `resources_prompts.md` | 📄 Leaf Task | ⬜ Planned |
| `integrate/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
