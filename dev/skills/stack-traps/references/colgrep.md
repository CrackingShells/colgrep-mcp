# colgrep CLI traps

## Flag order turns a status check into a search {#flag-order}

**Symptom**: you ran something like `colgrep status --color never` (or any
subcommand followed by a global flag) meaning to check status quietly, and
instead colgrep ran a *search* — it printed ranked hits and/or reindexed the
current directory.

**Cause**: clap parses a bare word appearing before a subcommand as the
`[QUERY]` positional of the default `search` command. `colgrep --color never
status` is not "status with color off"; it is a search for the words
`--color never status` is never reached because `--color` is itself consumed
as part of the query token stream ahead of any subcommand. One agent indexed
its worktree this way. (`KT-B` §Pain Points; `server/colgrep_mcp/adapter.py`
docstring — the adapter itself always inserts `--color never` *after*
`argv[0]`, i.e. right after the subcommand, for exactly this reason.)

**What to do**: always put the subcommand first, global flags after it —
`colgrep status --color never`, `colgrep init --color never <path>`. If you
are calling colgrep by hand instead of through the adapter, copy that
ordering. Never rely on flag position "reads fine to a human" — clap's
parse is positional-first.

## Never run the e2e driver or `colgrep init` against this repo {#ancestor-folding}

**Symptom**: you're tempted to sanity-check a change by pointing
`server/tests/e2e/run_e2e.py` or a bare `colgrep init` at this repository or
one of its worktrees.

**Cause**: colgrep folds any path into the nearest already-indexed ancestor
project, and `colgrep clear` is project-wide. Running the real binary here
would fold this worktree's files into whatever ancestor project is already
indexed on the machine, and clearing to recover would wipe that ancestor's
index too. The e2e driver refuses this repository on purpose, precisely to
stop this. (`KT-B`, `R03`, `AGENTS.md` §Traps, `MEM`.)

**What to do**: run `uv run python tests/e2e/run_e2e.py --corpus <some other
repo>` against a real, separate corpus instead — the standing one for this
purpose lives at `~/Documents/explore/_colgrep_e2e_corpus/click`. Inside this
repository and its worktrees, exercise behaviour through `fake_colgrep.py`
and pytest, never the real binary. `COLGREP_MCP_REAL=1 uv run pytest` is the
one sanctioned opt-in for tests that need the real binary, and it does not
touch this repo's own tree.

## A hit's `line`/`end_line` looks wrong {#location}

**Symptom**: a search hit's reported `line`/`end_line` doesn't bound the unit
you can see in `unit.code`, or `end_line` lands suspiciously close to the
file's total line count.

**Cause**: colgrep 1.6.2 reports wrong `line`/`end_line` for roughly 60% of
sampled units, while `unit.code` itself is exact. The server does not trust
colgrep's line numbers as-is: `locate.py` re-derives `(line, end_line)` by
finding `code`'s first line verbatim in the file (disambiguating by
following-line match or nearest distance to the reported line), and sets
`location_verified` accordingly. (`R03`; `KT-B` §Open Questions — whether
`--no-pool` changes this is still an open re-probe, not yet answered.)

**What to do**: trust `line`/`end_line` only when `location_verified` is
true; when it is false, cite the file rather than a specific line range,
and don't assume the discrepancy is a bug in this server — it's colgrep's
own numbers being unreliable, worked around in `locate.py`, not a defect to
"fix" in the adapter.
