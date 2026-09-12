# This machine's traps

## A Bash command gets blocked even though it looks harmless {#shell-hook}

**Symptom**: a Bash command is refused, even one you only used inside a
heredoc to write a file, or one where the actual search tool wasn't even
invoked — just its name appeared in the command text.

**Cause**: this machine has a shell hook that blocks recursive corpus
searches — `grep -r`, `rg`, and equivalents — in any Bash command text,
heredocs included, on the theory that a corpus search should go through
colgrep's semantic search instead of brute-force recursive grep. The block
is on the text of the command, not just its runtime behaviour, so even a
`cat <<EOF` block that merely *mentions* one of those invocations as
example text gets blocked. (`KT-H` §Pain Points.)

**What to do**: when a file's content must literally contain one of those
command names (documentation, a skill file like this one, a script
comment), write it with the Write/Edit tool instead of a Bash heredoc — the
hook only inspects Bash command text. When a blocked command must actually
run (rare — plain non-recursive `grep`, or `grep` filtering another
command's output, is never blocked), prefix it with `COLGREP_BYPASS=1`.
Don't fight the hook by obfuscating the command; reach for the sanctioned
bypass or a different tool.

## Windows CI fails only on the fake colgrep binary or a setup step {#windows-ci}

**Symptom**: a CI run is green on ubuntu/macos and red on windows-latest,
and the failures look like they're in test infrastructure rather than in
the server's own logic — or a `setup-uv` step fails outright before tests
even run.

**Cause**: two distinct, already-diagnosed causes. (1) `setup-uv@v10` is
not a real moving tag — the action's tags stop at `v7` while releases reach
`v10.1.0`, so pin the exact release tag, not a bare major. (2) Windows'
`CreateProcess` cannot spawn a bare `.py` file the way POSIX can
(`WinError 193`), which fails everything downstream of the fake `colgrep`
binary; the fix is a `.cmd` wrapper around the fake, `win32`-only, not a
change to the server. In both historical runs, once these two were fixed,
the *server*'s own code needed only one guarded fix in `resources.py`
(a path-normalisation branch for drive-rooted paths) — the adapter, locks
and path resolution needed nothing, i.e. the server itself was already
portable; only the test harness was not. `uv run` re-syncs the editable
install before running, on every OS. (`CI`, `KT-H`.)

**What to do**: when Windows CI is the only red job, check whether it's a
`setup-uv` tag problem or a fake-binary spawn problem before assuming the
*server* has a portability bug. Windows CI is the only real portability
oracle here — read its verdict, don't skim it, the first time a leaf adds
the first test of a previously-untested path, and name that path in the PR
body.

## `git worktree add` fails because `main` is checked out elsewhere {#worktree-main}

**Symptom**: `git worktree add <path> -b <branch> main` (or any variant
naming `main`) fails because `main` is already checked out in another
worktree (the main checkout, typically
`~/Documents/explore/colgrep_mcp`).

**Cause**: git refuses to check out the same branch in two worktrees at
once. A reviewer or lead adding a read-only worktree for inspection hits
this whenever the main checkout already has `main` checked out, which it
normally does. (`OBS-C` §Scope Boundary.)

**What to do**: create the worktree detached at `main`'s current commit
instead of on the branch itself — `git worktree add --detach <dir>
$(git rev-parse main)` — and remove the worktree (`git worktree remove
<dir>`) once you're done with it. This is specifically the reviewer's
worktree trick, not a substitute for the lead's own
`git worktree add <path> -b task/<leaf> <campaign-branch>` for a leaf
implementer, which names a real branch on purpose.

## Auto-mode permission classifier blocks compound history rewrites {#classifier}

**Symptom**: a Bash command chaining `git checkout --detach … && git merge … && git cherry-pick …
&& git branch -f … && git push --force-with-lease` is refused with "Blocked by classifier",
as was `git push … HEAD:main` and `cz bump` from a detached `/private/tmp` worktree in the
consistency session (`MEM`).

**Cause**: the auto-mode classifier judges the whole command; anything that rewrites a
checked-out branch or force-pushes reads as destructive, and a scratch worktree under a temp
directory makes it worse.

**What to do**: never rewrite history in place. Create a fresh branch (`git worktree add -b
<new-branch> <dir> <good-commit>`), rebuild it with single-purpose commands (`git merge`,
`git cherry-pick <sha>…`, one per call), push it normally, open a new PR and close the old one
with a pointer — the `dev_plugin` campaign's PR #4 → #5 is the precedent. Do releases from the
main checkout (`landing-and-release`).