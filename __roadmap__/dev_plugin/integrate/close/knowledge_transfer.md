# Knowledge Transfer and Release

**Goal**: Close the campaign: retrospective written, PR landed, v0.1.3 released from the main checkout, worktrees and merged branches removed.
**Pre-conditions**:
- [ ] `integrate/review` and `integrate/surface` merged; every confirmed review finding fixed or routed to the retrospective
- [ ] Lead-implemented
**Success Gates**:
- ✅ [run] PR CI green on ubuntu, macos, windows and the commit-message job; landed with `gh pr merge --merge --subject "<subject> (PR #N)"`
- ✅ [run] `cd server && uv run cz bump --changelog && uv run pytest` from the main checkout; `git push origin main v0.1.3`; `git worktree list` shows only the main checkout and this session's worktree
- ✅ [static] `__reports__/dev_plugin/03-knowledge_transfer_v0.md` with Wins, Pain Points, Root Causes, Next-cycle Changes, Open Questions; README updated
**References**: [R01 §Risks](../../../__reports__/dev_plugin/00-architecture_v0.md) — the risks to report against; [the consistency retrospective](../../../__reports__/consistency/02-knowledge_transfer_v0.md) — the shape and the follow-ups this campaign consumed

## Step 1: Write the retrospective
**Goal**: The next cycle starts from this report's Next-cycle Changes.
**Implementation Logic**:
Knowledge-transfer template (writing-reports): what shipped, wall time and agent count, per-leaf minutes from the Progress tables; wins and pain points from the dispatch and review; root causes; instruction/workflow/review changes — and, since the skills now exist, state which skill each change was written into (a pain point that reached no skill is a defect). Carried items not done this cycle: PyPI publish (credentials), Codex placeholder verification (no CLI), Agent Plugins `COLGREP_MCP_ROOT` asymmetry; running the four eval cases once `claude -p` authenticates.
**Deliverables**: `__reports__/dev_plugin/03-knowledge_transfer_v0.md`, `__reports__/dev_plugin/README.md`
**Consistency Checks**: `test -f __reports__/dev_plugin/03-knowledge_transfer_v0.md` (expected: PASS)
**Commit**: `docs(reports): close the dev_plugin campaign with its knowledge-transfer report`
