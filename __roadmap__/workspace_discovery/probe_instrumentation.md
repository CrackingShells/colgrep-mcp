# Probe instrumentation for workspace signals

**Goal**: Land an inert, dump-only probe facility and harness driver that record what dynamic workspace signals each harness actually delivers, changing no resolution behaviour.
**Pre-conditions**:
- [x] Campaign README, R01 and this leaf committed to the campaign branch (KT-B: worktrees see only committed files)
- [ ] Baseline green on this worktree: `cd server && uv run pytest -q` exits 0 before the first edit
**Success Gates**:
- ✅ `cd server && uv run pytest -q` exits 0 with `test_probe.py` in tree; `test_no_probe_side_effects` (the dump-only oracle) fails against the base commit this branch was cut from and passes here
- ✅ With `COLGREP_MCP_PROBE` unset, `capture_pure` round-trips byte-identical records and `resolve_target_paths` results equal the base behaviour in `test_capture_matches_runtime`
- ✅ `server/tests/e2e/probe_workspace.py` runs `doctor` against a packaged server and writes one JSONL record per tool call with the R01 §Probe dump schema keys
**References**: [R01 §Probe dump schema](../../__reports__/workspace_discovery/00-architecture_v0.md) — `init_capabilities`, `request_meta`, `roots_list`, `env` digest keys the driver must name

## Step 1: Probe dump facility
**Goal**: Add the workspace-signal probe as an inert module hooked only behind `COLGREP_MCP_PROBE`.
**Implementation Logic**:
New `server/colgrep_mcp/probe.py`: `capture_pure(snap) -> str` serializes a snapshot dict to one JSONL line (sorted keys, no volatile fields); `record(tool, raw_paths, ctx)` builds `{ts, server_pid, tool, raw_paths, env: {COLGREP_MCP_ROOT, COLGREP_MCP_BINARY, spawn_env_digest}, init_capabilities, request_meta, roots_list, resolved, cwd}` and appends to `$COLGREP_MCP_PROBE/colgrep_probe.jsonl` inside `try/except OSError: pass` with `logging_utils.safe_log` on failure — the probe must never raise into the resolve path. Wire one call at the top of `paths.resolve_target_paths` gated on `os.environ.get("COLGREP_MCP_PROBE")`, reading `init_capabilities`/`request_meta` from `ctx.request_context` via `getattr` (SDK absent or fragment = recorded as `None`, never inferred). `roots_list` records the *outcome* of the existing `client_roots` call (declared/empty/error + items); sharing that call rather than adding a second one keeps resolution cost unchanged (maintainer-policy §hardware-first — no new round-trip per call). The resolve chain itself is not otherwise touched: this step is observable-behaviour inert by construction (maintainer-policy §Client-visible behaviour).
Pseudo-code for the hook point only: `if probe_enabled: record(...)  # best effort` precedes the existing `settings = get_settings(ctx)` line. No change to `resolve_paths`/`default_root` precedence.
**Deliverables**: `server/colgrep_mcp/probe.py` (exports `capture_pure`, `record`, `PROBE_ENV`); `server/colgrep_mcp/paths.py` (one gated probe call in `resolve_target_paths`, otherwise unchanged); `server/tests/test_probe.py` (`test_capture_matches_runtime`, `test_probe_inert_without_env`, `test_no_probe_side_effects`)
**Consistency Checks**: `cd server && uv run pytest tests/test_probe.py -q` (expected: PASS)
**Commit**: `refactor(server): record workspace-signal probe behind COLGREP_MCP_PROBE`

## Step 2: Harness probe driver and dump-only guard
**Goal**: Add the probe-driven harness evidence driver and the regression tests that pin probe inertness.
**Implementation Logic**:
New `server/tests/e2e/probe_workspace.py` (not collected by pytest): a driver that (1) launches the packaged server through a named harness `Claude|Codex` via `subprocess` (`claude -p` / `codex exec` non-interactively with the canned single-line trigger), with a minimal stub `$PATH` shadowing `colgrep` so no real index is touched (stack-traps); (2) the stub's `doctor` subcommand writes one R01-schema JSONL record per invocation to `$COLGREP_MCP_PROBE/colgrep_probe.jsonl` and prints the static `doctor` payload; (3) the driver copies the JSONL to a named raw file and validates records deterministically (schema keys present). Timeout, non-zero exit and missing-ledger cases append an explicit gap record (`{"error": "<what failed>"}`) — raw evidence or a named gap, never a synthesized value. Newest 3 dated raw directories rotate out at 4 — bounded growth without destroying recent evidence. The trigger string is one constant `TRIGGER_PROMPT` ("Run the colgrep doctor tool now. Reply done.") so its shape is diffable.
`test_no_probe_side_effects` (regression test; failed against base in the first build attempt = the honest record required by maintainer-policy §Regression tests): with `COLGREP_MCP_PROBE` unset, a dump of `Client.list_tools()/list_resources()/list_prompts()` is unstaged-JSON-identical to the base dump produced by the same test, and `capture_pure` output is byte-identical across calls; with `COLGREP_MCP_PROBE` set and a temp dir, a resolved-path call writes exactly one record whose `resolved.source` equals the control run's `root_source`. `test_capture_matches_runtime` asserts the recorded `resolved` equals what `resolve_target_paths` returned on that call.
**Deliverables**: `server/tests/e2e/probe_workspace.py` (exports `main`, `collect_for(harness)`, `TRIGGER_PROMPT`); `server/tests/test_probe.py` (extended with `test_no_probe_side_effects`, `test_capture_matches_runtime`); `__reports__/workspace_discovery/probe_data/.gitignore` ("*\n!.gitignore\n")
**Consistency Checks**: `cd server && uv run pytest tests/test_probe.py -q` (expected: PASS)
**Commit**: `test(tests): pin probe inertness and add probe_workspace harness driver`
