---
name: campaign-lead
description: "Guides a lead through running a multi-agent campaign on this repository: deciding what to delegate and what to keep, writing the architecture report, building the roadmap, creating worktrees by hand, dispatching implementers, merging per level, running a read-only reviewer, and closing with a knowledge-transfer report. Load this whenever asked to lead, coordinate, plan, or dispatch work on this repo, before deciding a task is too small to delegate, to create a roadmap or worktrees for implementers, to review a merged roadmap level, or to close out a campaign cycle — even if the request never says 'skill'."
---

# Campaign Lead

Composes with the machine-level `writing-reports`, `managing-roadmaps` and `writing-history`
skills for mechanics; this skill is the order of operations and the rules this repository's
campaigns established, each cited to the retrospective that records it (`AGENTS.md` legend).

## The Default: Delegate First

`AGENTS.md` §Execution model states the contract; this section is how the lead applies it.
Every task that touches more than one file-disjoint leaf is a campaign, and every leaf goes to
an implementer unless the exception below applies. The lead's own context is the expensive
currency — it runs on the most capable tier and re-reads everything it touched on every later
turn — and wall-clock is the other: implementers run in parallel, so a level costs its slowest
leaf, while a dispatch carries a fixed overhead of the brief plus the implementer's cold read
of `AGENTS.md`, its leaf and the cited reports. Measured leaves ran 4–15 minutes each on the
cheaper tier (KT-C §Wins, KT-D §Wins); below that floor the lead is faster than its own brief.
Run implementers on the cheapest tier that clears the gates for leaves of that size; when one
leaf fails there, escalate that leaf, not the round. The harness instantiates the mechanism —
whatever it offers for parallel workers, in worktrees the lead created; with none, run the same
roadmap sequentially under the same discipline, and say so in the retrospective.

## Order of Operations

1. **Architecture report first** — contracts, file ownership per leaf, risks — under
   `__reports__/<topic>/`, via `writing-reports` (architecture type). Nothing gets dispatched
   against undocumented contracts.
2. **Roadmap next**, via `managing-roadmaps` (`dirtree-rdm init`/`add`). Leaves declare
   disjoint file ownership before anyone touches code.
3. **Commit specs and shared helpers before any dispatch.** A leaf that reaches for a
   not-yet-shared helper duplicates it, and two duplicates collide at merge (KT-B §Wins,
   KT-C §Wins: helpers before dispatch → zero conflicts).
4. **One worktree per leaf, created by hand**: `git worktree add <path> -b task/<leaf>
   <campaign-branch>`. Never let the harness create it — a harness convenience branches from
   whatever it considers the default base, not the campaign branch, and a whole dispatch round
   lands on the wrong base (KT-H §Pain Points, KT-B §Root Causes; the Claude Code instance of
   this trap is `stack-traps` `references/claude-code.md#agent-worktree`).
5. **Dispatch** with `references/dispatch-prompt.md`. Every prompt states "stop if the leaf
   file is missing from your worktree" — it turns a wrong-base worktree into a ~15-second
   no-op with zero stray commits instead of wasted work (KT-H §Wins).
6. **Merge level by level**, rebase-then-`--no-ff` (mechanics: `writing-history`). Re-run the
   gates yourself on every branch first — an implementer's reported test count is not evidence
   (KT-C §Pain Points).
7. **Reviewer after any level with more than two parallel branches** — see
   `references/reviewer-brief.md` — before merging onward.
8. **Close with a knowledge-transfer report** (`writing-reports`); its Next-cycle Changes seed
   the next campaign.

## Rules Specific to This Repository

- **Worktrees see only committed files.** Commit every spec and helper before dispatching, or
  the implementer's worktree simply will not have them.
- **File-disjoint ownership**, stated in the roadmap README's Gotchas, not assumed: each leaf
  edits only its own files and *reports* anything else it notices in its final message. This
  is what closes a campaign with zero merge conflicts (KT-H, KT-C §Wins).
- **Hard stop time**, stated in both the leaf and the dispatch prompt: the lead merges whatever
  is green at the stop (`consistency` roadmap README §Gotchas).
- **The exception to the default: do lead-sized leaves yourself.** Scaffolding, shared
  helpers, CI wiring, `AGENTS.md`, changelog fixes: delegating them costs a dispatch round-trip
  for work the lead finishes in minutes (`adapter_hygiene` took 4; KT-C, KT-H §Wins). The
  exception is per leaf, never per cycle — a cycle with no dispatch at all needs the
  retrospective to say why.
- **Refactor leaves need an explicit dump-and-diff oracle**, not "tests still pass": dump
  `Client.list_tools()`/`list_resources()`/`list_resource_templates()`/`list_prompts()` JSON on
  the base and the branch, diff empty. The MCP SDK ships docstrings verbatim, so even
  whitespace is client-visible (KT-C §Wins, OBS-C probe 1).
- **Regression tests must have failed once** — the rule and its reasoning are `maintainer-policy`
  §Regression tests earn their name; this skill only asks the lead to check the commit body says so.
- **Windows CI is the only portability oracle here** — read its verdict, don't skim it,
  whenever a leaf is the first to exercise a previously-untested path, and name that path in
  the PR body (KT-C §Pain Points, CI).
- **An implementer's turn ends with its report.** Anything it says it will do "in the
  background" after that never happens; make it block on the run (`gh run watch
  --exit-status`) or read the run yourself (`stack-traps` `references/claude-code.md#worker-turn`).
- **A drift test that relates two artefacts owned by different leaves is red until both land.**
  Order the roadmap so the *naming* side lands first (e.g. the `AGENTS.md` skill table before
  the skill leaves it names), even ahead of BFS order, or every merge in between is red on a
  test nobody owns (KT-D §Pain Points). Also: git does not track empty directories, so a
  scaffolded-but-empty directory never reaches a task worktree — a test that lists it must
  treat "absent" as "empty".
- **Merge commits are commits too.** Probe every merge subject with `cz check --message` and run
  `cz check --rev-range main..HEAD` on the campaign branch before pushing; per-task-branch ranges
  never contain the lead's own merges, and CI checks the whole range (KT-D §Pain Points).
- **Note the clock at the start; time-box the cycle.** A cycle here runs between one and four
  hours (KT-C, KT-H).

## What This Skill Does Not Restate

Report shapes and round-numbering: `writing-reports`. `dirtree-rdm` mechanics and its BNF
grammar: `managing-roadmaps` — `references/dirtree-gotchas.md` here only lists this
repository's specific traps against that grammar. Commit vocabulary, rebase-then-merge,
worktree teardown: `writing-history`.

## References

- `references/dispatch-prompt.md` — the dispatch-prompt template, with placeholders, and why
  each field exists.
- `references/dirtree-gotchas.md` — this repository's `dirtree-rdm` grammar traps.
- `references/reviewer-brief.md` — what a read-only reviewer's dispatch prompt must contain.
