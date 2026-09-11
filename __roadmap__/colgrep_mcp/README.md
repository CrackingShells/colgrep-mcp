# colgrep_mcp

## Context
Root campaign of this repository. Turns the `colgrep` CLI (semantic + hybrid code search) into an MCP server for coding agents, packaged as a Claude Code plugin and an Agent Plugins 1.0 plugin. Consumes the architecture report R01; produces an installable server, plugin manifests, and validation findings.

## Reference Documents
- [R01 Architecture](../../__reports__/colgrep_mcp/00-architecture_v0.md) — tool/resource/prompt surface, adapter contract, error model, risks
- [R02 MCP feature study](../../__reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md) — systematic client/server feature matrix and adoption decisions (written by `research_mcp_features`)
- [R03 colgrep behaviour](../../__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md) — empirical CLI behaviour: exit codes, stderr, JSON edge cases (written by `research_colgrep_behaviour`)
- [R04 CONTRIBUTING](../../CONTRIBUTING.md) — commit vocabulary and branching

## Goal
Ship `colgrep-mcp` v0.1.0: a stdio MCP server (Python SDK v2) exposing colgrep search/index operations as agent-first tools, resources and prompts, installable with `claude --plugin-dir` and as an Agent Plugins 1.0 directory.

## Pre-conditions
- [ ] `colgrep --version` ≥ 1.6.2 on PATH
- [ ] `uv` available; `uv run --with 'mcp>=2.2' python -c 'import mcp'` succeeds
- [ ] R01 architecture report exists

## Success Gates
- ⬜ [run] `cd server && uv run pytest -q` passes
- ⬜ [run] In-memory `Client(mcp)` lists every tool/resource/prompt named in R01 §Contracts
- ⬜ [run] `claude plugin validate .` passes
- ⬜ [behavioral] A stdio client calling `search` against a real repo returns ranked hits with file/line/score within 60 s of a warm index
- ⬜ [static] `plugin.json` (Agent Plugins 1.0), `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.mcp.json`, `mcp.json` all present and version-aligned with `server/pyproject.toml`
- ⬜ [static] `CHANGELOG.md` has a `0.1.0` entry

## Status
```mermaid
graph TD
    research_mcp_features[MCP Feature Matrix Study]:::inprogress
    research_colgrep_behaviour[colgrep CLI Behaviour Probe]:::inprogress
    scaffold_package[Package Scaffold]:::inprogress
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `research_mcp_features.md` | 📄 Leaf Task | 🔄 In Progress |
| `research_colgrep_behaviour.md` | 📄 Leaf Task | 🔄 In Progress |
| `scaffold_package.md` | 📄 Leaf Task | 🔄 In Progress |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
