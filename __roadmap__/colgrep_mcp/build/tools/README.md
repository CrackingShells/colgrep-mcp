# Tools

## Context
Depth 2. Three parallel leaves register handlers on the shared `MCPServer` through per-module `register(mcp)` functions, each in its own file, all consuming `ColgrepAdapter`. `integrate/` wires them and verifies the whole.

## Goal
Implement the complete MCP surface defined in R01: search/find_files/expand, index_*/list_indexes/doctor, resources+prompts+completions.

## Pre-conditions
- [x] `build/colgrep_adapter` done and merged into the milestone branch

## Success Gates
- ✅ [run] `cd server && uv run pytest -q` passes with all three modules registered
- ✅ [run] In-memory `Client(build())` lists 8 tools, 3 static resources, 1 resource template, 3 prompts

## Status
```mermaid
graph TD
    search_tools[Search Tools]:::done
    index_tools[Index Tools]:::done
    resources_prompts[Resources, Prompts, Completions]:::done
    integrate[Integrate]:::done
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `search_tools.md` | 📄 Leaf Task | ✅ Done |
| `index_tools.md` | 📄 Leaf Task | ✅ Done |
| `resources_prompts.md` | 📄 Leaf Task | ✅ Done |
| `integrate/` | 📁 Directory | ✅ Done |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
| `search_tools.md` | `task/search_tools` | 2 | budget renderer backtracks so the cap includes the continuation note; adapter.search now streams stderr for index_updated |
| `index_tools.md` | `task/index_tools` | 2 | elicitation only works on legacy-protocol sessions (modern 2026-07-28 has no back-channel) — degrades to confirm=true |
| `resources_prompts.md` | `task/resources_prompts` | 2 | static resources and completion handler cannot receive Context → build adapter from Settings.from_env() |
