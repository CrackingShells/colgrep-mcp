# Hook Namespace — Knowledge Transfer (v0)

Date: 2026-11-27

## Executive Summary
- **What shipped:** the portable hook policy is now mirrored at
  `com.github.copilot/hooks/hooks.json` with `${PLUGIN_ROOT}` as its root token, so the
  Agent Plugins v1 loader family — VS Code, the GitHub Copilot CLI — reads the plugin's
  hooks instead of reporting "Some hook files could not be loaded". `hooks/hooks.json` and
  `hooks/worktree-remove.json` are byte-unchanged, so Claude Code and Codex see no change.
  Two drift guards pin the pair and the manifest route that could bypass it; README,
  `AGENTS.md` and `stack-traps` now name which loader reads which file with which token.
- **Primary outcomes:**
  - Zero merged commits change anything in `server/` beyond `tests/test_hooks.py`; the
    product's runtime behaviour is untouched apart from hooks firing where they did not.
  - Four probes, no breaks: the scratch-marketplace install lists all four hooks,
    Codex's resolution still points at the root file, the mirrored command returns the
    policy, and the VS Code observation is a release-path fact rather than a defect.
  - The planned suite of three guards shipped as two: the third was mutation-checked
    and cut as tautological before it was written.
- **Cost:** zero subagent dispatches. 3 lead commits (R01, roadmap, corrections) plus
  4 leaf commits (1 on L1, 2 on L2, 1 on L3), folded into 3 leaf merges by the
  rebase-then-`--no-ff` contract.

## Wins
- **The bug was confirmed in sources before a line moved.** Three independent sources
  (VS Code `pluginParsers.ts`, a third party's Codex-CLI verification, another repo's
  plan) plus a schema read gave `R01` its evidence chain; Probes 1/2/4 then re-verified
  the mechanism cheaply rather than arguing from the warning text alone.
- **The first `cz check --message` probe lied about its own result** — a bare exit code
  check cannot tell "pass" from "fail", since a passing subject and an unrelated bad
  subject both gate 0/14 in confusing ways. Caught by pairing each probe with a known
  bad subject and reading the validator output ("Commit validation: successful!"
  vs. the pattern spill). Every merge subject after that was probed properly.
- **The plan caught its own tautology before execution.** Extending the launcher sweep
  to the mirror (G2) survives mutation of *every* per-command property once G1's
  `mirror ≡ swap(root)` equality holds. Cut with its rationale recorded in `R01`
  §Alternatives, so nobody re-adds it as "coverage".
- **The testing discipline paid off in an unexpected place**: my probe-4 script swapped
  the token inside a `print()`, so the diff compared *unswapped* data. What caught it
  was G1's `assert swapped != root` non-identity rule — the guard's anti-vacuity line.
- **Disjoint leaf ownership kept the merges boring.** L1 touched only
  `com.github.copilot/**` and `test_hooks.py`; L2 only README/`AGENTS.md`/`stack-traps`;
  L3 only reports and roadmap prose. All three `git show --stat` containment checks
  named exactly the intended files, and no conflicts appeared.

## Pain Points
- **Two stray `cd server` mistakes hit `git add`:** one commit attempt ran `git add`
  from `server/` (pathspec miss), and a later retry ran in the *campaign* worktree and
  got "nothing to commit". Each cost a round-trip to notice.
- **`pytest -q` summary is buried under the MCP deprecation warning tail**, so the
  summary line is not in the last lines of output. I ran the suite twice in one command
  to get it — that command also exceeded the 30s read window and had to be stopped.
- **The leaf's `**Commit**` field and the commit body diverge**: the field says
  `docs(readme): …` but the body reports the `AGENTS.md` + `stack-traps` work too, so
  `git log` under-reports the step. It is the field as written (verbatim per
  `landing-and-release` OBS-H Check 1), so the fix is the field, not the subject.
- **SLA: probe 3 cannot observe what a live VS Code session shows**, because the
  installed copy is 0.6.0 and ships no mirror by design. Accepted as byte-level
  evidence plus a release-path note, but it leaves the actual GUI quieting unverified.
- **`joblib` is jargon everywhere** in this campaign's prose (the tools named it that
  way on purpose; `joblib` oz). It is fine for this repo's reader but the phrase "one
  job" appears where "one commit" would be clearer.

## Root Causes
- **The learner's first `cz check` probes gated on the raw exit code
  instead of the validator's verdict,** so a bad subject looked passing. A probe that
  cannot distinguish its own outcomes is exactly the tautology class `designing-tests`
  warns about — the mistake it is warning about was being made *by* the probe.
- **The path context of Bash calls is not sticky,** and `cd server` (running Python
  tooling) is the repo's most common command, so the next command in the sequence often
  inherits the wrong directory silently.
- **The plan used one filename across its own text inconsistently** (`01-observation_*`
  in the roadmap deliverables vs `01-findings_*` in prose) because the phase-1 plan was
  written mid-skills-load, before the `findings` shape settled. Sed fixed it after the
  fact; naming discipline at author time would have avoided it.

## Next-cycle Changes
- **Instruction changes**
  - Probe `cz check --message` with one accepted *and* one rejected subject in the same
    call, and read the verdict line; never gate on exit code alone.
  - Before writing any report, fix its filename to its shape (`findings` vs `observation`
    vs `knowledge_transfer`) *before* any leaf cites it; a sed across references afterwards
    is a smell.
- **Workflow changes**
  - Give every Bash call an explicit `cd <worktree>` as its first token when it stages or
    commits, even when the previous call "should" have left the right directory.
  - For suite summaries use `--no-header -p no:warnings` and read the *count*, not the
    last line; do not double-run the suite to chase a summary.
  - Waste check (new): the two stray-`cd` incidents and the double-run cost roughly a
    minute each; both are avoidable by the two rules above, worth about 4 minutes per
    campaign at this size.
- **Review process changes**
  - Keep the mutation-check-as-gate before authoring a guard. If a candidate guard cannot
    name a bug the others miss, record the cut in `R01` §Alternatives — that record is
    what stops the "add it back for coverage" cycle.
  - For any `com.github.copilot/` change, keep probe 1 (scratch marketplace) mandatory:
    it is the only oracle for rules `plugin validate` never runs.

## Artifacts to Preserve
- `__reports__/hook_namespace/00-architecture_v0.md` — `R01` contracts `C1`–`C5` and
  mutation log in §Alternatives
- `__reports__/hook_namespace/01-findings_loader_probes_v0.md` — four probe verdicts,
  the install-oracle table, and the steering questions for Phase B
- `__roadmap__/hook_namespace/` — the leaves, with the guard/probe reasoning embedded
- Commit bodies on `task/hook-namespace-mirror` (`0846514`) and `task/hook-namespace-docs`
  (`3d311db`, `8b03438`) — the mutation log and the doc rationale

## Open Questions
- Should the residual VS Code notice be silenced by Phase B's single-file layout
  (`c1`), or is the mirror-plus-notice state good enough after the release pins the
  new version? The blocker for `c1` is a Claude filename oracle for naming
  `./com.github.copilot/hooks/hooks.json` in `.claude-plugin/plugin.json`.
- Other v1 clients (Antigravity / Open Plugin, `.plugin/`-rooted) hold the same class of
  bug with their own constants. A per-namespace mirror set is cheap from here — worth it?
- Does the `Hooks (4)` count in `claude plugin details` (three events, four entries) ever
  confuse a user into thinking something is duplicated? If so, the docstring of
  `com.github.copilot/hooks/hooks.json` is the place to say why.
