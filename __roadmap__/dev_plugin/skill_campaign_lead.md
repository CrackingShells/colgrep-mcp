# Skill: Campaign Lead

**Goal**: Ship `dev/skills/campaign-lead/`, the skill a lead loads to run a multi-agent campaign in this repository — dispatch, ownership, oracles, review — composing with the machine-level `writing-history`, `managing-roadmaps` and `writing-reports` skills instead of restating them, with the dispatch-prompt template as a reference and one triggering eval case.
**Pre-conditions**:
- [ ] Working in worktree `/Users/me/worktrees/colgrep-mcp/task-skill_campaign_lead` on branch `task/skill_campaign_lead` (created by the lead from the campaign branch); this file exists there — if it does not, stop and report
- [ ] R01 §C2 and §C4 `campaign-lead` inventory read in full; the `skill-creator` skill loaded; the dispatch prompt you received kept verbatim for Step 2
**Success Gates**:
- ✅ [static] every bullet of R01 §C4 `campaign-lead` appears once in the skill, each with its source id
- ✅ [run] `cd server && uv run pytest -q tests/test_dev_plugin.py` passes; `claude plugin validate ./dev` passes
- ✅ [static] `SKILL.md` ≤ 150 lines; `references/dispatch-prompt.md` has a placeholder for every field R01 lists (worktree path, branch, leaf file, ownership, gates, commit rules, hard stop, final-report shape)
**References**: [R01 §C2, §C4 campaign-lead, §Eval case format](../../__reports__/dev_plugin/00-architecture_v0.md) — the anatomy, the fact inventory with sources, the case.yaml shape

## Step 1: Author the skill
**Goal**: A lead who loads this skill dispatches without repeating the three cycles' mistakes.
**Implementation Logic**:
Description triggers: an agent is asked to lead, coordinate, plan or dispatch work on this repository, to create a roadmap or worktrees for subagents, to review a merged level, or to close a cycle. Body: the order of operations as a numbered checklist (architecture report → roadmap → commit specs and helpers → worktrees by hand → dispatch → merge per level → reviewer → knowledge transfer), each item one or two lines saying WHY (cite KT-B/KT-H/KT-C as R01 §C4 gives them), and a pointer to which machine skill does the mechanics (`writing-reports` for the report shapes, `managing-roadmaps` for `dirtree-rdm`, `writing-history` for rebase-then-`--no-ff`). Then the rules that are specific to this repository's history: hand-made worktrees from the campaign branch (the Agent tool's `isolation: worktree` branches from `main`), "stop if the leaf file is missing", file-disjoint ownership in the roadmap README, hard stops, lead-sized leaves stay with the lead, re-run the gates (agent counts are not evidence), reviewer after >2 parallel branches with intentional deltas and validator probing, dump-and-diff oracle for refactors, a regression test counts once it has failed, Windows CI as the portability oracle, subagents cannot watch CI in the background. Put in `references/`: `dirtree-gotchas.md` (the grammar traps and the `grammar leaf` command), `reviewer-brief.md` (what a read-only reviewer prompt contains: contract, intentional deltas, validator probes, report shape, worktree-detach trick), `dispatch-prompt.md` (Step 2). Keep SKILL.md to the checklist and the rules; depth goes to references.
**Deliverables**: `dev/skills/campaign-lead/SKILL.md`, `dev/skills/campaign-lead/references/dirtree-gotchas.md`, `dev/skills/campaign-lead/references/reviewer-brief.md`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_dev_plugin.py && cd .. && claude plugin validate ./dev && test $(wc -l < dev/skills/campaign-lead/SKILL.md) -le 150` (expected: PASS)
**Commit**: `docs(skill): add the campaign-lead skill to the dev plugin`

## Step 2: Add the dispatch-prompt template
**Goal**: The prompt shape three cycles converged on is a file a lead copies, not something re-derived.
**Implementation Logic**:
The dispatch prompt you received for this leaf is that shape. Reproduce it in `dev/skills/campaign-lead/references/dispatch-prompt.md` with `<placeholders>` for the worktree path, branch, leaf file, campaign branch, owned files, gate commands, commit rules, hard stop time, and the final-report shape (what was done, gates output, files touched outside ownership reported not edited, anything unfinished). Add one paragraph before it saying why each field exists (each maps to a failure from KT-B/KT-H/KT-C).
**Deliverables**: `dev/skills/campaign-lead/references/dispatch-prompt.md`
**Consistency Checks**: `test -f dev/skills/campaign-lead/references/dispatch-prompt.md && test $(wc -l < dev/skills/campaign-lead/references/dispatch-prompt.md) -ge 30` (expected: PASS)
**Commit**: `docs(skill): record the dispatch-prompt template in campaign-lead`

## Step 3: Add the triggering eval case
**Goal**: A future authenticated session can measure that the skill fires on a realistic lead prompt that never names it.
**Implementation Logic**:
Write `dev/evals/campaign-lead-triggers/case.yaml` in the shape of R01 §Eval case format with a prompt such as "run the next cycle on this repo with three Sonnet implementers; here are the follow-ups". Authored, not run.
**Deliverables**: `dev/evals/campaign-lead-triggers/case.yaml`
**Consistency Checks**: `python3 -c "import yaml; d=yaml.safe_load(open('dev/evals/campaign-lead-triggers/case.yaml')); assert d['graders'][0]['tool']=='Skill'"` (expected: PASS)
**Commit**: `test(skill): add the triggering eval case for campaign-lead`
