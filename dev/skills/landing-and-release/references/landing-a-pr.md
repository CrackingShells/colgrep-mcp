# Landing a PR

A GitHub PR and a local `git merge --no-ff` are two different ways to
integrate a branch, and they leave GitHub's own bookkeeping in different
states. Pick the PR path deliberately when the unit of work is going through
GitHub review, and follow it all the way through — mixing the two is what
causes the failure mode below. (`MEM`.)

## The sequence

1. `gh pr create` from the campaign or task branch, targeting the branch it
   was cut from (usually `main` or a `milestone/<campaign>` branch).
2. Wait for CI to go green on the PR before merging. The workflow
   (`.github/workflows/ci.yml`) runs, per job:
   - `ruff check`
   - `ruff format --check`
   - `pytest` on three OSes (this is the only portability oracle this
     repository has for Windows-specific path handling — read the verdict,
     don't skim it, whenever the PR is the first to exercise a previously
     untested path)
   - `cz check` over the PR's commit range
3. Land with:
   ```bash
   gh pr merge --merge --subject "<conventional subject> (PR #N)"
   ```
   `--merge` (not squash, not rebase) preserves the per-roadmap-step commits;
   the `(PR #N)` suffix on the subject is what makes the merge commit
   traceable back to the PR from `git log` alone.

## Why not a local rebase-then-merge here

A local `git merge --no-ff` followed by `git push origin <task>:main` does
land the code, but it rewrites the commit SHAs relative to what GitHub's PR
page is tracking. GitHub cannot recognize the pushed commits as "this PR,
merged" and leaves the PR showing **open** even though `main` now contains
the work. This has happened twice (PR #1, #2): the fix each time was to close
the PR by hand with a comment pointing at the merge commit SHA that actually
landed the change.

If a PR is open for a branch, land it through `gh pr merge`, not a local
merge and push. Reserve the local `land_branch.sh` path (see `SKILL.md`
§Integration) for branches that never went through a PR — most `task/<leaf>`
branches merging into a campaign branch inside one worktree tree, not into
`main`.
