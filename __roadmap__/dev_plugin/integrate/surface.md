# Surface: AGENTS.md, CLAUDE.md, CONTRIBUTING.md

**Goal**: The orientation files say only what the repo is, the gates, how to load the dev plugin, and which skill fires when; everything else lives in a skill and is pointed at, not repeated.
**Pre-conditions**:
- [ ] The four skill leaves merged into the campaign branch (their descriptions are the source of the skill table)
- [ ] Lead-implemented on the campaign branch directly
**Success Gates**:
- ✅ [run] `cd server && uv run pytest -q tests/test_dev_plugin.py tests/test_readme.py` green
- ✅ [static] `AGENTS.md` ≤ 130 lines; `CONTRIBUTING.md` under 60 lines; no paragraph of either restates a fact a skill carries (a pointer with the skill name is fine)
**References**: [R01 §C3 surface files](../../../__reports__/dev_plugin/00-architecture_v0.md) — what each file keeps

## Step 1: Rewrite the surface
**Goal**: A cold agent reads 130 lines and knows where every other answer lives.
**Implementation Logic**:
`AGENTS.md`: keep §What this is, §Repo map (add `dev/` and `dev/evals/` rows), §Report ids (add `R01 (dev_plugin)`), §Gate commands (add `ruff format --check`, `claude plugin validate ./dev`); replace §Conventions, §Coordinating a campaign and §Traps with §Maintainer skills: the load line and a table `skill | load it when` built from each SKILL.md description, then one line per former section pointing at the skill that now holds it. `CONTRIBUTING.md`: keep the type/bump table and the scope list (mirrors of `[tool.commitizen]`), the release recipe block, the branching bullets; replace the rest with a pointer to `landing-and-release` and `maintainer-policy`. `CLAUDE.md` unchanged (`@AGENTS.md`). `dev/README.md`: check it still matches. Also fold the `AGENTS.md` §Traps bullets into a final check that each now exists in `stack-traps` or `landing-and-release`; if one does not, add it to the right skill in this same commit and say so in the body.
**Deliverables**: `AGENTS.md`, `CONTRIBUTING.md`, `dev/README.md`
**Consistency Checks**: `cd server && uv run pytest -q tests/test_dev_plugin.py tests/test_readme.py && test $(wc -l < ../CONTRIBUTING.md) -lt 60` (expected: PASS)
**Commit**: `docs(docs): reduce AGENTS.md and CONTRIBUTING.md to the surface that points at the dev plugin skills`
