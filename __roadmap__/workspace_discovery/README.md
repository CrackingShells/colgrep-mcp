# workspace_discovery

## Context
Level-lead campaign rooted at this repository: a tool call with no `paths` resolves its default root to the server process cwd (the plugin install tree) when `COLGREP_MCP_ROOT` is unset and the client sends no roots — silently searching the wrong project. This campaign measures which dynamic per-call workspace signals each target harness actually sends so the default can resolve per call (contract: `__reports__/workspace_discovery/00-architecture_v0.md` §Contracts). Produces probe instrumentation, raw harness artifacts, a protocol survey, and the findings + architecture reports that carry the ladder decision.

## Reference Documents
- [R01 Architecture Analysis (v0)](../../__reports__/workspace_discovery/00-architecture_v0.md) — resolution ladder, probe dump schema, harness measurement matrix, fail+guidance error model
- [R02 Protocol survey (v0)](../../__reports__/workspace_discovery/01-findings_protocol_survey_v0.md) — per-call workspace channels on the MCP wire; written by the protocol_survey leaf

## Goal
Decide, from measured per-harness evidence, which rungs of the resolution ladder (dynamic workspace signal > env pin > guarded cwd + fail+guidance) survive into `paths.py`, and publish the findings + architecture reports that carry that decision.

## Pre-conditions
- [x] Environment contract measured 2026-11-12: `cd server && uv run pytest -q` resolves imports to this worktree and exits 0; `command -v claude codex` both resolve
- [x] Specs committed before dispatch (KT-B): this README, R01, and all leaf files are committed to the campaign branch before any worktree is cut
- [ ] Probe artifacts for `claude` and `codex` exist under `__reports__/workspace_discovery/probe_data/harness/` before the synthesis level runs (evidence gaps recorded as `—`, never filled)

## Success Gates
- ✅ `cd server && uv run pytest -q` exits 0 on the campaign branch with probe code in tree; probe inert: `Client.list_tools()`/`list_resources()`/`list_prompts()` dumps equal base and resolved paths bit-identical when `COLGREP_MCP_PROBE` is unset
- ✅ `__reports__/workspace_discovery/probe_data/harness/matrix.md` exists with every dynamic-signal cell a measured value or `—`
- ✅ `__reports__/workspace_discovery/01-findings_protocol_survey_v0.md` and `__reports__/workspace_discovery/01-findings_harness_probe_v0.md` exist, each opening with `type: findings` front matter and a Headline Result block
- ✅ `__reports__/workspace_discovery/02-architecture_v1.md` carries the adjudicated rung order and, for every `—` cell, the per-harness fail+guidance fallback contract (or an explicit Goal-restatement pivot)

## Gotchas
- Worktrees see only committed files (KT-B): commit this README, R01 and the leaf files before any dispatch. `probe_data/` is runtime-created; git tracks no empty directories, so a check must treat its absence as "not yet collected".
- File-disjoint ownership: `probe_instrumentation` owns `server/colgrep_mcp/probe.py`, `server/colgrep_mcp/paths.py`, `server/tests/test_probe.py`, `server/tests/e2e/probe_workspace.py`; `collect_harness_evidence` owns `__reports__/workspace_discovery/probe_data/**`; `protocol_survey` and `findings_report` own only the report files named in their Deliverables. The driver is owned by `probe_instrumentation` (mechanism) and merely *invoked* by `collect_harness_evidence` (operation) — evidence worktrees get it from the campaign branch after level-1 merges.
- The probe never runs real `colgrep` search against this repository (stack-traps): harness runs trigger `doctor` only — read-only, no index writes. Probe artifacts live under `probe_data/` and are committed as evidence (batch-01 reports cite their paths); the only string sent to any harness API is the canned `TRIGGER_PROMPT` constant.
- Consistency Checks that grep a Deliverable file are deliverable-dependent and exempt at authoring time (they run when the leaf executes); the baseline gates above were measured instead. Nothing may follow `(expected: PASS)` on a check line.
- Hard stop for the dispatch window: 21:30 JST 2026-11-12. Whatever is green at the stop gets merged; whatever is not, reports as unfinished.
- Adversarial verification is pledged for `probe_instrumentation` (measurement semantics + silent-failure risk): a verifier signs the dump-only invariant before level-2 leaves run.

## Status
```mermaid
graph TD
    probe_instrumentation[Probe instrumentation for workspace signals]:::inprogress
    protocol_survey[Workspace-channel protocol survey]:::inprogress
    evidence[Harness evidence collection]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `probe_instrumentation.md` | 📄 Leaf Task | 🔄 In Progress |
| `protocol_survey.md` | 📄 Leaf Task | 🔄 In Progress |
| `evidence/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:---|:---|:---|:---|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
