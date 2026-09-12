# Agent Orientation Docs

**Goal**: Give a cold LLM agent one file that says where things live, which commands are gates, and which traps the previous campaign hit.
**Pre-conditions**:
- [ ] `python_tooling` and `launcher` merged into the campaign branch
**Success Gates**:
- ✅ [static] `AGENTS.md` exists; every command it lists runs from the stated directory and exits 0 on the campaign branch
- ✅ [static] `CLAUDE.md` contains exactly one line, `@AGENTS.md`
- ✅ [static] `README.md` §Development points agents at `AGENTS.md`
**References**: [R01 §C4](../../../__reports__/repo_health/00-architecture_v0.md) — content contract; [0.1.0 retrospective](../../../__reports__/colgrep_mcp/03-knowledge_transfer_v0.md) — traps and next-cycle changes to carry over

## Step 1: Write AGENTS.md and the CLAUDE.md import
**Goal**: One body of orientation text readable by Claude Code, Codex and Agent Plugins clients.
**Implementation Logic**:
Lead-authored. Sections: what this repo is (one paragraph), repo map (table: path → what it holds → who edits it), gate commands (pytest, ruff check, cz check, cz bump --dry-run, claude plugin validate, claude --plugin-dir . mcp list), conventions (pointer to CONTRIBUTING, branch model, one step = one commit), release recipe (pointer), coordination artefacts (`__reports__/`, `__roadmap__/`, dirtree-rdm), known traps (never run e2e against this repo; `--color` before the subcommand indexes the cwd; worktrees see only committed files; grep conflict markers before committing a merge; manifests' version is written by cz bump only). Keep it under ~120 lines; no duplication of README content beyond a pointer. Add one sentence to README §Development pointing agents at `AGENTS.md`.
**Deliverables**: `AGENTS.md` (sections above), `CLAUDE.md` (`@AGENTS.md`), `README.md` (§Development pointer)
**Consistency Checks**: `test -f AGENTS.md && test "$(cat CLAUDE.md)" = "@AGENTS.md"` (expected: PASS); `cd server && uv run pytest -q tests/test_readme.py` (expected: PASS)
**Commit**: `docs(repo): add AGENTS.md orientation for maintaining agents and import it from CLAUDE.md`
