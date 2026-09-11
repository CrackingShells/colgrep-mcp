# Reports — colgrep_mcp

## Round 00
- `00-architecture_v0.md` — architecture analysis: tool/resource/prompt surface, adapter contract, error model, risks (superseded by 02-architecture_v1.md for the deltas listed there)

## Round 01
- `01-findings_mcp_feature_matrix_v0.md` — systematic MCP feature matrix with adopt/defer decisions (latest)
- `01-findings_colgrep_behaviour_v0.md` — measured colgrep CLI behaviour + evidence (latest)

## Round 02
- `02-architecture_v1.md` — architecture delta after R02/R03: unit location by code match, heartbeat progress, project-root folding (latest)
- `02-observation_code_review_v0.md` — read-only code review: 5 confirmed bugs (subprocess/task leaks on client cancellation in `adapter._run` and `tools_index.index_build`; `locate_unit` can return `location_verified=True` for a wrong span; token-budget hard cap not actually hard when zero hits are ever emitted), 6 risks, 3 consolidation cleanups, plus a traced-no-issue list covering every scenario the review leaf named (latest)

## Status
Campaign bootstrapped 2026-09-11. Architecture v0 authored by the team lead; round-01 findings delegated to research agents. Round-02 code review complete; findings await lead triage (bug → `fix(...)` + test on `task/code_review_fixes`; consolidation → apply if <30 lines else next cycle; risk → knowledge-transfer report) before release.
