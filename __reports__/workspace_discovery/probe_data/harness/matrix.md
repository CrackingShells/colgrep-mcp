# Harness × workspace-signal measurement matrix

Columns are R01's fixed set (§Per-harness measurement matrix): `initialize
capabilities`, `request _meta keys`, `roots/list verdict`, `successor
(2026-07-28)`, `spawn env relevant vars`, plus `Channel Map` (R02 station ids)
and `Notes`. Every cell is measured from a raw JSONL probe record or `—`
(silence). No cell is rounded, inferred, or synthesized.

| harness | initialize capabilities | request `_meta` keys | `roots/list` verdict | successor (2026-07-28) | spawn env relevant vars | Channel Map | Notes |
|---|---|---|---|---|---|---|---|
| `claude` | — | — | — | — | — | Station 3 (initialize); Station 2 (request `_meta`); Station 1 (`roots/list` + successor); env (launch pin) | gap record `claude_tool-20261127_141546.jsonl`: `{"error": "claude completed but no probe record written"}` — no R01-schema fields emitted, so no measured cells |
| `codex` | — | — | — | — | — | Station 3 (initialize); Station 2 (request `_meta`); Station 1 (`roots/list` + successor); env (launch pin) | gap record `codex_tool-20261127_141606.jsonl`: `{"error": "codex completed but no probe record written"}` — no R01-schema fields emitted, so no measured cells |
| `copilot-agent-plugins` | — | — | — | — | — | Station 3 (initialize); Station 2 (request `_meta`); Station 1 (`roots/list` + successor); env (launch pin) | no `copilot_tool-*.jsonl` present in raw store; reuse-by-filename-match absent, row recorded as `—` |
