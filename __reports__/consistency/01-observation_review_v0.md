# Read-Only Review of the Consistency Pass — Observation (v0)

---
type: observation
topic: consistency
spotted-during: read-only reviewer pass over the merged depth-0 result (roadmap leaf `__roadmap__/consistency/integrate/review.md`), tracing the seven probes it names against R01 (`00-architecture_v0.md` §Contracts C1–C6) and R05/R02 (`__reports__/colgrep_mcp/02-architecture_v1.md`, `02-observation_code_review_v0.md`)
date: 2026-09-12
domain: code
confidence: confirmed
urgency: medium
deferred-because: this is a read-only review pass (roadmap leaf explicitly says "Reviewer (read-only)"); the one confirmed risk below is routed to the lead for `task/docstrings`/knowledge-transfer triage, not fixed here
---

## What Was Noticed

All four depth-0 leaves (`search_tools`, `index_tools`, `context_free_handlers`,
`adapter_hygiene`) hold up under trace: every leftover-idiom pattern the leaf
names is confined to its contractually-owning module, the F1/F2 cancellation
fixes and F6/F10 concurrency fixes from the 0.1.0 review are intact and test-
covered, `Client.list_tools()`/`list_resources()`/`list_resource_templates()`/
`list_prompts()` diff empty against `main` except for the one documented
whitespace-only dedent, `find_files`'s `files` output is byte-identical
before/after, both perf claims reproduce well within 2×, and
`resolve_target_paths` calls `roots/list` exactly as many times as the
contract requires (0 with `COLGREP_MCP_ROOT` set, 1 without it and no
explicit `paths`).

One genuine, empirically confirmed **risk** surfaced outside the seven named
probes, from reasoning through probe (3)'s "what if two lifespans overlap"
question rather than stopping at "tests only run one `Client(build())` at a
time": `server._app` is a single module-global written and cleared by
whichever `lifespan()` invocation's `__aenter__`/`finally` runs, so two
`Client(build())` sessions held open *concurrently* in one process (not the
sequential case the existing tests and R01 Risk #2 already cover) corrupt
each other — the first session to exit clears `_app` out from under the
second, which is still running, and every resource/prompt/completion handler
with no request `Context` (`colgrep://settings`, `colgrep://indexes`,
`colgrep://guide`, `colgrep://errors`, `complete_path`) then raises
`RuntimeError: colgrep-mcp server is not running` — a wrong and misleading
error for a session that is very much still running. Reproduced empirically
below (Evidence, OV1).

No dead code, no unused helper, no genuinely-unawaited `async def`, and no
stale comment were found in the ten files this campaign's depth-0 leaves
touched (two static-analysis false positives — `lifespan` and
`translate_adapter_errors` — are flagged and dismissed under Traced, No
Issue). The AGENTS.md report-id legend that R01 §C6 calls for is still
missing, and several docstrings still cite bare `F7`/`F11`/`F13`/`F14`
without one — **not reported as a finding**: `git log task/docstrings`
shows that work already in progress on a sibling branch not yet merged into
this one (see Context).

### Findings Table

| id | file:line | severity | confidence | proposed fix |
|:--|:--|:--|:--|:--|
| OV1 | `server.py:47,52-59,65-76` | risk | confirmed | Replace the single module-global `_app: AppContext \| None` with a `contextvars.ContextVar[AppContext \| None]` set inside `lifespan` (`token = _app_var.set(ctx); try: yield ctx; finally: _app_var.reset(token)`). Each session's async task tree then sees only its own lifespan's context, so a second concurrent session's exit can no longer clear the first session's handle out from under it. `get_app()`'s no-`ctx` branch becomes `_app_var.get(None)`. |

## Context

Primary task: read-only trace of the merged four depth-0 leaves
(`search_tools`, `index_tools`, `context_free_handlers`, `adapter_hygiene`)
against the seven probes `__roadmap__/consistency/integrate/review.md` names,
cross-checked against R01's contracts C1–C6 and the F1/F2/F6/F10 fixes R02
(0.1.0 review) had flagged. `cd server && uv run pytest` passes (all-dots
run, no `F`/`E`, exit 0 — the venv's custom terminal reporter does not print
a final summary line, but the dot stream and exit code are unambiguous);
`uv run ruff check` reports "All checks passed!".

Not reported as findings, because they are already someone else's
in-progress work, not a gap this pass introduced:
- **AGENTS.md report-id legend (R01 §C6)** and the docstring cleanup
  (stripping roadmap-step narration, keeping only *why*) are the explicit
  job of `integrate/docstrings.md`. `git log task/docstrings --oneline -5`
  (read-only, no checkout) shows two commits already on that branch —
  `docs(docs): add the report-id legend and the one-idiom-per-concern rules
  to AGENTS.md` and `docs(server): strip roadmap narration from docstrings
  and keep only the why` — not yet merged into `task/review`. The bare
  `F7`/`F11`/`F13`/`F14`/`R01`/`R05` citations this review's own probe (8)
  turned up in `adapter.py`, `tools_search.py` and `paths.py` are exactly
  what those two commits already address.

Out of scope by the leaf's own instruction: no source file under
`server/colgrep_mcp/` or `server/tests/` was modified; the two worktrees
this review created against `main`'s commit (never against `main`'s branch
name directly, since it is checked out elsewhere) were both `git worktree
remove`d after use.

