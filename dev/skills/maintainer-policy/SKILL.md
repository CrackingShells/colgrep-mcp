---
name: maintainer-policy
description: States who colgrep-mcp is built for (agents, not humans, README.md excepted) and how ceremony, tests, docstrings, commit types, and performance claims get judged here. Load this before adding any scaffold, CI step, git hook, badge, template, or "best practice" to the repo; before reviewing or refactoring server code; before writing a docstring; before choosing between perf, refactor, and fix; or whenever asked "should we add X here", "wouldn't Y be more standard", or "this is I/O-bound so it doesn't matter".
---

# Maintainer policy: for agents, by agents

## Who this repository is for

Every consumer of this repository is an LLM agent inside a harness: end users
reach it through the MCP tools, maintainers reach it through this dev plugin.
Every design, engineering, and project-management decision is judged by one
question — does it make an agent's next command shorter, or make a failure
disappear? `README.md` is the sole exception: humans read it to decide
whether to install the tool or point their own agent at it (`MEM`, `KT-H`
§Executive Summary). When you are drafting anything else — a doc, a check, a
convention — picture the agent that will read it under time pressure, not a
human skimming for reassurance.

## The ceremony test

Generic GitHub ceremony — heavy CI, pre-commit hooks, badges, issue/PR
templates, bot integrations — is suspect by default. Before adding any of it,
name the agent command it shortens or the agent failure it removes; if you
can't, don't add it (`MEM`: "a lot of good code or github practice is
overengineering").

This is why enforcement here is **CI-only**: there is no blocking local git
hook, because an agent authoring a commit would pay a retry loop for no local
benefit. `cz check`, `pytest`, and `ruff check` gate the pull request, not the
commit (`CONTRIBUTING.md` §Checks, `KT-H`).

## Drift tests, not checklists

When two artefacts must agree — versions across manifests, the README tool
table against the real tools, changelog headings, `AGENTS.md` against the
skills actually shipped — write a test that fails the moment they disagree,
never a checklist item a future agent might skip (`KT-H` §Next-cycle
Changes). This repository's existing guards are `test_version.py`,
`test_manifests.py`, `test_changelog.py`, `test_readme.py`, and
`test_dev_plugin.py`. Before wiring up any new drift-checking tool or
generator, run its dry-run mode against the artefact that already exists and
diff the output — accepting an untested generator's config is how drift
guards themselves drift. See `references/drift-tests.md` for what each guard
pins today and the recipe for writing the next one.

## Docstrings cite evidence, not narration

A docstring says *why* the code is shaped this way and cites the report id
from the `AGENTS.md` legend that measured it — it never narrates which
roadmap step produced the line (`KT-C` §Executive Summary;
`consistency/00-architecture_v0.md` §C6). If you can't name the report, the
claim probably belongs in a commit body instead, not a docstring.

## Hardware-first code

Code here is written for the hardware before it is written for humans
(Casey Muratori school): "it's I/O-bound anyway" is not an argument, because
every wasted syscall, subprocess spawn, or round trip is paid again on every
program sharing the machine, not once. Hunt for work proportional to the
*input* rather than the *output* — file reads, subprocess spawns, protocol
round-trips, environment copies, a `Path.resolve()` per lock — and remove it
even when a single instance looks negligible; make I/O lazy where the answer
may not be needed at all. A change justified only by human readability, with
no effect on an agent's commands or failures, does not meet this bar (`MEM`,
`KT-C`). The measured examples that anchor this rule — `find_files` and
`expand` before/after, the per-spawn env copy, the per-lock resolve, the
per-request guide read — are in `references/input-proportional-waste.md`;
read it before arguing a hunt target is too small to matter.

## One idiom per concern

An agent should navigate this codebase by symbol, not by re-deriving the
pattern each time. Every concern below has exactly one entry point; a tool
that reimplements it instead of calling it is a bug, not a style choice
(`AGENTS.md` §Conventions, `KT-C`):

| Concern | Single idiom |
|:--|:--|
| Registering a tool | `server.register_tool(mcp, handler, *, title, annotations)` — dedents the docstring into the client-visible description |
| Resolving target paths | `paths.resolve_target_paths(ctx, paths)` — the only place the env → roots → cwd fallback lives |
| Translating adapter errors | `errors.translate_adapter_errors(path=...)` around every adapter call |
| Notifying a client | `logging_utils.safe_log` / `safe_progress` / `safe_notify_resource_updated` — never a bare `try/except Exception: pass` |
| Reaching the lifespan app outside a request | `server.get_app(ctx=None)` |
| Rendering a size-capped text block | the one budgeted renderer, not a bespoke truncation |

## `perf` vs `refactor`

A `perf` commit body carries a measured before/after: median of 5 runs,
against a synthetic corpus built in the scratchpad — never the real
`colgrep` pointed at this repository (see `stack-traps` for why) — with
enough detail that a reviewer can reproduce the number within 2x. No
numbers in the body means the commit is a `refactor`, full stop, regardless
of how confident the author is that it's faster (`CONTRIBUTING.md`, `KT-C`
§Wins, `OBS-C` probe 5).

## Regression tests earn their name

A test only counts as a regression test once it has actually failed against
the old code; if you wrote it after the fix and it never saw the bug, say so
in the `fix` commit body rather than implying it caught the regression
(`KT-C` §Root Causes).

## Client-visible behaviour is a leaf-level decision

A change to what an MCP client actually observes from a product tool
(argument semantics, output shape, notification counts) ships only when a
roadmap leaf says so explicitly and a test pins the new behaviour — never as
a side effect of a refactor or a performance fix (`consistency` roadmap
README §Gotchas).

## See also

- `references/input-proportional-waste.md` — the hunt list and measured
  before/after numbers behind the hardware-first section above.
- `references/drift-tests.md` — what each existing drift test pins, and the
  dry-run-then-diff recipe for writing a new one.
- `CONTRIBUTING.md` — the commit type/scope table this skill does not
  restate.
- The `stack-traps` skill — colgrep, MCP SDK, and plugin-loader specifics
  that inform some of these rules but aren't policy themselves.
