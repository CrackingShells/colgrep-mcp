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

## Never run the e2e driver here; check for an indexed ancestor before the first `search` {#ancestor-folding}

**Symptom**: you're tempted to sanity-check a change by pointing
`server/tests/e2e/run_e2e.py` at this repository or one of its worktrees —
or, the opposite over-correction, you refuse to use the plugin's own
`search` tool in a worktree at all and fall back to reading whole files.

**Cause**: colgrep folds any path into the nearest *already-indexed
ancestor* project, and `colgrep clear` is project-wide. A worktree with an
indexed ancestor would have its files folded into that ancestor's index,
and clearing to recover would wipe the ancestor too. The e2e driver refuses
this repository on purpose because it runs `index_build`/`index_clear`
against its corpus. A path with **no** indexed ancestor has no such
problem: the first `search` creates a fresh project rooted at that path
(`index_status` afterwards reports `project == requested_path`), and the
plugin's `WorktreeRemove` hook reaps that index when the worktree goes.
That is exactly why the maintainer's worktrees live outside the repository
tree (`~/…/claude-worktrees/…`, not `<repo>/.claude/worktrees`, which
colgrep ignores): each gets its own index. Verified 2026-09-13 on the
`harness_wiring` worktree: no ancestor among 164 indexed projects, first
`search` indexed it in 13 s, `project` equalled the worktree path. (`KT-B`,
`R03`, harness_wiring R01, `MEM`.)

**What to do**: before the first `search` in a worktree, call
`index_status` on it. `indexed: false` means the search will create the
worktree's own project — go ahead. `indexed: true` with `project` different
from `requested_path` means you are folded into an ancestor: search from
that ancestor knowingly, and never `index_clear` from the worktree path
(the tool refuses with `PROJECT_ROOT_MISMATCH` anyway, R05 D3). Never run
`run_e2e.py` against this repository; use `uv run python
tests/e2e/run_e2e.py --corpus <some other repo>` (the standing corpus is
`~/colgrep-e2e-corpus/click`). Tests exercise behaviour through
`fake_colgrep.py`; `COLGREP_MCP_REAL=1 uv run pytest` is the one opt-in for
the real binary and does not touch this tree.

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
