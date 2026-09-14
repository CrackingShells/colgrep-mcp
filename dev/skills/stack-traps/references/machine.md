# Machine and harness traps

## A Bash command gets blocked even though it looks harmless {#shell-hook}

**Symptom**: a Bash command is refused with "Shell corpus search … is
disabled by the colgrep-mcp plugin", even one you only used inside a
heredoc to write a file, or one where the actual search tool wasn't even
invoked — just its name appeared in the command text.

**Cause**: the product plugin ships a `PreToolUse` hook
(`hooks/colgrep_policy.py`, harness_wiring R01 §C5) that denies recursive
corpus searches — `grep -r`, `rg`, `find -exec grep`, `xargs grep` — in any
Bash command text whose targets are a source corpus, on the theory that a
corpus search should go through the `search` tool instead of brute-force
recursive grep. The block is on the text of the command, not just its
runtime behaviour, so even a `cat <<EOF` block that merely *mentions* one
of those invocations as example text gets denied. The flag match requires
whitespace before the dash, so `-r` inside a hyphenated word such as
`-patterns` is not read as a flag and a single-file grep passes.
(`KT-H` §Pain Points; harness_wiring R01.)

**What to do**: when a file's content must literally contain one of those
command names (documentation, a skill file like this one, a script
comment), write it with the Write/Edit tool instead of a Bash heredoc — the
hook only inspects Bash command text. When a blocked command must actually
run (rare — plain non-recursive `grep`, or `grep` filtering another
command's output, is never blocked), prefix it with `COLGREP_BYPASS=1`.
Don't fight the hook by obfuscating the command; reach for the sanctioned
bypass or a different tool. To see exactly what the hook would decide, feed
it the harness's JSON by hand — `server/tests/test_hooks.py` shows the
shape.

## Windows CI fails only on the fake colgrep binary or a setup step {#windows-ci}

**Symptom**: a CI run is green on ubuntu/macos and red on windows-latest,
and the failures look like they're in test infrastructure rather than in
the server's own logic — or a `setup-uv` step fails outright before tests
even run.

**Cause**: two distinct causes. (1) `setup-uv@v10` is not a real moving
tag — the action's tags stop at `v7` while releases reach `v10.1.0`, so pin
the exact release tag, not a bare major. (2) Windows' `CreateProcess`
cannot spawn a bare `.py` file the way POSIX can (`WinError 193`), which
fails everything downstream of the fake `colgrep` binary; the fix is a
`.cmd` wrapper around the fake, `win32`-only, not a change to the server.
The server itself is portable — the adapter, locks and path resolution
need nothing Windows-specific beyond the drive-rooted path branch in
`resources.py` — so a red Windows job is almost always the test harness.
`uv run` re-syncs the editable install before running, on every OS.
(`CI`, `KT-H`.)

**What to do**: when Windows CI is the only red job, check whether it's a
`setup-uv` tag problem or a fake-binary spawn problem before assuming the
*server* has a portability bug. Windows CI is the only real portability
oracle here — read its verdict, don't skim it, the first time a leaf adds
the first test of a previously-untested path, and name that path in the PR
body.

## `git worktree add` fails because `main` is checked out elsewhere {#worktree-main}

**Symptom**: `git worktree add <path> -b <branch> main` (or any variant
naming `main`) fails because `main` is already checked out in another
worktree (the main checkout).

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
&& git branch -f … && git push --force-with-lease` is refused with "Blocked by classifier";
so is `git push … HEAD:main` or `cz bump` run from a detached worktree under a temp directory.

**Cause**: the auto-mode classifier judges the whole command; anything that rewrites a
checked-out branch or force-pushes reads as destructive, and a scratch worktree under a temp
directory makes it worse.

**What to do**: never rewrite history in place. Create a fresh branch (`git worktree add -b
<new-branch> <dir> <good-commit>`), rebuild it with single-purpose commands (`git merge`,
`git cherry-pick <sha>…`, one per call), push it normally, open a new PR and close the old one
with a pointer. Do releases from the main checkout (`landing-and-release`).

## `uv run` says "Failed to spawn: `cz`" although `uv sync` audits every package {#stale-venv}

**Symptom**: in a checkout, `uv run cz …` (or `pytest`, `ruff`) fails with
`Failed to spawn: \`cz\`` / `No such file or directory`, while `uv sync`
reports every package present and `.venv/bin/cz` exists.

**Cause**: the venv was created before the repository moved on disk. Every
launcher in `.venv/bin/` has an absolute shebang
(`#!/old/path/server/.venv/bin/python3`), `uv sync` audits installed
packages rather than shebangs, so nothing rewrites them; the kernel's "bad
interpreter" surfaces as uv's "Failed to spawn".

**What to do**: `rm -rf server/.venv && uv sync --directory server`. Never
hand-edit the shebangs and never "fix" it by pointing the release at another
checkout — `release.sh` must still run from the main one.
