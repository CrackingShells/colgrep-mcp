# Reports — colgrep_mcp

## Round 00
- `00-architecture_v0.md` — architecture analysis: tool/resource/prompt surface, adapter contract, error model, risks (superseded by 02-architecture_v1.md for the deltas listed there)

## Round 01
- `01-findings_mcp_feature_matrix_v0.md` — systematic MCP feature matrix with adopt/defer decisions (latest)
- `01-findings_colgrep_behaviour_v0.md` — measured colgrep CLI behaviour + evidence (latest)

## Round 02
- `02-architecture_v1.md` — architecture delta after R02/R03: unit location by code match, heartbeat progress, project-root folding (latest)
- `02-findings_e2e_validation_v0.md` — end-to-end run of the assembled server against the real `colgrep` 1.6.2 binary and a real `pallets/click` clone: 3 stdio sessions (warm, cold, warm again), 17 tool/resource/prompt calls each, `claude --plugin-dir` behavioural + connectivity gate. No defect found; no `fix(...)` commit needed (latest)

## Status
Campaign bootstrapped 2026-09-11. Architecture v0 authored by the team lead; round-01 findings delegated to research agents. Round-02 adds the architecture delta and the first real-binary end-to-end validation, both clean.