## Location Map

- `server/colgrep_mcp/server.py:43-76` — module-global `_app`, `lifespan`, `get_app` → OV1
- `server/colgrep_mcp/adapter.py:218-240` — `_run`'s `except BaseException` kill+reap → F1 (0.1.0 review), confirmed still intact
- `server/colgrep_mcp/tools_index.py:219-247` — `index_build`'s `finally: task.cancel(); await task` before the lock releases → F2 (0.1.0 review), confirmed still intact
- `server/colgrep_mcp/tools_search.py:354-359` — `distinct_paths`/`AsyncExitStack` locking every resolved path → F6 (0.1.0 review), confirmed still intact, and test-covered (`test_search_locks_every_resolved_path_not_only_the_first`)
- `server/colgrep_mcp/prompts.py:37-62` — `_stats_lock` guarding `_cached_project_paths` → F10 (0.1.0 review), confirmed still intact
- `server/colgrep_mcp/paths.py:83-103` — `_roots_can_matter`/`resolve_target_paths` → probe (6), confirmed correct call counts
- `server/colgrep_mcp/tools_search.py:305-320,367-369` — `_do_search(..., locate: bool)` → probe (4)/(5) find_files equivalence and perf
- `server/colgrep_mcp/tools_search.py:590-606` — `_read_span` → probe (5) expand perf
- `server/colgrep_mcp/errors.py`, `resources.py:45-49` — `from_adapter_error(` outside `errors.py` is the one documented exception (`_map_adapter_error`) → probe (2), confirmed compliant
- `server/colgrep_mcp/config.py:25` — `os.environ` outside `adapter.py` is `Settings.from_env`'s own module → probe (2), confirmed compliant
- Scratchpad probes (throwaway, never committed, never against a real `colgrep` or this repository): `.../scratchpad/dump_list_tools.py`, `probe_app_and_roots.py`, `probe_overlapping_lifespans.py`, `probe_perf.py`, `dump_find_files.py`

## Evidence

### Schema invariance (probe 1)

Dumped `list_tools()`/`list_resources()`/`list_resource_templates()`/
`list_prompts()` (full `model_dump(mode="json")`, sorted) from a detached
worktree at `main`'s commit and from this branch, both against
`tests/fake_colgrep.py` via `COLGREP_MCP_BINARY`. Raw `diff` shows exactly
three changed lines, all `description` fields, all for `search`/
`find_files`/`expand`:

```
155c155  (expand)      <8-space-indented triple-quoted docstring, trailing spaces>
195c195  (find_files)  <same>
454c454  (search)       <same>
```

A second pass normalized every `description` string's whitespace
(`re.sub(r'\s+', ' ', d).strip()`) and recursively compared every other
field (name, title, annotations, inputSchema, every resource/template/prompt
field) — zero `WORD DIFF` / `VALUE DIFF` lines printed. This matches the
task's documented, intentional delta exactly and nothing more.

