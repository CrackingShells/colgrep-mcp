# Reviewer Pass

**Goal**: Read the merged depth-0 diff for what the tests cannot prove and file an observation report the lead can triage before release.
**Pre-conditions**:
- [ ] `python_tooling` and `launcher` merged into the campaign branch; `cd server && uv run pytest` passes there
**Success Gates**:
- ✅ [static] `__reports__/repo_health/01-observation_review_v0.md` exists, follows the observation template, and every finding carries `confidence` and `urgency`
- ✅ [static] no file outside `__reports__/repo_health/` is modified by this leaf
**References**: [R01 all contracts and risks](../../../__reports__/repo_health/00-architecture_v0.md) — check the diff against them; [`git diff v0.1.0..HEAD`] — the material under review

## Step 1: Review and report
**Goal**: Findings, not fixes.
**Implementation Logic**:
Read-only. Check: (1) does the commitizen `schema_pattern` accept exactly the CONTRIBUTING types with a mandatory scope, and reject `feat: x` and `chore(repo): x.`-style violations — try `cz check --message` on a handful of good and bad subjects; (2) does `cz bump --dry-run --increment PATCH` list all five files and would the `version_files` patterns also touch any line they must not (e.g. `$schema` URLs containing `1.0.0`); (3) are the launch argv, placeholders and env blocks consistent across `.mcp.json`, `mcp.json`, and the two plugin manifests, and does `test_manifests.py` actually assert that; (4) does `importlib.metadata` resolve the right distribution when the package is imported from `server/` with the editable install; (5) anything the README now promises that the manifests do not do. For each finding: confidence (hunch/plausible/confirmed), urgency, location map, evidence, hand-off question. Write `__reports__/repo_health/01-observation_review_v0.md`. Consolidations and non-blocking suggestions go in a final "Notices" list.
**Deliverables**: `__reports__/repo_health/01-observation_review_v0.md` (front matter, What Was Noticed per finding, Location Map, Evidence, Hand-off Questions, Scope Boundary, Notices)
**Consistency Checks**: `test -z "$(git diff --name-only HEAD~1 | grep -v '^__reports__/repo_health/')"` (expected: PASS)
**Commit**: `docs(reports): record the reviewer pass over the repo_health depth-0 changes`
