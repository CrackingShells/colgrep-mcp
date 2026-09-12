# Skill: Maintainer Policy

**Goal**: Ship `dev/skills/maintainer-policy/`, the skill that tells a maintaining agent whom this repository is for and how code quality is judged here ("for agents, by agents" and hardware-first code), with one triggering eval case.
**Pre-conditions**:
- [ ] Working in worktree `/Users/me/worktrees/colgrep-mcp/task-skill_policy` on branch `task/skill_policy` (created by the lead from the campaign branch); this file exists there — if it does not, stop and report
- [ ] R01 §C2 (skill anatomy) and §C4 `maintainer-policy` inventory read in full; the `skill-creator` skill loaded
**Success Gates**:
- ✅ [static] every bullet of R01 §C4 `maintainer-policy` appears once in the skill (SKILL.md or a reference), each with its source id
- ✅ [run] `cd server && uv run pytest -q tests/test_dev_plugin.py` passes; `claude plugin validate ./dev` passes
- ✅ [static] `SKILL.md` ≤ 150 lines; front matter `name: maintainer-policy`; description ≥ 80 chars stating when to load it
**References**: [R01 §C2, §C4 maintainer-policy, §Eval case format](../../__reports__/dev_plugin/00-architecture_v0.md) — the anatomy, the fact inventory with sources, the case.yaml shape

## Step 1: Author the skill
**Goal**: A cold agent that loads this skill judges a proposed change the way the last three cycles did.
**Implementation Logic**:
Follow `skill-creator`: front matter `name`, then a description that says what the skill does AND concrete triggers — an agent is about to add scaffold, CI, hooks, docs, or a "best practice"; is reviewing or refactoring server code; is choosing between `perf` and `refactor`; is writing a docstring; is asked "should we add X to the repo". Body (imperative, WHY before rule): the two consumer kinds and the README exception; the "which agent command or failure does this remove?" test for any ceremony; CI-only enforcement; drift tests over process with the list of existing guards; docstrings cite report ids from the `AGENTS.md` legend; the hardware-first section with the input-proportional-work hunt list and the "I/O-bound is not an argument" reasoning; the one-idiom-per-concern helper table; the perf-commit convention (median of 5, synthetic corpora in the scratchpad, never the real colgrep against this repo, reviewer reproduces within 2×, no numbers → `refactor`); regression tests count once they have failed against the old code; client-visible behaviour changes only with a leaf and a pinning test. Put the long lists in `references/`: `references/input-proportional-waste.md` (the hunt list with the measured examples from KT-C: find_files 63.4→0.65 ms, expand 6.1→0.03 ms, per-spawn env copy, per-lock resolve, per-request guide read) and `references/drift-tests.md` (what each existing drift test pins and the recipe for a new one: dry-run the generator against the existing artefact, diff, then pin the parseable shape). Cite sources as R01 §C4 gives them. Do not restate CONTRIBUTING's type table; link it.
**Deliverables**: `dev/skills/maintainer-policy/SKILL.md`, `dev/skills/maintainer-policy/references/input-proportional-waste.md`, `dev/skills/maintainer-policy/references/drift-tests.md`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_dev_plugin.py && cd .. && claude plugin validate ./dev && test $(wc -l < dev/skills/maintainer-policy/SKILL.md) -le 150` (expected: PASS)
**Commit**: `docs(skill): add the maintainer-policy skill to the dev plugin`

## Step 2: Add the triggering eval case
**Goal**: A future authenticated session can measure that the skill fires on a realistic prompt that never names it.
**Implementation Logic**:
Write `dev/evals/maintainer-policy-triggers/case.yaml` exactly in the shape of R01 §Eval case format, with a prompt such as an agent being asked to "add a pre-commit hook and a PR template to this repo" or "this function is I/O-bound so the extra file read doesn't matter, right?" — something the skill should catch. The case is authored, not run (`claude -p` is unusable here); do not attempt `claude plugin eval`.
**Deliverables**: `dev/evals/maintainer-policy-triggers/case.yaml`
**Consistency Checks**: `python3 -c "import yaml,sys; d=yaml.safe_load(open('dev/evals/maintainer-policy-triggers/case.yaml')); assert d['graders'][0]['tool']=='Skill'"` (expected: PASS)
**Commit**: `test(skill): add the triggering eval case for maintainer-policy`
