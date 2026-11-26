# Docs and Naming

**Goal**: Teach every reader where each loader finds the hooks, and record the warning text so the next agent recognises the trap before losing an hour.
**Pre-conditions**:
- [ ] `R01` is committed; its §Contracts is the prose this leaf must stay equal to
**Success Gates**:
- ✅ README's Hooks and Troubleshooting sections name both paths and both tokens, with the v1 warning text verbatim [static]
- ✅ `AGENTS.md` names `com.github.copilot/hooks/hooks.json` and `cd server && uv run pytest tests/test_dev_plugin.py -q` passes its line cap [run]
- ✅ `dev/skills/stack-traps/` carries the symptom row and an `#agent-plugins-hooks` reference section citing `R01` [static]
**References**: [R01 §Evidence](../../__reports__/hook_namespace/00-architecture_v0.md) — the loader behaviour each sentence must stay equal to

## Step 1: Teach the README and AGENTS.md the two paths
**Goal**: Make the landing page and the agent surface state, in the same terms, which loader reads which file with which token.
**Implementation Logic**:
`README.md`: in §Hooks after the loader-semantics paragraph, add the v1 rule — a plugin declaring the Agent Plugins v1 `$schema` has its hooks read only from `com.github.copilot/hooks/hooks.json` (token `${PLUGIN_ROOT}`) while `hooks/hooks.json` keeps serving Claude Code and Codex (`${CLAUDE_PLUGIN_ROOT}`), the two files one policy mirrored and the drift guards keeping them identical modulo the token. In §Troubleshooting's "The hooks do not fire" entry, add the v1 case with the symptom verbatim ("Some hook files could not be loaded") and the path to check. In §Repository map, correct "the one placeholder both ecosystems expand": three loaders, two token spellings. `AGENTS.md`: the repo-map `hooks/` row names `com.github.copilot/hooks/hooks.json` beside the root file, and the report-id legend gains `R01 (hook_namespace)`. The file is capped at 130 lines (`test_dev_plugin.py::test_agents_md_stays_under_the_line_cap`, 127 today) — move detail into a dev skill rather than growing it.
**Deliverables**: `README.md` — §Hooks v1 paragraph, §Troubleshooting v1 case, §Repository map token sentence; `AGENTS.md` — `hooks/` repo-map row and `R01 (hook_namespace)` legend row
**Consistency Checks**: `cd server && uv run pytest tests/test_dev_plugin.py -q` (expected: PASS)
**Commit**: `docs(readme): name where each loader finds the hooks`

## Step 2: Record the trap in stack-traps
**Goal**: Make the warning self-diagnosing for the next agent that loads this plugin.
**Implementation Logic**:
In `dev/skills/stack-traps/`: add one row to `SKILL.md`'s symptom index — "a plugin declaring the Agent Plugins v1 `$schema` shows 'Some hook files could not be loaded' and runs no hook in VS Code or Copilot" resolving to `references/claude-code.md#agent-plugins-hooks` — and write the `#agent-plugins-hooks` section in `references/claude-code.md`: symptom (the warning, and the hooks silently not firing), cause (the v1 loader reads only the reverse-DNS mirror; `hooks/hooks.json` is the legacy contract), and what to do (mirror the portable file under `com.github.copilot/hooks/hooks.json` with `${PLUGIN_ROOT}`; never move the root file and never name `./hooks/hooks.json` in the Claude manifest), citing `R01` (hook_namespace). Keep the skill's always-on budget in mind (AGENTS.md: ~530 tokens across four skills).
**Deliverables**: `dev/skills/stack-traps/SKILL.md` — symptom-index row; `dev/skills/stack-traps/references/claude-code.md` — `#agent-plugins-hooks` section
**Consistency Checks**: `cd server && uv run pytest -q` (expected: PASS)
**Commit**: `docs(skill): diagnose the Agent Plugins v1 hook path trap`
