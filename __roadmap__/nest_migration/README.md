# Nest Migration

## Context
colgrep-mcp currently owns the `cracking-shells` marketplace name in its own repository, listing
`colgrep-mcp` and the maintainer plugin `colgrep-mcp-dev`. `CrackingShells/Nest` is taking that name
over as the organisation's single catalogue. This campaign hands the name across and moves this
repo's manifests to the reshaped generator's output. It is **fully gated** on the
`agent_plugin_nest` campaign in the playbook: nothing here starts until Nest provably installs
plugins, because relinquishing a working catalogue before its replacement is proven would leave
users with neither.

## Reference Documents
- [R01 Implementation Plan](~/.claude/plans/good-news-overall-it-s-gleaming-wreath.md) — the campaign gate and the Nest entry shape
- [R02 Traps](https://github.com/CrackingShells/cracking-shells-playbook/blob/main/skills/spawning-agent-plugins/references/traps.md) — marketplace naming and the hooks-duplicate install failure (lives in the playbook repo, not here)

## Goal
colgrep-mcp ships no marketplace, points users at Nest, and carries manifests in the Agent-Plugins-plus-extensions shape.

## Pre-conditions
- [ ] `relinquish_marketplace` waits on `agent_plugin_nest/generator/rollout/verify/end_to_end.md` — Nest must install playbook plugins for real before this repo gives up a working catalogue
- [ ] `regenerate_manifests` waits only on `agent_plugin_nest/generator/generator_reshape.md`, so it can start earlier than its sibling
- [ ] Nest lists `colgrep-mcp` and `colgrep-mcp-dev`, so nothing is dropped when this repo stops listing them
- [ ] A playbook checkout containing the reshaped generator is available, and its path is named in the implementer's brief

## Success Gates
- ✅ Neither `.claude-plugin/marketplace.json` nor `.agents/plugins/marketplace.json` exists [run]
- ✅ No `.codex-plugin/` directory remains [run]
- ✅ `check_plugin.py` reports no problems for this repo [run]
- ✅ README install snippets name `CrackingShells/Nest` and no longer name `CrackingShells/colgrep-mcp` [run]
- ✅ Installing colgrep-mcp from Nest connects the MCP server and fires the hooks [behavioral]

## Status
```mermaid
graph TD
    relinquish_marketplace[Relinquish Marketplace]:::blocked
    regenerate_manifests[Regenerate Manifests]:::inprogress
    verify[Verification]:::blocked
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `relinquish_marketplace.md` | 📄 Leaf Task | 🚫 Blocked |
| `regenerate_manifests.md` | 📄 Leaf Task | 🔄 In Progress |
| `verify/` | 📁 Directory | 🚫 Blocked |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
