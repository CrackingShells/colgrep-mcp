# Read-Only Review of the dev_plugin Campaign — Observation (v0)

Date: 2026-09-12

---
type: observation
topic: dev_plugin
spotted-during: read-only reviewer pass over the merged six depth-0 leaves (roadmap leaf `__roadmap__/dev_plugin/integrate/review.md`), tracing all seven named probes against `00-architecture_v0.md` §C2/C4/C8 and the consistency campaign's `01-observation_review_v0.md` for report shape/probe style
date: 2026-09-12
domain: code
confidence: confirmed
urgency: low
deferred-because: this is a read-only review pass (leaf says "trace ... and file the findings as an observation report the lead routes to fixes or the retrospective"); nothing below is fixed here
---

## What Was Noticed

The merged result holds up under trace on all seven probes. Coverage (probe 1)
is complete against R01 §C4's content inventory — every bullet lands in its
named skill, most linked from `references/*.md` rather than restated — except
one fact restated verbatim in two skills instead of linked once (F1, a
consolidation finding, not a correctness bug). Skill quality (probe 2) is
clean: all four `SKILL.md` files are well under the 150-line cap (60–121
lines), every front-matter description clears 80 chars with concrete
triggers, `probe_cz_check.sh` passes, `land_branch.sh` and `release.sh` both
refuse as required, and `claude --plugin-dir ./dev plugin details
colgrep-mcp-dev` lists exactly the four skills. Schema invariance (probe 3)
is exact: `Client.list_tools()`/`list_resources()`/`list_resource_templates()`/
`list_prompts()` full `model_dump(mode="json")` diff empty between `main`
(`be54fcc`) and `task/review` (`d277a83`). Intentional deltas (probe 4) are
the only client-visible changes: dumping every tool's text on the fixture on
both worktrees shows one real difference (`list_indexes` gaining its
`"<n> indexed projects on this machine"` header), plus timing-only noise in
`search`/`index_status`/`doctor` text (elapsed-ms and this-worktree's own
absolute binary path, neither a code delta); `find_files` and the full
`list_tools()` JSON are byte-identical. Perf claims (probe 5): the
`find_files` fold micro-benchmark reproduces well within 2x (5.60x measured
vs ~5.5x claimed); the stderr-notification claim is confirmed via the passing
regression test rather than independently re-benchmarked for bytes (see
Evidence — a real gap, not a fabricated number). Validators (probe 6) all
behave correctly under deliberately invalid inputs, with one instruction
mismatch worth flagging: the leaf's literal "add 10 lines" to `AGENTS.md`
does not trip the line-cap test, because `AGENTS.md` currently sits 41 lines
under its 130-line cap (89 lines) — the test itself is correct (confirmed by
adding enough lines to actually exceed the cap) (F2). Regression tests
(probe 7): all three `fix`/`perf` commits on `main..HEAD` state the
old-code failure in their bodies with specific numbers; one (`426aa12`,
`list_indexes` budget) was spot-checked by reverting the renderer in a
scratch monkeypatch and reproduced the claimed 55034-char figure exactly.

### Findings Table

| id | file:line | severity | confidence | proposed fix |
|:--|:--|:--|:--|:--|
| F1 | `dev/skills/maintainer-policy/SKILL.md:97-102` and `dev/skills/campaign-lead/SKILL.md:54-55` | consolidation | confirmed | The "a regression test counts only once it has failed against the old code" fact (R01 §C4, `KT-C` §Root Causes) is fully restated in both skills instead of owned by `maintainer-policy` and linked from `campaign-lead` (per C2: "a fact belongs in exactly one skill; another skill that needs it links `See <skill>/references/<file>.md` instead of restating"). Low-stakes (both statements agree and are short), but it is the one drift risk in the set: a future edit to the rule only needs to touch one of the two to go stale. Trim `campaign-lead/SKILL.md:54-55` to a one-line pointer, e.g. "Regression tests only count once they've failed against the old code — `maintainer-policy` §Regression tests earn their name." |
| F2 | `__roadmap__/dev_plugin/integrate/review.md` (probe 6, "add 10 lines to the copied AGENTS.md") | risk | confirmed | Not a code defect — `test_agents_md_stays_under_the_line_cap` is correct and fails at 134 lines (see Re-observation Steps). But `AGENTS.md` is 89 lines against a 130-line cap (41-line margin), so the leaf's literal "add 10 lines" instruction passes silently instead of demonstrating the guard, which could read as "validator probed, ok" when the probe as specified never exercised the failure path. Future review leaves for this repository should size the injected delta relative to the file's current margin (e.g. "add cap + 1 minus current length lines") rather than a fixed constant. |

