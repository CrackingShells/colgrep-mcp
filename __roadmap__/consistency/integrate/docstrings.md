# Docstrings: Why, Not Roadmap Narration

**Goal**: Make every docstring in `server/colgrep_mcp/` say what the object is for and why it is shaped that way, strip the roadmap-process narration that leaked in ("Step 1 provides…", "Implemented in leaf…", "PI request … mid-run"), and give the report ids they cite a legend in `AGENTS.md` together with the one-idiom-per-concern rules this campaign established.
**Pre-conditions**:
- [ ] Working in worktree `/Users/me/worktrees/colgrep-mcp/task-docstrings` on branch `task/docstrings` (created by the lead from the campaign branch **after** the four depth-0 leaves merged); this file exists there — if it does not, stop and report
- [ ] `cd server && uv run pytest` passes before any change
**Success Gates**:
- ✅ [run] `cd server && uv run pytest` passes; `uv run ruff check` clean; `git diff --stat` shows only docstring/comment lines changed in `server/` (no executable line changes — verify with `git diff -U0 server | grep '^[-+]' | grep -v '^[-+][-+]'` and read it)
- ✅ [static] no docstring under `server/colgrep_mcp/` or `server/tests/` contains `Step 1`, `Step 2`, `roadmap leaf`, `Implemented in leaf`, `mid-run`
- ✅ [static] `AGENTS.md` has a "Report ids in docstrings" table and four "one idiom" rules under §Conventions
**References**: [R01 §C6](../../__reports__/consistency/00-architecture_v0.md) — the docstring contract; [AGENTS.md](../../../AGENTS.md) — keep it under ~130 lines and pointer-heavy

## Step 1: Strip narration, keep the why
**Goal**: A cold agent reading a module learns what it owns and why, not which campaign step produced it.
**Implementation Logic**:
For every `.py` under `server/colgrep_mcp/` and `server/tests/`: rewrite module docstrings to state (a) what the module owns, (b) what it must never do (e.g. `adapter.py`: "the only module that spawns a process"; `errors.py`: "the only module that owns the code vocabulary"), (c) which report holds the measured evidence, by id. Remove sentences about roadmap steps, leaves, who implemented what, and the PI request wording. Function docstrings: keep the WHY paragraphs (they are good) but drop step/leaf references. Report ids (`R01`, `R05 D1`, `F11`, `R03`) stay — they are pointers, and Step 2 gives them a legend. **Do not change any executable line.** `ruff check` must stay clean (an import made unused by a docstring edit is impossible; if `ruff` complains, you changed code).
**Deliverables**: `server/colgrep_mcp/*.py`, `server/tests/*.py` (docstrings only; read `git diff -U0 HEAD~1 -- server | grep '^[-+]'` yourself before committing and confirm every changed line is prose)
**Consistency Checks**: `cd server && uv run pytest -q` (expected: PASS); `! COLGREP_BYPASS=1 grep -rqE 'Step [0-9]|roadmap leaf|Implemented in leaf|mid-run' server/colgrep_mcp server/tests` (expected: PASS); `cd server && uv run ruff check` (expected: PASS)
**Commit**: `docs(server): strip roadmap narration from docstrings and keep only the why`

## Step 2: Legend and rules in AGENTS.md
**Goal**: The report ids become resolvable, and the idioms this campaign unified become rules a future agent reads before adding a tool.
**Implementation Logic**:
In `AGENTS.md` §Conventions add four bullets: tools are module-level `async def … (*, ctx: Context)` registered in `register()` with `READ_ONLY_TOOL` where read-only; paths resolve through `paths.resolve_target_paths` only; adapter calls are wrapped in `errors.translate_adapter_errors` only; client notifications go through `logging_utils.safe_*` only. Add a §"Report ids in docstrings" table right after §Repo map: `R01 (colgrep_mcp)` → `__reports__/colgrep_mcp/00-architecture_v0.md`; `R03` → `01-findings_colgrep_behaviour_v0.md`; `R05` (with `D1–D11`, `M1–M5` its sections) → `02-architecture_v1.md`; `F1–F14` → `02-observation_code_review_v0.md`; `R01 (repo_health)` → `__reports__/repo_health/00-architecture_v0.md`; `R01 (consistency)` → `__reports__/consistency/00-architecture_v0.md`. Note in one sentence that the same `R01` label is reused per campaign and the module docstring's topic disambiguates. Keep the file under ~130 lines.
**Deliverables**: `AGENTS.md` (§Conventions four bullets; §Report ids in docstrings table)
**Consistency Checks**: `grep -q 'resolve_target_paths' AGENTS.md && grep -q 'Report ids' AGENTS.md` (expected: PASS); `test $(wc -l < AGENTS.md) -le 135` (expected: PASS)
**Commit**: `docs(docs): add the report-id legend and the one-idiom-per-concern rules to AGENTS.md`
