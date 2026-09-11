# Code Review Pass

**Goal**: Have a reader, not a test runner, trace the paths whose failure modes are hard to reproduce mechanically and turn what they find into observation reports the team can act on before release.
**Pre-conditions**:
- [ ] All `build/tools/integrate/*.md` leaves merged; full suite green
**Success Gates**:
- ✅ [static] `__reports__/colgrep_mcp/02-observation_code_review_v0.md` exists (one `observation` report per distinct finding is also acceptable, named `02-observation_<slug>_v0.md`), each finding with: file:line, the traced scenario, severity (bug / risk / consolidation), and a proposed fix
- ✅ [static] Every finding rated `bug` is either fixed in a `fix(<scope>): …` commit with a regression test, or explicitly deferred in the knowledge-transfer report with a reason
- ✅ [static] Review covers at minimum: `adapter._run` (timeout/kill/zombie, stderr drain deadlock, large stdout), `locate.locate_unit` (ambiguity, CRLF, trailing whitespace, code shorter than file tail), `tools_search.render_*` (budget backtracking termination, empty hits), `tools_index.index_build` heartbeat task cancellation on client disconnect, `index_clear` guard ordering, `paths.resolve_paths` (symlinks, `~`, files vs dirs), `resources` standalone adapter lifetime, `errors` coverage of every raise site
**References**: [R01 §Contracts & Invariants](../../../../../../__reports__/colgrep_mcp/00-architecture_v0.md); [R05](../../../../../../__reports__/colgrep_mcp/02-architecture_v1.md); `writing-reports` reference `observation.md`

## Step 1: Trace, report, and route fixes
**Goal**: Findings with enough context that a cold implementer can fix them without re-tracing.
**Implementation Logic**:
Reviewer (read-only) reads the modules listed in the gates against the R01/R05 invariants, tracing concrete scenarios (e.g. "client cancels during index_build: does the heartbeat task get cancelled and the subprocess killed?"; "two hits share a first line and the second's following line differs only by trailing whitespace"; "budget smaller than the header line"). Writes the observation report(s) with the `writing-reports` `observation` template. The lead triages: `bug` → dispatched as `fix(...)` commits with tests on `task/code_review_fixes`; `consolidation` → applied if under 30 lines of change, else recorded for the next cycle; `risk` → recorded in the knowledge-transfer report.
**References**: `/Users/me/.claude/skills/writing-reports/references/observation.md`
**Deliverables**: `__reports__/colgrep_mcp/02-observation_code_review_v0.md` (or per-finding files), `__reports__/colgrep_mcp/README.md` (round 02 entries), optional `fix(...)` commits with tests
**Consistency Checks**: `cd server && uv run pytest -q -p no:warnings` (expected: PASS)
**Commit**: `docs(reports): record code review findings and route fixes`
