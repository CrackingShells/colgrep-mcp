# Input-proportional waste: the hunt list

Hardware-first code (see `../SKILL.md` §Hardware-first code) means treating
work that scales with *input size* — not with how big the output happens to
look, or how rare a code path feels — as a defect. This is the checklist to
run whenever you touch a hot path (anything a `search`/`find_files`/`expand`
call reaches per request) or review someone else's change to one: does this
change add a step whose cost grows with the input, that the old code didn't
pay?

## Where this waste hides

Run this list against any function that runs once per request, once per hit,
or once per line of subprocess output:

- **File reads per unit of input** — reading a file (or a hit's source file)
  once per result instead of once per request, or reading it at all when the
  caller never asked for its contents.
- **Syscalls per unit of input** — anything that touches the filesystem or
  the OS once per item in a collection, rather than once for the collection.
- **Subprocess spawns** — spawning a process (or re-spawning one) more often
  than the request strictly requires.
- **Protocol round-trips** — a client notification (`roots/list`, a stderr
  line forwarded as a log message, a progress update) sent once per line of
  some other program's chatter instead of once per outcome that matters.
- **Environment copies** — copying the process environment on every spawn
  instead of once, or when nothing in it changed.
- **`Path.resolve()` per lock acquisition** — resolving a path every time a
  lock is taken, when the path doesn't change between acquisitions.
- **Per-request reads of static content** — reading a reference document (a
  guide, a template) from disk on every request instead of once and reusing
  it.

None of these matter for a single call in isolation — that's exactly the
trap. On a shared machine, every one of these runs again for every other
program's request too; "it's I/O-bound anyway" ignores that the same waste is
paid by everyone else at the same time. Remove it even when a single
instance looks negligible, and prefer making the I/O lazy — don't do it until
the caller's request actually needs the answer.

## Measured examples (`KT-C`)

These are the numbers that anchor the rule — not hypothetical savings, but
what the `consistency` campaign measured, median of 5, on a synthetic
corpus:

| Hot path | Before | After | What changed |
|:--|:--|:--|:--|
| `find_files` | 63.4 ms | 0.65 ms | stopped resolving and reading every hit's source file when the caller only wanted filenames |
| `expand` | 6.1 ms | 0.03 ms | removed a per-call read of static reference content that didn't depend on the request |
| per-spawn environment copy | — | — | stopped copying the full process environment on every `colgrep` subprocess spawn |
| per-lock `Path.resolve()` | — | — | stopped re-resolving a path on every lock acquisition when the path was already known |
| per-request guide read | — | — | stopped re-reading the agent guide document from disk on every request that referenced it |

A change that removes one of these is a `perf` commit only when it carries
this shape of before/after in the body — see `../SKILL.md` §`perf` vs
`refactor` for the measurement convention (median of 5, synthetic corpus in
the scratchpad, never the real `colgrep` against this repository, reviewer
reproduces within 2x).
