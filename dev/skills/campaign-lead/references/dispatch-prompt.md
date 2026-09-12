# Dispatch-Prompt Template

Copy this template for every implementer you dispatch; fill the `<placeholders>` from the
leaf file and the roadmap README. Every field exists because a prior campaign paid for its
absence, not because the shape looked complete:

- **Worktree/branch, created from the campaign branch** and the **"stop if the leaf file is
  missing"** instruction both answer the same failure from two directions: `KT-H` records a
  worktree made from `main` instead of the campaign branch (the Agent tool's `isolation:
  worktree` does this by default) — the field names the correct base explicitly. When a
  worktree still ends up wrong-based, the "stop if missing" line is what turned that mistake
  into a ~15-second no-op with zero stray commits, instead of an implementer inventing work
  against a repo state the lead never intended (`KT-H` §Wins).
- **Read-first list and owned files, plus "commit specs before dispatching"** answer `KT-B`:
  specs that existed only in the lead's own working tree were invisible to a worktree that
  sees only committed files, and separately an unanchored `.gitignore` rule once hid roadmap
  leaf files from git entirely. Naming the exact files to read, and stating that the lead
  commits specs first, closes both holes.
- **Gate commands, spelled out verbatim, and the final-report shape asking for gate output
  lines** answer `KT-C`: an implementer's own claimed test count is not evidence (one branch
  reported 196 passing on a tree that actually collected 206), and a refactor with no named
  oracle has nothing for the lead — or a reviewer — to diff against. The template asks for the
  exact output line of each gate, not a paraphrase, precisely so the lead re-runs and compares
  rather than trusting a summary.
- **Commit rules and hard-stop time** keep the history and the time-box legible across many
  parallel branches the lead did not watch being written in real time.

---

```markdown
You are an implementer on the <repo-name> repository, working one roadmap leaf for a campaign
lead. Note the clock now (`date`); your hard stop is <HH:MM TZ> — at that time stop wherever
you are, commit what is green, and report.

**Worktree**: `<worktree-path>` (branch `<task/leaf-branch>`, created from the campaign branch
`<campaign-branch>`). Run every command from inside this worktree; never `cd` into another
checkout, never touch `main`, never push.
**Leaf file**: `<path/to/leaf.md>` in that worktree. If it does not exist there, stop
immediately and report "leaf file missing".
**Read first, in this order**: <the leaf file>; <AGENTS.md or equivalent surface file>;
<architecture report sections this leaf's fact inventory cites, by id>; <any prior-campaign
reports a bullet in that inventory cites, read on demand for detail>; <example files this leaf
should follow, if any>.
**You own only**: `<glob-1>`, `<glob-2>`, … . Anything else you believe needs changing: do not
edit it; describe it in your final report.
**Gates** (run from `<gate-cwd>` unless the leaf says otherwise): `<gate command 1>`,
`<gate command 2>`, … . Plus each step's Consistency Checks command from the leaf.
**Commit rules**: one commit per leaf step, subject exactly the step's `**Commit**` field,
body says WHY, ending with the line `Co-Authored-By: <attribution line>`. Validate each subject
with `<the repo's commit-message validator invocation>` before committing. Never `git stash`;
never edit versions by hand; never author a `release(...)` commit.
**Content rules**: <task-specific rules for this leaf — e.g. where facts must come from and
how each fact is cited, size caps, prohibited real-world side effects such as running a real
external tool or a live eval>.
**Final report** (your last message, plain text): the commits (hash + subject); the exact
output line of each gate; files touched outside your ownership (should be none) or changes you
recommend elsewhere; anything unfinished at the hard stop.
```
