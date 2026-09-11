# Build

## Context
Depth 1 of the campaign. Runs after the scaffold and both research leaves; produces the adapter (the only code that talks to colgrep), the three plugin manifests, and the agent-facing skill. Its `tools/` child builds the MCP surface on top of the adapter.

## Goal
Deliver the foundations that every MCP handler needs: a fixture-tested adapter, installable plugin manifests, and usage guidance for agents.

## Pre-conditions
- [ ] `scaffold_package` done (`cd server && uv run pytest -q` passes)
- [ ] R03 colgrep behaviour report merged (adapter fixtures come from its evidence)

## Success Gates
- ⬜ [run] `cd server && uv run pytest -q tests/test_adapter.py tests/test_textparse.py` passes
- ⬜ [run] `claude plugin validate .` passes
- ⬜ [static] `skills/colgrep-search/SKILL.md` exists with valid frontmatter

## Status
```mermaid
graph TD
    colgrep_adapter[colgrep Adapter]:::planned
    plugin_packaging[Plugin Packaging]:::inprogress
    agent_skill[Agent Usage Skill]:::done
    tools[Tools]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `colgrep_adapter.md` | 📄 Leaf Task | ⬜ Planned |
| `plugin_packaging.md` | 📄 Leaf Task | 🔄 In Progress |
| `agent_skill.md` | 📄 Leaf Task | ✅ Done |
| `tools/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
