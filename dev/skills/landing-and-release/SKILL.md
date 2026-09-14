---
name: landing-and-release
description: Git and release mechanics for colgrep-mcp — commit shape, rebase-then-merge integration, landing a PR, and cutting a `cz bump` release. Load this before authoring a commit, rebasing or merging a branch, opening or landing a pull request, resolving a merge conflict, running `cz check`/`cz bump`, editing CHANGELOG.md, or the moment `cz check` fails in this repository.
---

# Landing and release

The git and release mechanics of this repository, with the reason behind each
rule and a citation to the report that records it (`AGENTS.md` legend).

## Commit shape

Why: `cz check` enforces the schema in `server/pyproject.toml`
`[tool.commitizen.customize]`, and CI blocks a PR on it — a subject that looks
right by eye can still fail the regex. The type/bump table lives in
[`CONTRIBUTING.md`](../../../CONTRIBUTING.md#commit-convention); this skill does
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
committing (`KT-C`, `KT-B` §Pain Points). The merge commit is a commit too:
probe its subject with `cz check --message` before merging, and run
`cz check --rev-range main..HEAD` on the campaign branch before pushing —
checking each task branch's range is not enough, because the lead's own
merge subjects appear only in the campaign branch's range (`KT-D` §Pain
Points; `land_branch.sh` probes the subject). The general rebase-then-merge
method is the machine-level `writing-history` skill (`references/branches.md`
there); `scripts/land_branch.sh` runs the sequence for this repository's
gates.

Never bare `git stash`: the stash stack is shared across worktrees and
sessions, so a pop can take someone else's work. Prefer a throwaway commit;
if you must stash, `git stash push -u -m <tag>` and restore by SHA, never
`pop`.

`.gitignore` rules are written for the whole repository, not one package —
anchor them (`/server/build/`); a bare `build/` once hid
`__roadmap__/**/build/`. (`KT-B` §Pain Points.)

## Branches and worktree cleanup

`main` is always installable; one `task/<leaf>` branch per roadmap leaf,
branched from the campaign branch (which may itself be a harness-created
`claude/<name>` branch). Delete a branch and remove its worktree only after
the branch is merged (`git worktree remove`, `git branch -d`).
(`CONTRIBUTING.md` §Gates.)

## Landing a PR

Why: a PR and a local merge are two different integration paths, and mixing
them leaves GitHub's state wrong. See `references/landing-a-pr.md` for the
`gh pr create` → CI → `gh pr merge` sequence and why a local rebase-then-merge
pushed straight to `main` leaves the PR open on GitHub.

## Release

Why: `cz bump` mutates version-tracked files across the tree and pushes a
tag; running it anywhere but the one checkout that is actually `main` risks
bumping a version nobody merges, or a push a sandboxed permission classifier
silently blocks. Only from the main checkout (the first entry of
`git worktree list`, which is how `release.sh` finds it), never a scratch or
detached worktree:

```bash
cd server
uv run cz bump --changelog
uv run pytest   # uv run re-syncs the editable install
git push origin main v<x.y.z>   # the tag is lightweight; --follow-tags skips it
```

`cz bump` rewrites `pyproject.toml`, `uv.lock` (pre-bump hook), the four
version-tracked manifests, the `uvx colgrep-mcp==<version>` pin in the three
MCP manifests, and `CHANGELOG.md`, and writes its own
`release(colgrep-mcp): v<x.y.z>` commit — never author that commit or edit a
version by hand; a version-drift test failing means a file was hand-edited,
not that the environment is stale. (`OBS-H` Check 4, `CONTRIBUTING.md`
§Versioning and release.) `scripts/release.sh` enforces the checkout/branch
check and runs the recipe up to (never including) the push.

The tag push is the publish decision: `.github/workflows/publish.yml` fires
on it, refuses unless the tag is `v<pyproject version>` on a commit reachable
from `main`, builds, uploads to PyPI through trusted publishing (the `pypi`
GitHub environment; no token exists anywhere) and creates the GitHub release
from the tag's `CHANGELOG.md` section (pypi_publication R01 §C1–C4). If the
upload fails, nothing is burned: fix the cause (usually the trusted-publisher
registration on PyPI) and re-run the workflow from the Actions tab — never
re-tag. Until the upload succeeds the manifests pin a version PyPI does not
have, so the plugin is unlaunchable; that is the signal, not a bug to patch
around.

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
