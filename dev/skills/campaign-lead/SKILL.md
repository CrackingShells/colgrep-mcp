---
name: campaign-lead
description: "Guides a lead through running a multi-agent campaign on this repository: writing the architecture report, building the roadmap, creating worktrees by hand, dispatching implementers, merging per level, running a read-only reviewer, and closing with a knowledge-transfer report. Load this whenever asked to lead, coordinate, plan, or dispatch work on this repo, to create a roadmap or worktrees for subagents, to review a merged roadmap level, or to close out a campaign cycle — even if the request never says 'skill'."
---

# Campaign Lead

Composes with the machine-level `writing-reports`, `managing-roadmaps` and `writing-history`
skills for mechanics; this skill is the order of operations and the rules three prior campaigns
(`colgrep_mcp`, `repo_health`, `consistency`) paid to learn.

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
   <campaign-branch>`. Never rely on the Agent tool's `isolation: worktree` for this — it
   branches from the primary checkout's `main`, not the campaign branch, and cost a full
   wasted dispatch round in `repo_health` (KT-H §Pain Points, KT-B §Root Causes, lead memory).
5. **Dispatch** with `references/dispatch-prompt.md`. Every prompt states "stop if the leaf
   file is missing from your worktree" — it turned the wrong-base failure above into a
   ~15-second no-op with zero stray commits instead of wasted work (KT-H §Wins).
6. **Merge level by level**, rebase-then-`--no-ff` (mechanics: `writing-history`). Re-run the
   gates yourself on every branch first — an implementer's reported count is not evidence; one
   branch reported 196 passing tests on a tree that actually collected 206 (KT-C §Pain Points).
7. **Reviewer after any level with more than two parallel branches** — see
   `references/reviewer-brief.md` — before merging onward.
8. **Close with a knowledge-transfer report** (`writing-reports`); its Next-cycle Changes seed
   the next campaign.

## Rules Specific to This Repository

- **Worktrees see only committed files.** Commit every spec and helper before dispatching, or
  the implementer's worktree simply will not have them.
- **File-disjoint ownership**, stated in the roadmap README's Gotchas, not assumed: each leaf
  edits only its own files and *reports* anything else it notices in its final message.
  `repo_health` and `consistency` both closed with zero merge conflicts this way (KT-H, KT-C
  §Wins).
- **Hard stop time**, stated in both the leaf and the dispatch prompt: the lead merges whatever
  is green at the stop (`consistency` roadmap README §Gotchas).
- **Do lead-sized leaves yourself.** Scaffolding, shared helpers, CI wiring, `AGENTS.md`,
  changelog fixes: delegating them costs a dispatch round-trip for work the lead finishes in
  minutes (KT-C, KT-H §Wins).
- **Refactor leaves need an explicit dump-and-diff oracle**, not "tests still pass": dump
  `Client.list_tools()`/`list_resources()`/`list_resource_templates()`/`list_prompts()` JSON on
  the base and the branch, diff empty. The MCP SDK ships docstrings verbatim, so even
  whitespace is client-visible (KT-C §Wins, OBS-C probe 1).
- **A regression test counts only once it has failed against the old code** — say so in the
  `fix` commit body (KT-C §Root Causes).
- **Windows CI is the only portability oracle here** — read its verdict, don't skim it,
  whenever a leaf is the first to exercise a previously-untested path, and name that path in
  the PR body (KT-C §Pain Points, CI).
- **A subagent that says it is "watching CI in the background" has already ended its turn.**
  Make it block on `gh run watch --exit-status`, or read the run yourself (lead memory).
- **Note the clock at the start; time-box the cycle.** The three prior cycles closed between
  50 minutes and 4 hours (KT-C, KT-H).

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