### Leftover idioms (probe 2)

```
COLGREP_BYPASS=1 grep -rn '<pattern>' server/colgrep_mcp
```
for each of the eight patterns named in the leaf:

| pattern | occurrences outside the owning module | verdict |
|:--|:--|:--|
| `from_adapter_error(` | `resources.py:49` | allowed — the documented `_map_adapter_error` exception (R01 §C3) |
| `except Exception:` then `pass` | none | clean — the three notification guards in `logging_utils.py` all `log.debug(...)`, none are bare `pass` |
| `Settings.from_env` | `__main__.py:28` | allowed — the documented fail-fast parse (R01 §C1) |
| `ToolAnnotations(read_only_hint=True` | none outside `server.py` | clean |
| `_standalone_adapter` | none, anywhere | clean — eliminated as C1 intended |
| `resolve_paths(` | only within `paths.py` (definition + one internal call) | clean |
| `mcp.tool(` | none, anywhere | clean — every tool goes through `register_tool`/`server.tool` |
| `os.environ` | `config.py:25` | allowed — `Settings.from_env`'s own module |

### App handle (probe 3)

```
=== Probe 3: app handle ===
OK: RuntimeError outside lifespan: colgrep-mcp server is not running: no lifespan context available
session 0: _app cleared after exit? True
session 1: _app cleared after exit? True
adapter ids across two sequential sessions: [4470367696, 4459490112] distinct? True
```
`get_app()` outside any running server raises `RuntimeError` as required;
two *sequential* `Client(build())` sessions each get a fresh `ColgrepAdapter`
(`id()` differs) and `_app` is `None` again after each exits.

**OV1 — overlapping lifespans** (the "reason, do not fix" half of probe 3,
turned into a direct empirical check): two sessions held open
*concurrently* via `asyncio.gather`, one exiting after 0.1s and one after
0.5s, both against the one `mcp` module-singleton `build()` returns:

```
{'A_short': ('ok', True),
 'B_long': ('error', "MCPError(-32603, 'Error reading resource colgrep://settings', "
                      "{'uri': 'colgrep://settings'})")}
```

`B_long`'s `colgrep://settings` read — issued at t=0.5s, while `B_long`'s
own session is still fully alive — fails with the exact `RuntimeError:
colgrep-mcp server is not running: no lifespan context available` `get_app`
raises when `_app is None`, because `A_short`'s `finally: _app = None` ran
at t=0.1s and stayed cleared. Every ordinary tool call is unaffected (they
all thread `ctx` through to `ctx.request_context.lifespan_context`, which is
per-session); only the four `ctx`-less resources and the completion
callback are exposed. This is a real gap, not a hypothetical: `MCPServer`
supports transports other than stdio (the docstring conditions this
module-global's existence on "the SDK gives static resources no `ctx`", not
on "only one client connects per process"), and the existing test suite's
"one `Client(build())` per test" habit (R01 Risk #2's stated mitigation)
would not catch two tests or two client connections overlapping in the same
process.

### `find_files` equivalence (probe 4)

`find_files({"query": "config parsing", "limit": 10})`'s `structured_content["files"]`
dumped from the same two worktrees (`main`'s commit, this branch), both
against `tests/fake_colgrep.py`: `diff main_files.json branch_files.json`
exit code `0` — byte-identical.

### Perf claims (probe 5)

Re-ran both `perf(search)` (067bac5) synthetic benchmarks in-process (never
against a real `colgrep`), median of 5 runs each, against the two helpers
the commit body names (`_fill_file_cache`+`hit_from_raw` for the
locate=True/False split, `_read_span` vs. `read_text`+`splitlines` for
`expand`):

| benchmark | claimed before → after (speedup) | reproduced before → after (speedup) | within 2×? |
|:--|:--|:--|:--|
| find_files (300 hits / 100 files × 5000 lines) | 63.43ms → 0.65ms (~97×) | 53.21ms → 0.70ms (~76×) | yes |
| expand (lines 10–60 of a 200,000-line file) | 6.105ms → 0.031ms (~195×) | 3.647ms → 0.032ms (~115×) | yes |

Also re-checked `perf(server)`'s (7063479) description-byte claim from the
same `list_tools()` dumps used for probe 1: claimed 1510→1395 bytes across 8
tools' descriptions; measured 1516→1401 (the small constant offset is
almost certainly this probe's own JSON dump summing `description` fields
directly rather than the exact wire-serialized `ListToolsResult`, not a
discrepancy in the change itself) — within 2×, same direction, same order
of magnitude.

### `resolve_target_paths` roots calls (probe 6)

```
root set, paths=None -> list_roots calls: 0 (expect 0)
root unset, paths=None -> list_roots calls: 1 (expect 1)
```
Monkeypatched `paths.get_settings` to return a `Settings` with/without
`root` set, and a fake `ctx.session.list_roots()` that counts calls; matches
R01 §C2 exactly.

### Cancellation paths (probe 7)

Read (not re-executed — the 0.1.0 review's own probes already exercised
these against `fake_colgrep.py`; re-reading confirms the code shape survived
the refactor unchanged in substance):

- `adapter.py:218-240`: `_run`'s `try/except TimeoutError/except BaseException` both `proc.kill(); await proc.wait()` before re-raising — the `except BaseException` arm (F1's fix) is present with a comment explaining exactly why it must catch `CancelledError` too.
- `tools_index.py:219-247`: `index_build`'s `try/finally` around the heartbeat loop does `task.cancel()` + `contextlib.suppress(asyncio.CancelledError): await task` before the `async with project_lock` block's `__aexit__` runs — F2's fix, present, with the same reasoning comment as the 0.1.0 review's proposed fix.

