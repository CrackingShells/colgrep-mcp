# Reviewer Brief

Dispatch a read-only reviewer whenever a roadmap level merges more than two parallel branches,
or before closing a risky refactor leaf. The reviewer's job is to find what the test suite
cannot prove — schema drift, leftover idioms, unreproduced perf claims — not to re-derive
whether the tests pass (that is a gate, run it yourself first).

A reviewer's dispatch prompt must contain all five of the following.

1. **The architecture contract.** Point it at the campaign's own contract sections (this
   campaign's `C1`–`C8`, or the equivalent for another campaign) so it checks the merged code
   against stated invariants, not against its own guess at what "correct" means.
2. **The list of intentional client-visible deltas** (e.g. the campaign's oracle/delta table).
   Without this the reviewer either re-reports an approved behavior change as a bug, or cannot
   confirm it is the *only* delta — both failures waste the lead's time triaging noise.
3. **Instructions to probe every validator with deliberately invalid input, not just read
   valid history.** `cz check --rev-range` only ever sees commits that already passed; feed it
   a bad `--message` instead. Give a drift test a deliberately broken fixture. Both commitizen
   defects found in this repository's history were caught this way — never by reading valid
   history (KT-H §Review process changes, OBS-H).
4. **The dump-and-diff oracle for anything client-visible**: dump
   `Client.list_tools()`/`list_resources()`/`list_resource_templates()`/`list_prompts()` JSON
   on the base and the branch, diff must be empty (KT-C §Wins, OBS-C probe 1).
5. **The report shape**: an `observation` report (`writing-reports`) with a findings table —
   id, file:line, severity (bug/risk/consolidation), confidence, proposed fix — that the lead
   routes to fixes or folds into the retrospective (KT-H §Review process changes, OBS-H).

## Scope boundary

The reviewer is read-only: it edits nothing but its own report file. If it needs its own
worktree checked out from `main` while `main` is checked out elsewhere, see the `stack-traps`
skill for the detach-and-remove pattern — don't restate it here.

## Size validator probes to the margin

When the brief says "break the guard and confirm the test fails", state the delta relative to the
artefact's *current* margin, not as a fixed number: "add 10 lines" to an 89-line file under a
130-line cap never crosses the cap, and the probe passes without exercising anything (dev_plugin
review F2). Ask for "enough to exceed the cap" and have the reviewer report the size used.