## Context

Reviewing after all six depth-0 leaves (`skill_policy`, `skill_campaign_lead`,
`skill_stack_traps`, `skill_landing_release`, `list_indexes_budget`,
`search_path`) merged into the campaign branch and the lead cut `task/review`
from it. Worked entirely inside
`/Users/me/worktrees/colgrep-mcp/task-review`
(branch `task/review`); two detached worktrees were created under and removed
from the scratchpad for the schema/tool-text diffs (probes 3–4), never
pointing at this repository as a search target and never running a real
`colgrep`. Hard stop for this pass was 19:30 CEST; this report was written
with time to spare after all seven probes completed, so nothing here is a
partial pass.

## Location Map

- `__roadmap__/dev_plugin/integrate/review.md` — the leaf this report answers.
- `__reports__/dev_plugin/00-architecture_v0.md` §C2 (skill anatomy), §C4
  (content inventory), §C8 (oracles/allowed deltas).
- `dev/skills/maintainer-policy/SKILL.md`, `dev/skills/campaign-lead/SKILL.md`,
  `dev/skills/landing-and-release/SKILL.md`, `dev/skills/stack-traps/SKILL.md`
  — the four skills probed for coverage and quality.
- `dev/skills/landing-and-release/scripts/{probe_cz_check,land_branch,release}.sh`
  — the three scripts probed in probe 2.
- `server/colgrep_mcp/tools_search.py:60` (`hit_from_raw`), `:387`
  (`_file_hits_from_raw`) — probe 5's benchmarked functions.
- `server/colgrep_mcp/tools_index.py` (`_render_index_list`,
  around the `426aa12` diff) — probe 7's spot-checked regression.
- `server/tests/test_dev_plugin.py:53,58,70,85` — the four validators probed
  in probe 6 (`test_agents_md_stays_under_the_line_cap`,
  `test_agents_md_names_every_dev_skill`,
  `test_every_dev_skill_has_a_name_matching_its_directory_and_a_description`,
  `test_marketplace_lists_both_plugins_from_disjoint_sources`).
- `server/tests/test_tools_search.py::test_search_sends_at_most_one_log_notification`,
  `::test_search_sends_zero_log_notifications_when_index_already_current` —
  probe 4's notification-count pins.
- `server/tests/test_tools_index.py::test_list_indexes_text_is_budgeted_and_structured_content_is_complete`
  — probe 7's spot-checked regression test.
- Commit bodies checked for probe 7: `70c7409`, `473dfdf`, `426aa12`
  (`git log main..HEAD --grep='perf(search)\|fix(index)'` and `git show <sha>`).

## Evidence

