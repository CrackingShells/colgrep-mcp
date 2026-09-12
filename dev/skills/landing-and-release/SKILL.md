---
name: landing-and-release
description: Git and release mechanics for colgrep-mcp — commit shape, rebase-then-merge integration, landing a PR, and cutting a `cz bump` release. Load this before authoring a commit, rebasing or merging a branch, opening or landing a pull request, resolving a merge conflict, running `cz check`/`cz bump`, editing CHANGELOG.md, or the moment `cz check` fails in this repository.
---

# Landing and release

Three cycles of this repository hit the same detours at these mechanics. This
skill is the fourth cycle not repeating them.

## Commit shape

Why: `cz check` enforces the schema in `server/pyproject.toml`
`[tool.commitizen.customize]`, and CI blocks a PR on it — a subject that looks
right by eye can still fail the regex. The type/bump table lives in
[`CONTRIBUTING.md`](../../../CONTRIBUTING.md#allowed-types); this skill does
not repeat it.

Rules the schema enforces: `type(scope): description`, scope mandatory and
kebab-case, subject ≤ 100 chars (the whole line), lowercase after the colon,
no trailing period, imperative mood; a body says *why* the change exists; one
roadmap step is one commit and the step's `**Commit**` field is the subject
verbatim. (`OBS-H` Check 1.)

Before trusting a subject, probe the validator instead of guessing —
`scripts/probe_cz_check.sh` runs this from `server/`:

```bash
uv run cz check --message "<subject>"
```

against subjects that must be accepted and four that must not: a missing
scope (`feat: add x`), a trailing period (`chore(repo): tidy.`), a capitalised
type (`Feat(search): add x`), and an unknown type (`style(server): x`). Run
the probe whenever `[tool.commitizen]` changes.

## Integration: rebase, gate, merge

Why: a fast-forward or a squash loses the per-step commit history the
roadmap process relies on, and a merge without re-running the gates ships
whatever the task branch happened to have last. Rebase the task branch onto
its target, re-run the gates, then `git merge --no-ff -m "<message>"` into the
target — never `git merge -F -`, which does not read stdin inside an `&&`
chain. After any conflicting merge, search the tree for `<<<<<<<` before
committing; it has bitten this repository twice. (`KT-C`, `KT-B` §Pain
Points.) The general rebase-then-merge method is the machine-level
`writing-history` skill (`~/.claude/skills/writing-history/SKILL.md`,
`references/branches.md`); `scripts/land_branch.sh` runs the sequence for
this repository's gates.

Never bare `git stash`: the stash stack is shared across worktrees and
sessions, so a pop can take someone else's work. Prefer a throwaway commit;
if you must stash, `git stash push -u -m <tag>` and restore by SHA, never
`pop`. (Environment rule, `MEM`.)

`.gitignore` rules are written for the whole repository, not one package —
anchor them (`/server/build/`); a bare `build/` once hid
`__roadmap__/**/build/`. (`KT-B` §Pain Points.)

## Branches and worktree cleanup

`main` is always installable; one `task/<leaf>` branch per roadmap leaf,
branched from the campaign branch (which may itself be the session's
`claude/<name>` branch). Delete a branch and remove its worktree only after
the branch is merged (`git worktree remove`, `git branch -d`).
(`CONTRIBUTING.md` §Branching.)

## Landing a PR

Why: a PR and a local merge are two different integration paths, and mixing
them leaves GitHub's state wrong. See `references/landing-a-pr.md` for the
`gh pr create` → CI → `gh pr merge` sequence and why a local rebase-then-merge
pushed straight to `main` leaves the PR open on GitHub.

## Release

Why: `cz bump` mutates version-tracked files across the tree and pushes a
tag; running it anywhere but the one checkout that is actually `main` risks
bumping a version nobody merges, or a push a sandboxed permission classifier
silently blocks. Only from the main checkout
(`~/Documents/explore/colgrep_mcp`), never a scratch or detached worktree:

```bash
cd server
uv run cz bump --changelog
uv run pytest   # uv run re-syncs the editable install
git push origin main v<x.y.z>   # the tag is lightweight; --follow-tags skips it
```

`cz bump` rewrites `pyproject.toml`, `uv.lock` (pre-bump hook), the four
version-tracked manifests, and `CHANGELOG.md`, and writes its own
`release(colgrep-mcp): v<x.y.z>` commit — never author that commit or edit a
version by hand; a version-drift test failing means a file was hand-edited,
not that the environment is stale. (`AGENTS.md` §Traps, `OBS-H` Check 4,
`CONTRIBUTING.md`, `MEM`.) `scripts/release.sh` enforces the checkout/branch
check and runs the recipe up to (never including) the push.

Commitizen has sharp edges around this recipe: see
`references/commitizen-gotchas.md` before treating `cz bump --dry-run` or a
`!` in a subject as more informative than they are.

## Scripts

- `scripts/probe_cz_check.sh` — the commit-shape validator probe above.
- `scripts/land_branch.sh <task-branch> <target-branch> <merge-message>` —
  rebase, gates, `--no-ff` merge, conflict-marker search; never pushes.
- `scripts/release.sh [--run]` — refuses outside the main checkout or off
  `main`; without `--run` prints the dry-run bump; never pushes.

All three: `set -euo pipefail`, `--help`, echo each step before running it,
stop at the first red gate.
