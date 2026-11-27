# Workspace-channel protocol survey

**Goal**: Publish the per-station workspace-channel verdicts — which dynamic per-call signals the MCP wire, as pinned in this environment, can actually carry — in the R02 findings report.
**Pre-conditions**:
- [ ] Campaign README and R01 committed on the campaign branch (this leaf reads only committed material plus the pinned `mcp` SDK source)
- [x] `cd server && uv run python -c "import mcp; print(mcp.__file__)"` resolves to this worktree's `.venv` (environment contract, 2026-11-12)
**Success Gates**:
- ✅ `test -s __reports__/workspace_discovery/01-findings_protocol_survey_v0.md` and its front matter parses to `type: findings`, `topic: workspace_discovery`, `version: v0`, `prior-version: none`, `decision-required: confirm`
- ✅ The verdict table's `duration` and `invoker_coverage` columns are non-empty for every row; every row's `evidence_for` cites an identifier (`mcp <version> <module/spec §>`) or `—` guarded by "dialect has no timestamp"
- ✅ No raw JSON schema dump, SDK source excerpt, or HTML appears in the report body (competition against the steering bullets wins every merge conflict)
**References**: [R01 §Contracts & Invariants](../../__reports__/workspace_discovery/00-architecture_v0.md) — probe dump schema the survey's channels must map onto

## Step 1: Author the channel verdicts
**Goal**: Fill R02 — every candidate per-call workspace channel adjudicated as `dynamic`/`static`/`none`/`?` with citations and a minimal diagram.
**Implementation Logic**:
Write `__reports__/workspace_discovery/01-findings_protocol_survey_v0.md` following the `writing-reports` §findings contract exactly (front matter block first, then Headline Result key/value block, Results Tables, Observations four-column table, ≤5 Steering Questions, Pointers = links only). Survey stations: (1) client `roots` capability on the 2026-07-28 MCP revision — `roots/list` deprecation and whatever the pinned `mcp` SDK (version recorded from `uv pip show mcp`) exposes as its successor (`notification/roots/list_changed` status included); (2) request `_meta` presence on `tools/call` in the SDK's `Context.request_context` — what key, if any, a host can stamp per call; (3) `initialize` handshake context fields. Evidence policy: claims come from the installed SDK's own source (read-only, cite module + symbol), the MCP specification versions the SDK names, and the repo's own `R05 M1` note (AGENTS.md report-id table); raw corpus runs of other harnesses are expressly out of scope (that is `collect_harness_evidence`'s job — this leaf surveys mechanism, not behaviour). Where the wire cannot carry a channel at the pinned version, verdict is `static` or `none` and the `invoker` column names who must hold the value in that case (host spawn env / user pin / none — fail+guidance). One Mermaid diagram maps signals to the R01 resolution-ladder rungs. Facts (SDK version, spec section ids, symbol names) are cited in `evidence_for`; conclusion prose in its own column; `<` and `|` stripped from cells.
**Deliverables**: `__reports__/workspace_discovery/01-findings_protocol_survey_v0.md` (front matter fields `type/topic/date/version/prior-version/key-metric/decision-required`; `## Headline Result` with `metric: dynamic_channels_found`; one Mermaid signal-to-rung diagram; Results Tables `station|verdict|evidence_for|invoker|duration|invoker_coverage` and `channel|window|trigger|validation|notes`; Observations four-column table)
**Consistency Checks**: `grep -q '^type: findings' __reports__/workspace_discovery/01-findings_protocol_survey_v0.md && grep -q '^## Headline Result' __reports__/workspace_discovery/01-findings_protocol_survey_v0.md` (expected: PASS)
**Commit**: `docs(reports): survey per-call workspace channels on the MCP wire`
