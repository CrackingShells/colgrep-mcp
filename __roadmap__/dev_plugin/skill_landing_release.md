# Skill: Landing and Release

**Goal**: Ship `dev/skills/landing-and-release/`, the skill for this repository's git and release mechanics — commits, integration, PR landing, `cz bump` release — with scripts for the mechanical steps and one triggering eval case.
**Pre-conditions**:
- [ ] Working in worktree `/Users/hacker/Documents/tmp/claude-worktrees/colgrep_mcp/task-skill_landing_release` on branch `task/skill_landing_release` (created by the lead from the campaign branch); this file exists there — if it does not, stop and report
- [ ] R01 §C2 and §C4 `landing-and-release` inventory read in full; `CONTRIBUTING.md` and `server/pyproject.toml` `[tool.commitizen]` read; the `skill-creator` skill loaded
**Success Gates**:
- ✅ [static] every bullet of R01 §C4 `landing-and-release` appears once in the skill, each with its source id; nothing restates CONTRIBUTING's type table (link it)
- ✅ [run] `bash dev/skills/landing-and-release/scripts/probe_cz_check.sh` exits 0 in this worktree (every expected accept/reject matches); `cd server && uv run pytest -q tests/test_dev_plugin.py` passes; `claude plugin validate ./dev` passes
- ✅ [static] `SKILL.md` ≤ 150 lines; the three scripts are executable, print usage on `--help`, and stop on the first red gate
**References**: [R01 §C2, §C4 landing-and-release, §Eval case format](../../__reports__/dev_plugin/00-architecture_v0.md) — the anatomy, the fact inventory with sources, the case.yaml shape

## Step 1: Author the skill
**Goal**: An agent who loads this skill lands and releases without the detours of the last three cycles.
**Implementation Logic**:
Description triggers: an agent is about to commit, rebase, merge, open or land a PR, resolve a merge conflict, cut a release, bump a version, edit the changelog, or hit a `cz check` failure in this repository. Body sections, each WHY first: commit shape (link CONTRIBUTING for the table; add the probe command and the four invalid subjects to try); integration (rebase → gates → `git merge --no-ff -m`, never `-F -`; conflict-marker search after any conflicting merge; anchored `.gitignore`; never bare `git stash` because the stash is shared across worktrees); branches and worktree cleanup; landing a PR (`gh pr create`, CI jobs to wait for, `gh pr merge --merge --subject "<subject> (PR #N)"`, why a local rebase-merge leaves the PR open); release (main checkout only, the recipe, lightweight tag pushed by name, the permission-classifier detour from a detached worktree); commitizen gotchas as a table (symptom → cause → what to do). Put the gotcha table in `references/commitizen-gotchas.md` and the PR/CI sequence in `references/landing-a-pr.md`; SKILL.md keeps the flow and the script names.
**Deliverables**: `dev/skills/landing-and-release/SKILL.md`, `dev/skills/landing-and-release/references/commitizen-gotchas.md`, `dev/skills/landing-and-release/references/landing-a-pr.md`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_dev_plugin.py && cd .. && claude plugin validate ./dev && test $(wc -l < dev/skills/landing-and-release/SKILL.md) -le 150` (expected: PASS)
**Commit**: `docs(skill): add the landing-and-release skill to the dev plugin`

## Step 2: Add the mechanical scripts
**Goal**: The steps that are the same every time run as one command that refuses to continue past a red gate.
**Implementation Logic**:
Three bash scripts under `dev/skills/landing-and-release/scripts/`, each with `set -euo pipefail`, a `--help`, and `echo` of every step before it runs. `land_branch.sh <task-branch> <target-branch>`: checks the working tree is clean, rebases `<task-branch>` onto `<target-branch>`, runs `cd server && uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run cz check --rev-range <target>..<task>`, merges into `<target>` with `--no-ff -m "$3"` (third arg: the merge message, mandatory), then searches the tree for conflict markers and fails if any remain; it never pushes. `probe_cz_check.sh`: runs `uv run cz check --message` from `server/` over a table of subjects with expected exit codes (accept: `feat(search): add x`, `release(colgrep-mcp): v0.1.2`; reject: `feat: add x`, `chore(repo): tidy.`, `Feat(search): add x`, `style(server): x`) and exits non-zero on any mismatch — this is the validator probe the review process asks for. `release.sh`: refuses unless the current directory is inside the main checkout (`git rev-parse --show-toplevel` equals `git worktree list` first entry) and the branch is `main` and the tree is clean; prints `cz bump --changelog --dry-run`; on `--run`, executes `uv run cz bump --changelog && uv run pytest -q` from `server/` and prints the exact `git push origin main v<x.y.z>` line (it does not push). Do not run `release.sh --run` yourself.
**Deliverables**: `dev/skills/landing-and-release/scripts/land_branch.sh`, `dev/skills/landing-and-release/scripts/probe_cz_check.sh`, `dev/skills/landing-and-release/scripts/release.sh`
**Consistency Checks**: `bash dev/skills/landing-and-release/scripts/probe_cz_check.sh && bash dev/skills/landing-and-release/scripts/release.sh --help >/dev/null && bash dev/skills/landing-and-release/scripts/land_branch.sh --help >/dev/null` (expected: PASS)
**Commit**: `chore(skill): add the land, probe and release scripts to landing-and-release`

## Step 3: Add the triggering eval case
**Goal**: A future authenticated session can measure that the skill fires on a realistic prompt that never names it.
**Implementation Logic**:
Write `dev/evals/landing-and-release-triggers/case.yaml` in the shape of R01 §Eval case format with a prompt such as "the task branch is green, get it onto main and cut the patch release". Authored, not run.
**Deliverables**: `dev/evals/landing-and-release-triggers/case.yaml`
**Consistency Checks**: `python3 -c "import yaml; d=yaml.safe_load(open('dev/evals/landing-and-release-triggers/case.yaml')); assert d['graders'][0]['tool']=='Skill'"` (expected: PASS)
**Commit**: `test(skill): add the triggering eval case for landing-and-release`
