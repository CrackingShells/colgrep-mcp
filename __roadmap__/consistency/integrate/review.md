# Read-Only Review

**Goal**: Trace the merged depth-0 result for what the tests cannot prove — schema invariance, leftover idioms, the perf claims, and the new module-global app handle — and file the findings as an observation report the lead routes to fixes or the retrospective.
**Pre-conditions**:
- [ ] Working in worktree `/Users/me/worktrees/colgrep-mcp/task-review` on branch `task/review` (created by the lead from the campaign branch **after** the four depth-0 leaves merged); this file exists there — if it does not, stop and report
- [ ] `cd server && uv run pytest` passes on the branch
**Success Gates**:
- ✅ [static] `__reports__/consistency/01-observation_review_v0.md` exists with the observation front matter and a findings table (id, file:line, severity bug/risk/consolidation, confidence, proposed fix)
- ✅ [run] the report's Re-observation Steps reproduce every `confirmed` finding from the scratchpad, never against a real `colgrep` and never against this repository
- ✅ [static] no file outside `__reports__/consistency/` is modified on this branch
**References**: [R01 all sections](../../../__reports__/consistency/00-architecture_v0.md) — the contracts to check against; [the 0.1.0 review](../../../__reports__/colgrep_mcp/02-observation_code_review_v0.md) — the report shape and the probe style to reuse

## Step 1: Probe and report
**Goal**: Findings a fresh agent can act on cold.
**Implementation Logic**:
Read `git log main..HEAD --stat` and the diff of `server/colgrep_mcp/`. Then probe, each in a scratchpad script against `tests/fake_colgrep.py`: (1) **Schema invariance** — `Client.list_tools()`, `list_resources()`, `list_resource_templates()`, `list_prompts()` dumped on `main` (use `git worktree add` of `main` into the scratchpad, or `git stash`-free checkout of the file set) and on this branch; diff must be empty. (2) **Leftover idioms** — grep `server/colgrep_mcp` for `from_adapter_error(` outside `errors.py`, `except Exception:` followed by `pass`, `Settings.from_env` outside `server.py`/`__main__.py`, `ToolAnnotations(read_only_hint=True` outside `server.py`, `_standalone_adapter`, `resolve_paths(` outside `paths.py`. (3) **App handle** — call `get_app()` with no running server and confirm `RuntimeError`; start two `Client(build())` sessions sequentially and confirm the second sees a fresh adapter (the first lifespan's `finally` cleared `_app`); think about (do not fix) what happens if two lifespans overlap in one process. (4) **`find_files` equivalence** — for the fixture, `files` list before/after (`main` vs branch) byte-identical. (5) **Perf claims** — re-run the two micro-benchmarks described in the `perf(search)` commit body and report whether the numbers reproduce within 2×. (6) **`resolve_target_paths`** — confirm `roots/list` is not sent when `COLGREP_MCP_ROOT` is set (count `list_roots` calls via monkeypatch) and is sent exactly once when it is unset and `paths` is `None`. (7) **Cancellation paths** — re-read `adapter._run` and `index_build` after the refactor; F1/F2 fixes must still be intact. Write `__reports__/consistency/01-observation_review_v0.md` (observation template: front matter, What Was Noticed, Context, Location Map, Evidence, Re-observation Steps, Hand-off Questions, Scope Boundary) and add it to `__reports__/consistency/README.md` under Round 01.
**Deliverables**: `__reports__/consistency/01-observation_review_v0.md`, `__reports__/consistency/README.md` (Round 01 entry)
**Consistency Checks**: `test -f __reports__/consistency/01-observation_review_v0.md` (expected: PASS); `git diff --name-only main..HEAD -- . ':!__reports__' | grep -v '^__roadmap__' | wc -l | grep -qx 0` (expected: PASS)
**Commit**: `docs(reports): record the read-only review of the consistency pass`