### Probe 8 — dead code, stale comments, unused helpers, unawaited `async def`

An AST sweep (`ast.walk` over every `AsyncFunctionDef`, flagging any with no
`Await`/`AsyncFor`/`AsyncWith` node in its body) over every `.py` file in
`server/colgrep_mcp/` found two hits, both false positives:

- `server.py:51 lifespan` — an `@asynccontextmanager` generator whose whole
  body is `settings = ...; adapter = ...; _app = ...; try: yield _app;
  finally: _app = None` — it must be `async def` to be usable as `async
  with`, not because it awaits anything itself.
- `errors.py:125 translate_adapter_errors` — same shape, an
  `@asynccontextmanager` wrapping `try: yield; except ColgrepError as exc:
  raise ...`.

No unused helper, no dead branch, and no comment referring to code that no
longer exists were found in the ten changed files.

## Traced, No Issue

- `locks.py`'s `_lock_for` now keys on `str(path)` instead of
  `str(path.resolve())` (a perf change this campaign's `adapter_hygiene`
  leaf made) — verified every caller (`_do_search`'s `distinct_paths`,
  `index_build`/`index_clear` via `_resolve_one` → `resolve_target_paths`)
  already passes a path that went through `paths.resolve_paths`'s own
  `.resolve()`, so the lock key is still canonical; no double-`.resolve()`
  cost was silently reintroduced and no lock-key mismatch was introduced.
- `locks.py`'s `_locks: dict[str, asyncio.Lock]` still grows unboundedly for
  the life of the process (one entry per distinct project ever touched,
  never evicted) — pre-existing (this campaign only changed the key
  computation, not the eviction policy, and R01 does not name this as one
  of C1–C6), not a new gap this pass introduced; left for a future cycle.
- `resources.py`/`prompts.py` sharing the lifespan's one adapter via
  `get_adapter()`/`get_adapter(ctx)` (R01 §C1): every call site checked
  (`settings_resource`, `indexes_resource`, `status_resource`,
  `_cached_project_paths`) uses the no-`ctx` or `ctx` form correctly for
  its handler shape; no call site was left calling a since-removed
  `_standalone_adapter`.
- `index_status`'s `try: stats = await adapter.stats() except ColgrepError:
  stats = []` is a real fallback with a body, not the banned
  `except Exception: pass` idiom (it also correctly narrows to
  `ColgrepError`, not the bare `Exception` the probe pattern looks for).
- `index_clear`'s two `except Exception:` blocks (capability-check failure,
  elicitation-call failure) both have `# noqa: BLE001` with a one-line
  justification and a real, differentiated body (F8's fix from the 0.1.0
  review, confirmed still intact: a technical elicitation failure surfaces
  `CONFIRMATION_REQUIRED` with its own detail, not silently collapsed into
  "declined").
