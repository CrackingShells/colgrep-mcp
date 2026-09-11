# Reports — colgrep_mcp

## Round 00
- `00-architecture_v0.md` — architecture analysis: tool/resource/prompt surface, adapter contract, error model, risks (superseded by 02-architecture_v1.md for the deltas listed there)

## Round 01
- `01-findings_mcp_feature_matrix_v0.md` — systematic MCP feature matrix with adopt/defer decisions (latest)
- `01-findings_colgrep_behaviour_v0.md` — measured colgrep CLI behaviour + evidence (latest)

## Round 02
- `02-architecture_v1.md` — architecture delta after R02/R03: unit location by code match, heartbeat progress, project-root folding (latest)
- `02-observation_code_review_v0.md` — read-only code review: 5 confirmed bugs (subprocess/task leaks on client cancellation, `locate_unit` false positives, budget corner case), 6 risks, 3 consolidations; fixes tracked on `task/code_review_fixes` (latest)
- `02-findings_e2e_validation_v0.md` — end-to-end run against the real `colgrep` 1.6.2 and a `pallets/click` clone: warm/cold/warm stdio sessions, 17 calls each, median warm search 759 ms, cold build 16.2 s with 4 progress notifications, `claude --plugin-dir` connectivity gate passed; no defect (latest)

## Round 03
- `03-knowledge_transfer_v0.md` — 0.1.0 retrospective: wins, pain points, root causes, next-cycle changes, open questions (latest)

## Status
Campaign bootstrapped 2026-09-11. Architecture v0 by the team lead; round-01 findings by research agents. Round-02: architecture delta, clean real-binary e2e validation, code review with 12/14 findings fixed. Round-03: retrospective. Released as v0.1.0 on 2026-09-12.
