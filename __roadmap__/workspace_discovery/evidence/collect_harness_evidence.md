# Collect harness probe artifacts

**Goal**: Run the probe driver under each reachable harness and record raw JSONL evidence per harness plus the consolidated signal matrix — measured values or `—`, never synthesized.
**Pre-conditions**:
- [ ] `probe_instrumentation` merged to the campaign branch: `git cat-file -e <campaign-branch>:server/tests/e2e/probe_workspace.py` exits 0 in this worktree
- [ ] R02 (`01-findings_protocol_survey_v0.md`) exists on the campaign branch so the matrix's `Channel Map` column can cite its station ids
- [ ] Hard stop honoured: campaign README §Gotchas names the dispatch window close; stop there and commit whatever is green
**Success Gates**:
- ✅ `__reports__/workspace_discovery/probe_data/harness/raw/` contains one `claude_tool-*.jsonl` and one `codex_tool-*.jsonl` *or* a gap record naming the harness and the failure mode (`{"error": ...}` — unstubbed result is a named gap, not an invented value)
- ✅ `test -s __reports__/workspace_discovery/probe_data/harness/matrix.md` and every harness row has exactly one cell per matrix column (value or `—`)
**References**: [R01 §Per-harness measurement matrix](../../../__reports__/workspace_discovery/00-architecture_v0.md) — the column set this leaf must not alter; [L1 R01 §Probe dump schema](../../../__reports__/workspace_discovery/00-architecture_v0.md) — what each raw JSONL line must contain

## Step 1: Claude harness run
**Goal**: Capture `claude -p` probe evidence into the raw store.
**Implementation Logic**:
Invoke the driver from the campaign branch (tool-owned: the leaf only orchestrates) as `COLGREP_MCP_PROBE=<tmp> uv run python server/tests/e2e/probe_workspace.py --harness claude --out __reports__/workspace_discovery/probe_data/harness/raw/claude_tool-$(date +%Y%m%d_%H%M%S).jsonl`. The driver stubs `colgrep` on `$PATH` and calls `doctor` only — no real search, no index writes (stack-traps). A run that times out, fails to spawn, or leaves no ledger yields a gap record at the same path (`{"error": "<stage>: <stderr head>"}`); do not retry more than 2 attempts, do not hand-edit any raw artifact. If the run succeeds, copy the JSONL verbatim (schema keys already validated by the driver).
**Deliverables**: `__reports__/workspace_discovery/probe_data/harness/raw/claude_tool-*.jsonl` (verbatim driver output or `{"error": ...}` gap record)
**Consistency Checks**: `ls __reports__/workspace_discovery/probe_data/harness/raw/claude_tool-*.jsonl` (expected: PASS)
**Commit**: `chore(repo): record claude harness probe artifacts`

## Step 2: Codex harness run
**Goal**: Capture `codex exec` probe evidence into the raw store.
**Implementation Logic**:
As step 1 with `--harness codex` and raw name `codex_tool-*.jsonl`: `codex exec` non-interactively, same stubbed `PATH`, same `doctor`-only trigger, same 2-attempt limit and gap-record discipline. `codex`'s terminal escaping may flatten output — the raw artifact keeps what it printed; flattening is reported in the matrix `Notes` column in step 3, never guessed behind.
**Deliverables**: `__reports__/workspace_discovery/probe_data/harness/raw/codex_tool-*.jsonl` (verbatim driver output or `{"error": ...}` gap record)
**Consistency Checks**: `ls __reports__/workspace_discovery/probe_data/harness/raw/codex_tool-*.jsonl` (expected: PASS)
**Commit**: `chore(repo): record codex harness probe artifacts`

## Step 3: Consolidated signal matrix
**Goal**: Publish the harness × signal matrix with every cell measured or `—`.
**Implementation Logic**:
Write `__reports__/workspace_discovery/probe_data/harness/matrix.md`: one row per harness (`claude`, `codex`, `copilot-agent-plugins`), columns exactly R01's: `initialize capabilities | request _meta keys | roots/list verdict | successor (2026-07-28) | spawn env relevant vars`. Cells are filled only from the corresponding raw JSONL fields (probe dump schema keys) crossed with R02's station ids in a final `Channel Map` column; absent evidence writes `—` plus the gap record name in `Notes`. The `copilot-agent-plugins` row may be filled from raw JSONL a previous collection dropped in the same raw dir (reuse by filename match `copilot_tool-*.jsonl`), else `—`. No cell is inferred, rounded, or synthesized (competition rule: silence loses to signal, and `—` is the recorded silence).
**Deliverables**: `__reports__/workspace_discovery/probe_data/harness/matrix.md` (rows per harness; columns `initialize capabilities`, `request _meta keys`, `roots/list verdict`, `successor (2026-07-28)`, `spawn env relevant vars`, `Channel Map`, `Notes`)
**Consistency Checks**: `grep -c '^| ' __reports__/workspace_discovery/probe_data/harness/matrix.md` (expected: PASS)
**Commit**: `docs(reports): consolidate harness probe matrix`