- `cz check --rev-range main..HEAD` was not re-run for the four already-
  merged leaves' history (out of scope: this leaf only checks its own
  commit range once written).

## Re-observation Steps

All scratchpad scripts are throwaway (never committed), run against
`tests/fake_colgrep.py` only, never a real `colgrep`, never this repository
as a search target.

```bash
cd server

# Probe 1 — schema invariance (run once per worktree: this branch, and a
# detached worktree at `git rev-parse main`'s commit — `main` the branch
# name is checked out elsewhere, so `git worktree add --detach <dir> $(git rev-parse main)`)
chmod +x tests/fake_colgrep.py
uv run python <scratchpad>/dump_list_tools.py > branch_list.json
# (repeat from the main-commit worktree's server/ dir) > main_list.json
diff main_list.json branch_list.json   # 3 lines, description-only, whitespace-only

# Probe 2 — leftover idioms
for p in 'from_adapter_error(' 'Settings.from_env' 'ToolAnnotations(read_only_hint=True' \
         '_standalone_adapter' 'resolve_paths(' 'mcp.tool(' 'os.environ'; do
  COLGREP_BYPASS=1 grep -rn "$p" colgrep_mcp
done

# Probe 3 / OV1 — app handle + overlapping lifespans
uv run python <scratchpad>/probe_app_and_roots.py
uv run python <scratchpad>/probe_overlapping_lifespans.py

# Probe 4 — find_files equivalence
uv run python <scratchpad>/dump_find_files.py > branch_files.json
# (repeat from the main-commit worktree) > main_files.json
diff main_files.json branch_files.json   # empty

# Probe 5 — perf reproduction
uv run python <scratchpad>/probe_perf.py

# Probe 6 — resolve_target_paths roots calls
# (same run as probe_app_and_roots.py above, second half of its output)

# Probe 8 — AST sweep for async-never-awaits
uv run python - << 'EOF'
import ast, glob
for fn in glob.glob("colgrep_mcp/*.py"):
    tree = ast.parse(open(fn).read(), filename=fn)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            if not any(isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for n in ast.walk(node)):
                print(f"{fn}:{node.lineno}: async def {node.name} never awaits")
EOF
```

## Hand-off Questions

- OV1: is a `contextvars.ContextVar` the right fix, or does the SDK's own
  session/task-group model already guarantee stdio serves at most one
  lifespan per process (in which case this is a documented, accepted
  limitation worth one sentence in `server.py`'s module docstring rather
  than a code change)? This review confirmed the *symptom* empirically but
  did not trace whether any currently-shipped transport/launcher
  configuration in this repo can actually reach the overlapping-session
  state outside a synthetic `asyncio.gather` probe. Either way, is it worth
  doing in this cycle, or filed to the knowledge-transfer report's
  next-cycle items — the leaf ownership table (R01 §Roadmap Recommendation)
  puts `server.py` under the lead, not any of the four merged leaves?
- Should `integrate/docstrings` (already in progress on `task/docstrings`,
  not yet merged) also touch the two `errors.py`/`locks.py` module
  docstrings this review read closely? Both read as legitimate provenance
  notes (`errors.py`: "PI request 2026-09-12, mid-run"; not roadmap-step
  narration), so this review did not flag them, but the docstrings leaf may
  disagree.

## Scope Boundary

This report is observation-only: no file under `server/colgrep_mcp/` or
`server/tests/` was modified. The two detached worktrees this review
created against `main`'s commit (`git worktree add --detach`, never the
branch name `main` itself, which is checked out elsewhere) were both
removed with `git worktree remove` after use. Every throwaway probe script
lives only under this session's scratchpad directory, never in the
repository. Routing OV1 to a `fix(...)` commit, `server.py`'s module
docstring, or the knowledge-transfer report's next-cycle items is the
lead's decision, not this report's to make.
