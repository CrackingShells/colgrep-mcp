# Release 0.1.0

**Goal**: Cut v0.1.0: changelog entry, version alignment check, knowledge-transfer report, and the tag.
**Pre-conditions**:
- [ ] `e2e_validation` merged with no open `intervene` decision in its findings report
**Success Gates**:
- ⬜ [static] `CHANGELOG.md` has a `## [0.1.0] - 2026-09-12` section listing every `feat`/`fix` commit subject since the first commit, grouped Added/Fixed
- ⬜ [run] `cd server && uv run pytest -q` passes on the milestone branch head
- ⬜ [static] `__reports__/colgrep_mcp/03-knowledge_transfer_v0.md` exists (wins, pain points, next-cycle changes)
- ⬜ [static] `git tag -l v0.1.0` prints the tag on the merge commit into `main`
**References**: [R04 CONTRIBUTING §Versioning](../../../../../../CONTRIBUTING.md); `writing-reports` skill reference `software-knowledge-transfer.md`

## Step 1: Changelog and knowledge-transfer report
**Goal**: Leave the PI a release they can read and a retrospective the next cycle can act on.
**Implementation Logic**:
Generate the commit list with `git log --oneline --no-merges main..HEAD` (or from the first commit), map `feat`→Added, `fix`→Fixed, `perf`→Changed; write the `0.1.0` section; bump nothing (version already 0.1.0). Write the knowledge-transfer report with the `writing-reports` skill (`/Users/me/.claude/skills/writing-reports/references/software-knowledge-transfer.md`): what went well (parallel leaves against a written contract, fake binary), pain points (whatever the e2e report surfaced, spec churn from R02), next-cycle changes (PyPI publish, streamable-http, roots migration, icons). Update `__reports__/colgrep_mcp/README.md`.
**References**: [R02 Steering Questions](../../../../../../__reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md) — carry unresolved ones into next-cycle changes
**Deliverables**: `CHANGELOG.md` (`[0.1.0]` section), `__reports__/colgrep_mcp/03-knowledge_transfer_v0.md`, `__reports__/colgrep_mcp/README.md`
**Consistency Checks**: `grep -q "## \[0.1.0\]" CHANGELOG.md` (expected: PASS)
**Commit**: `docs(reports): write 0.1.0 changelog and knowledge-transfer retrospective`