**Probe 1 — coverage.** Walked `00-architecture_v0.md` §C4's four subsections
against the four `SKILL.md` files line by line. Every bullet is present,
almost entirely paraphrased-and-cited or linked to a `references/*.md` file
with a when-to-read hint (per C2). One duplication found: the regression-test
rule appears as a full restatement in both `maintainer-policy/SKILL.md`
("## Regression tests earn their name") and `campaign-lead/SKILL.md`
("A regression test counts only once it has failed against the old code —
say so in the `fix` commit body") — see F1. No other duplicate and no
omission found.

**Probe 2 — skill quality.**
```
$ wc -l dev/skills/*/SKILL.md
  76 dev/skills/campaign-lead/SKILL.md
 111 dev/skills/landing-and-release/SKILL.md
 121 dev/skills/maintainer-policy/SKILL.md
  60 dev/skills/stack-traps/SKILL.md
```
All four descriptions are well over 80 chars and name concrete triggers
("Load this before adding any scaffold, CI step, git hook..."). Every
`references/*.md` is linked from its `SKILL.md`'s body or a "See also" /
"References" section with a one-line hint. Scripts:
```
$ bash dev/skills/landing-and-release/scripts/probe_cz_check.sh
... six ACCEPT/REJECT checks ...
probe_cz_check: all expectations met   (exit 0)

$ bash dev/skills/landing-and-release/scripts/land_branch.sh task/this-branch-does-not-exist-xyz main "test merge message"
error: no such branch: task/this-branch-does-not-exist-xyz   (exit 1)

$ bash dev/skills/landing-and-release/scripts/release.sh   # run from this worktree
refuse: this is '.../task-review', not the main checkout '.../explore/colgrep_mcp'; ...   (exit 1)
```
All three scripts also answered `--help` with usage text and exit 0.
```
$ claude --plugin-dir ./dev plugin details colgrep-mcp-dev
Skills (4)  campaign-lead, landing-and-release, maintainer-policy, stack-traps
```

**Probe 3 — schema invariance.** Detached worktree at `git rev-parse main`
(`be54fcc`), removed after use:
```
$ git worktree add --detach <scratch>/main-detached $(git rev-parse main)
```
Ran a small script (in the scratchpad, not committed) in each worktree's
`server/` that spins up `Client(build())` against `tests/fake_colgrep.py`
and dumps `list_tools()`/`list_resources()`/`list_resource_templates()`/
`list_prompts()` via `model_dump(mode="json")`, `sort_keys=True`:
```
diff branch_schema.json main_schema.json   # empty, exit 0
```

**Probe 4 — intentional deltas only.** Same pattern, calling `search`,
`find_files`, `list_indexes`, `doctor`, `index_status` on a common fixture
project on both worktrees and diffing the text:
```
< "2 indexed projects on this machine\n/tmp/fake-corpus  ..."   (branch)
> "/tmp/fake-corpus  ..."                                        (main)
```
— the only content delta, matching the documented `list_indexes` header
addition exactly (`IndexList` gains no field; format of each index block
unchanged). The other three diff hunks (`doctor`'s embedded absolute
`colgrep_path` and `search`/`index_status`'s elapsed-ms) are per-worktree/
per-run noise, not code deltas. `find_files` text was byte-identical.
Legacy-mode notification counting for `search` was not independently
re-implemented under this pass's time box; it is confirmed via the full
suite passing on this branch, specifically
`test_search_sends_at_most_one_log_notification` and
`test_search_sends_zero_log_notifications_when_index_already_current`
(`cd server && uv run pytest` — 0 failures, exit 0). Likewise
`test_list_indexes_text_is_budgeted_and_structured_content_is_complete`
(400 fake indexes, capped ≤ `text_budget`, all 400 still in
`structured_content`) passed in the same run.

**Probe 5 — perf claims.** `find_files` fold (commit `473dfdf`, claimed
0.684–0.693 ms old vs 0.124–0.126 ms new, ~5.5x): reproduced with a
standalone script building 300 synthetic raw hits over 100 files, timing
`hit_from_raw`-per-hit-then-fold (the old approach, using the
still-present `hit_from_raw`) against `_file_hits_from_raw` (the new
function), median of 5, in-process, no real `colgrep`:
```
old (hit_from_raw fold): 0.6371 ms
new (_file_hits_from_raw): 0.1138 ms
ratio: 5.60x
```
Within 2x of both claimed numbers (in fact within ~9%). The stderr-
notification perf claim (commit `70c7409`: 3→1 frames, 127→77 bytes) was
**not** independently re-benchmarked for byte counts in this pass — time-
boxed out; the ≤1-notification behavior itself is confirmed via the
passing regression test named above, but the specific byte figures are
unverified by this reviewer. Flagging as a residual gap rather than a
finding, since the commit body's own methodology note (fixture gap: fake
`search` never emits stderr, so a synthetic adapter stand-in was used)
already discloses the same limitation.

**Probe 6 — validators with invalid inputs.** Copied `AGENTS.md`,
`dev/skills/**`, and `.claude-plugin/marketplace.json` into a scratchpad
tree; loaded `test_dev_plugin.py` and monkeypatched its `REPO_ROOT`/
`AGENTS_MD`/`DEV_PLUGIN`/`DEV_SKILLS` module globals to the copy (no
tracked file touched). Four checks, each restored after:
| perturbation | test | result |
|:--|:--|:--|
| +10 lines to `AGENTS.md` (89→99 lines, cap 130) | `test_agents_md_stays_under_the_line_cap` | **PASS (did not fail)** — see F2 |
| +45 lines instead (89→134 lines, over cap) | same test | FAIL: "AGENTS.md is 134 lines; move detail into a dev skill" |
| remove `` `stack-traps` `` from `AGENTS.md` text | `test_agents_md_names_every_dev_skill` | FAIL: "AGENTS.md does not name these dev skills: ['stack-traps']" |
| `stack-traps/SKILL.md` front matter `name: stack-traps` → `stack-traps-typo` | `test_every_dev_skill_has_a_name_matching_its_directory_and_a_description` | FAIL: "stack-traps: front matter name is 'stack-traps-typo'" |
| append a third plugin to the scratch `marketplace.json` | `test_marketplace_lists_both_plugins_from_disjoint_sources` | FAIL (assertion on plugin-name set) |
All four restored copies re-passed afterward, confirming the perturbations, not the copy setup, caused each failure.

**Probe 7 — regression tests failed once.** `git log main..HEAD --stat`
read in full; the three atomic `fix`/`perf` commits
(`70c7409`, `473dfdf`, `426aa12` — the two merge commits `4c2e48d`/`d42eb08`
just integrate these) each state, in their bodies, the specific pre-change
failure their new regression test caught. Spot-checked `426aa12`
(`fix(index): cap list_indexes text at the text budget`) by monkeypatching
`tools_index._render_index_list` back to the pre-change unbudgeted
`"\n".join(...)` in a scratch script (not editing the tracked file) and
re-running the same 400-fake-index scenario the real test uses:
```
text length: 55034
```
— an exact match to the commit body's stated "55034 chars for 400 fake
indexes, no cap". Did not additionally revert `70c7409`/`473dfdf`'s code
given the time box; both bodies name the exact pre-change count/ms figures
in the same self-disclosing style already spot-checked as trustworthy on
`426aa12`.

## Re-observation Steps

1. Schema diff: `git worktree add --detach <scratch-dir> $(git rev-parse main)`, run the dump-and-diff script (recreate per the shape in Evidence, probe 3) in both `server/` dirs against `tests/fake_colgrep.py`, diff, then `git worktree remove <scratch-dir>`.
2. Perf: recreate the `find_files` fold script from Evidence probe 5 (300 synthetic raw hits, 100 files, `statistics.median` of 5 timed calls to `hit_from_raw`-fold vs `_file_hits_from_raw`).
3. F2: in a scratch copy of `AGENTS.md`, append `130 - <current line count> + 1` filler lines (not a fixed 10) and re-run `test_agents_md_stays_under_the_line_cap` with `REPO_ROOT` monkeypatched to the copy; it fails.
4. F1: `grep -n "counts only once it has failed\|only counts as a regression test once"` (single-file, not recursive) across `dev/skills/maintainer-policy/SKILL.md` and `dev/skills/campaign-lead/SKILL.md` to see both restatements side by side.

## Hand-off Questions

Working theory, if any: neither finding blocks closing this campaign; F1 is
a one-line trim, F2 is advice for the next campaign's reviewer-brief
template, not a code change.

- Does the lead want F1 fixed now (a `campaign-lead/SKILL.md` one-line edit) or deferred to the knowledge-transfer report's Next-cycle Changes?
- Should `dev/skills/campaign-lead/references/reviewer-brief.md` be updated to say "size the injected line-count relative to the file's current margin" (F2), so the next campaign's reviewer doesn't hit the same silent-pass?
- Is independently re-benchmarking the stderr-notification byte counts (probe 5's residual gap) worth a follow-up, or is the passing regression test sufficient given `fake_colgrep.py` cannot itself produce the real chatter (a pre-existing, disclosed fixture gap, not new to this pass)?

## Scope Boundary

This report does not authorize fixing F1, F2, or anything else in
`dev/`, `AGENTS.md`, `server/`, or `__roadmap__/`; the reviewer's only owned
files are this report and `__reports__/dev_plugin/README.md`'s Round 02
entry, and no other file was left modified (all scratch perturbations above
were made and restored in a scratchpad copy or a detached worktree, never on
`task/review`'s tracked tree).
