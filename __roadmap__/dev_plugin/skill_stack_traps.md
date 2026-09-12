# Skill: Stack Traps

**Goal**: Ship `dev/skills/stack-traps/`, the skill that lists what colgrep, the MCP Python SDK v2 and Claude Code's plugin loader do behind a maintainer's back in this repository, with one triggering eval case.
**Pre-conditions**:
- [ ] Working in worktree `/Users/me/worktrees/colgrep-mcp/task-skill_stack_traps` on branch `task/skill_stack_traps` (created by the lead from the campaign branch); this file exists there — if it does not, stop and report
- [ ] R01 §C2 and §C4 `stack-traps` inventory read in full; the `skill-creator` skill loaded
**Success Gates**:
- ✅ [static] every bullet of R01 §C4 `stack-traps` appears once in the skill, each with its source id
- ✅ [run] `cd server && uv run pytest -q tests/test_dev_plugin.py` passes; `claude plugin validate ./dev` passes
- ✅ [static] `SKILL.md` ≤ 150 lines; each trap states symptom, cause and what to do in that order
**References**: [R01 §C2, §C4 stack-traps, §Eval case format](../../__reports__/dev_plugin/00-architecture_v0.md) — the anatomy, the fact inventory with sources, the case.yaml shape

## Step 1: Author the skill
**Goal**: An agent who loads this skill recognises a stack trap from its symptom before losing an hour to it.
**Implementation Logic**:
Description triggers: an agent is about to run `colgrep` by hand, run the e2e driver, add or change a tool/resource/prompt handler, touch the manifests or `.claude-plugin/mcp.json`, debug a plugin that does not connect, read a Windows CI failure, or sees `claude -p` fail. Organise by layer, one reference file each, and keep SKILL.md as the symptom index (a table: symptom you see → layer → reference anchor): `references/colgrep.md` (flag ordering `--color never <subcommand>` = search; ancestor-project folding and the ban on `colgrep init`/e2e against this repo and its worktrees, the e2e corpus path; wrong `line`/`end_line` and `locate.py`); `references/mcp-sdk.md` (`__doc__` shipped verbatim → `register_tool`; `validate_call` vs `functools.cache`; no `Context` for static resources and completions → `get_app(ctx=None)` on a `ContextVar`; 2026-07-28 deprecations, legacy-mode sessions for roots and elicitation, `safe_*`; `url2pathname` for Windows roots); `references/claude-code.md` (root `.mcp.json` is project config, placeholders in `args`/`env` never `command`, `${VAR:-default}` project-scope only, Agent Plugins forbids fallbacks, Codex unverified; marketplace vs plugin namespaces; `claude -p` on an expired OAuth session and the degraded gate `claude --plugin-dir . mcp list`; `claude plugin eval` needs the same auth); `references/machine.md` (the shell-search hook and heredocs, `COLGREP_BYPASS=1`; Windows CI `.cmd` wrapper and `setup-uv` pin; `git worktree add --detach $(git rev-parse main)` because `main` is checked out elsewhere). Cite sources as R01 §C4 gives them.
**Deliverables**: `dev/skills/stack-traps/SKILL.md`, `dev/skills/stack-traps/references/colgrep.md`, `dev/skills/stack-traps/references/mcp-sdk.md`, `dev/skills/stack-traps/references/claude-code.md`, `dev/skills/stack-traps/references/machine.md`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_dev_plugin.py && cd .. && claude plugin validate ./dev && test $(wc -l < dev/skills/stack-traps/SKILL.md) -le 150` (expected: PASS)
**Commit**: `docs(skill): add the stack-traps skill to the dev plugin`

## Step 2: Add the triggering eval case
**Goal**: A future authenticated session can measure that the skill fires on a realistic prompt that never names it.
**Implementation Logic**:
Write `dev/evals/stack-traps-triggers/case.yaml` in the shape of R01 §Eval case format with a prompt such as "the plugin shows a pending second colgrep entry and a spawn ENOENT when I open the repo, what is going on" or "check the index status of this repo with colgrep from the shell". Authored, not run.
**Deliverables**: `dev/evals/stack-traps-triggers/case.yaml`
**Consistency Checks**: `python3 -c "import yaml; d=yaml.safe_load(open('dev/evals/stack-traps-triggers/case.yaml')); assert d['graders'][0]['tool']=='Skill'"` (expected: PASS)
**Commit**: `test(skill): add the triggering eval case for stack-traps`
