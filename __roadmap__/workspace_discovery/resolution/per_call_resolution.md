# Per-call workspace resolution ladder (meta, roots, pin, fail+guidance)

**Goal**: Land the sponsor-folded resolution ladder in `paths.py`: per-call argument > per-call dynamic discovery (request `_meta` vendor keys and per-call client roots) > `COLGREP_MCP_ROOT` pin > fail with guidance naming an absolute `paths` entry.
**Pre-conditions**:
- [ ] `probe_hardening` is `done` (its truth-source probe and calibration oracle are what these rungs are measured against)
- [ ] R03b decided this ladder: [03-findings_live_probe_v0.md](../../__reports__/workspace_discovery/03-findings_live_probe_v0.md) — both dynamic channels measured working; the pin and fail+guidance are the degradation ladder beneath them
**Success Gates**:
- ✅ `cd server && uv run pytest -q` green with tests that pin every rung: explicit `paths` wins, `_meta` stamp resolves per call, rooted answer resolves per call (AFTER `probe_hardening`'s race fix — a late-arriving roots answer must not lose to a premature `cwd` fallback), `COLGREP_MCP_ROOT` applies only when both dynamic rungs are silent, and a silent-everything call raises the guidance error naming the `paths` remedy
- ✅ The served guide `server/colgrep_mcp/guide.md` states the ladder order and the `paths` remedy; `test_readme.py`/drift tests stay green
- ✅ Resolution outcome is byte-identical with the probe disabled (dump-only law intact from step 0 of `probe_hardening`)
**References**: [R01 §Proposed State](../../__reports__/workspace_discovery/00-architecture_v0.md) — the ladder diagram this implements; [R03b §Results](../../__reports__/workspace_discovery/03-findings_live_probe_v0.md) — the live evidence for each dynamic rung; [02-gap_analysis](../../__reports__/workspace_discovery/02-gap_analysis_calibrated_probe_v0.md) — what the calibration tests must catch while this lands

## Step 1: Consume per-call request meta in the resolver
**Goal**: `paths.resolve_target_paths` reads workspace location from request `_meta` before anything else dynamic.
**Implementation Logic**:
Rung-2a of the ladder. In `paths.py`, `resolve_target_paths` (or a pure helper called by it for testability) reads `ctx.request_context.meta` — via the same `getattr` spines the probe now records — and extracts a workspace directory from documented keys in priority order: an alias list (e.g. `com.visualstudio.code/workspaceFolder`, `com.visualstudio.code/workspace`, plus the repo-documented colgrep key if any) then a single documented primary key. Absent or non-path values degrade to the next rung (never raise). The key list is a module-level constant `META_WORKSPACE_KEYS` — one idiom, one list. Verification trail: fabricated `_meta` stamps in unit tests use `forge_record` snapshots so the probe's `request_meta` column and the resolver agree on what a stamp looks like.
**Deliverables**: `server/colgrep_mcp/paths.py` (exports `META_WORKSPACE_KEYS`, `default_root_from_meta`); `server/tests/test_paths_resolution.py` (`test_meta_stamp_beats_pin_and_cwd`, `test_meta_absent_falls_back_silently`, `test_meta_alias_priority`)
**Consistency Checks**: `grep -q '_meta' __reports__/workspace_discovery/03-findings_live_probe_v0.md` (expected: PASS)
**Commit**: `feat(server): resolve the default root from per-call request meta`

## Step 2: Per-call roots without the first-call race
**Goal**: The client-roots rung answers from what the client actually sent, never from a lost race.
**Implementation Logic**:
Rung-2b. `client_roots` (shared with the probe call — one round-trip per call, `maintainer-policy` hardware-first) must await the `roots/list` response to completion before concluding; a timeout or remote method-absence classifies `error`-classed roots per `probe` step 1 (`error` is not `empty`). Registration of `list_changed` remains best-effort on 2025-11-25 dialects and must not defer the first answer. The regression test reproduces the measured race from R03b's ledgers (first `resolve` empty-answer → `cwd`, second → `roots`) and asserts the new behaviour resolves `roots` on the first call; it must fail against the pre-fix code to earn its name.
**Deliverables**: `server/colgrep_mcp/paths.py` (`client_roots` awaits completion distinctly classifies error/empty); `server/tests/test_paths_resolution.py` (`test_first_call_roots_race_regression`, `test_roots_error_falls_to_pin`)
**Consistency Checks**: `grep -q 'race' __reports__/workspace_discovery/03-findings_live_probe_v0.md` (expected: PASS)
**Commit**: `feat(server): resolve per-call roots without the first-call race`

## Step 3: Wire the ladder, the pin rung, and fail+guidance
**Goal**: The rung order `paths > dynamic > COLGREP_MCP_ROOT > guided failure` is the single resolution idiom, documented in the served guide.
**Implementation Logic**:
Compose `default_root(settings, roots, meta_root) -> (root, source)` with sources `paths` \| `meta` \| `roots` \| `env` \| `cwd`, meta before roots before env-pin per the sponsor fold (explicit argument stays first at the `paths`-level); `resolve_paths` documents that relative entries resolve against this default. When all rungs are silent (no meta, roots error/empty, no pin, and cwd is not a plausible project root — the R01 guarded-cwd condition), raise `Code.ROOT_UNRESOLVED` (advisory id; use the existing error-code registry) whose message names the remedy verbatim: pass an absolute `paths` entry. `guide.md` §Scoping gains the ladder and the remedy sentence (this is the client-visible behaviour change — a pinned test per `maintainer-policy`). Multi-root policy documented: roots[0] when several, surfaced via the existing `root_source` label.
**Deliverables**: `server/colgrep_mcp/paths.py` (`default_root` ladder sources); `server/colgrep_mcp/errors.py` (`ROOT_UNRESOLVED` code with guidance text); `server/colgrep_mcp/guide.md` (§Scoping ladder + remedy); `server/tests/test_paths_resolution.py` (`test_ladder_order_pins_each_rung`, `test_silence_fails_with_paths_guidance`, `test_root_source_labels`)
**Consistency Checks**: `grep -q 'fail+guidance\|fail with guidance' __roadmap__/workspace_discovery/resolution/per_call_resolution.md` (expected: PASS)
**Commit**: `feat(search): land the per-call resolution ladder with guided failure`
