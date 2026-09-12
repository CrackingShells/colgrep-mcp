# Branch Cleanup, Retrospective and Release

**Goal**: Apply accepted review findings, delete the merged 0.1.0 branches, write the retrospective, land the campaign on `main` and cut 0.1.1 with `cz bump`.
**Pre-conditions**:
- [ ] `integrate/agent_docs.md`, `integrate/ci_workflow.md`, `integrate/review.md` are `done`
- [ ] Lead has triaged `01-observation_review_v0.md`
**Success Gates**:
- ✅ [run] `git branch --merged main | grep -cE 'task/|milestone/|worktree-agent-'` prints 0 after the release
- ✅ [run] `git tag` lists `v0.1.1`; `git -C /Users/me/colgrep-mcp log --oneline -1` shows `release(colgrep-mcp): v0.1.1`
- ✅ [run] `cd server && uv run pytest` passes on `main` after the bump
- ✅ [static] `__reports__/repo_health/02-knowledge_transfer_v0.md` exists; `__reports__/repo_health/README.md` indexes rounds 00–02
**References**: [R01 §C1](../../../../__reports__/repo_health/00-architecture_v0.md) — release recipe; [writing-history branches.md] — rebase, re-verify, `--no-ff`

## Step 1: Apply accepted review fixes
**Goal**: Close the confirmed findings before release.
**Implementation Logic**:
Lead triages the observation report: confirmed + high/medium → fix on the campaign branch (one commit per finding class, vocabulary type by nature: `fix`/`build`/`docs`); hunch or low → listed as deferred in the retrospective. Re-run pytest, ruff, cz check.
**Deliverables**: fixes as required by the report (files named there)
**Consistency Checks**: `cd server && uv run pytest -q && uv run ruff check && uv run cz check --rev-range v0.1.0..HEAD` (expected: PASS)
**Commit**: `fix(repo): apply the confirmed reviewer findings before the 0.1.1 release`

## Step 2: Write the retrospective and index the reports
**Goal**: Leave the next cycle its starting point.
**Implementation Logic**:
`02-knowledge_transfer_v0.md` per the knowledge-transfer template: what shipped, wins, pain points, root causes, next-cycle changes (PyPI publish → `uvx`; `ruff format` sweep; Windows result from CI once a remote exists; homepage URL in manifests names a GitHub repo that does not exist yet; `server/README.md` is a stub that PyPI would show), artefacts, open questions. Update `__reports__/repo_health/README.md` with rounds 00 (architecture, launch placeholders findings), 01 (review observation), 02 (knowledge transfer).
**Deliverables**: `__reports__/repo_health/02-knowledge_transfer_v0.md`, `__reports__/repo_health/README.md`
**Consistency Checks**: `test -f __reports__/repo_health/02-knowledge_transfer_v0.md` (expected: PASS)
**Commit**: `docs(reports): write the repo_health retrospective and index the reports`

## Step 3: Delete merged campaign branches, land on main, bump
**Goal**: A clean branch list and a release cut by the machinery it introduces.
**Implementation Logic**:
Verify every `task/*`, `milestone/*`, `worktree-agent-*` branch has zero commits ahead of `main` (`git rev-list --count main..<b>`), then `git branch -d` each (safe delete refuses anything unmerged). Mark the roadmap nodes `done` with dirtree-rdm and commit. Then, with the `main` checkout at `/Users/me/colgrep-mcp` verified clean: `git -C <main> merge --no-ff claude/mcp-server-repo-health-e13188` with a message naming the campaign; `cd <main>/server && uv run pytest`; `uv run cz bump --changelog` (expected `0.1.0 → 0.1.1`: the campaign contains `fix(plugin)` commits and no `feat`); `uv sync`; `uv run pytest` again (the version drift test now checks 0.1.1 everywhere). Roadmap status update is the commit of this step; the bump commit is written by cz.
**Deliverables**: deleted branches; `__roadmap__/repo_health/**` status all done; on `main`: merge commit, `release(colgrep-mcp): v0.1.1` commit, tag `v0.1.1`, `CHANGELOG.md` 0.1.1 section, manifests at 0.1.1
**Consistency Checks**: `git -C /Users/me/colgrep-mcp tag --points-at HEAD` (expected: `v0.1.1`); `cd /Users/me/colgrep-mcp/server && uv run pytest -q` (expected: PASS)
**Commit**: `docs(roadmap): close campaign repo_health — all nodes done`
