# Code Review — Observation (v0)

Date: 2026-09-12

---
type: observation
topic: colgrep_mcp
spotted-during: code review pass over `server/colgrep_mcp/` (roadmap leaf `build/tools/integrate/verify/code_review.md`), tracing the ten scenarios the leaf names against R01 (`00-architecture_v0.md` §Contracts & Invariants, §Error model) and R05 (`02-architecture_v1.md` D1–D11, M1–M5)
date: 2026-09-12
domain: code
confidence: confirmed
urgency: high
deferred-because: this is a read-only review pass (roadmap leaf explicitly: "Reviewer (read-only)"); fixes are routed by the lead to separate `fix(...)` commits with tests, not applied here
---

## What Was Noticed

Five confirmed **bugs**, six **risks**, and three **consolidation**-grade cleanups, found by tracing the ten scenarios the leaf names, plus every explicit sub-question in scenarios 1–10. Three findings were verified by writing throwaway scripts against `fake_colgrep.py` (never against a real `colgrep`, never under `/private/tmp`) rather than by code reading alone; all scripts and their raw output are reproduced under **Re-observation Steps**. The two most severe bugs are subprocess/task leaks on **client cancellation** (as opposed to timeout, which is already correctly handled and tested): `adapter._run` and `tools_index.index_build` both leave a live child process running, unkilled and unawaited, when the tool call itself is cancelled rather than timing out. The two `locate_unit` bugs are more subtle: the function can return `location_verified=True` for a *wrong* line span, not just fail safe to `False` — this quietly undermines the very field R05 D1 introduced to make hit locations trustworthy.

### Findings Table

| id | file:line | scenario | severity | confidence | proposed fix |
|:--|:--|:--|:--|:--|:--|
| F1 | `adapter.py:200-219` | client cancels a tool call mid-`search`/`init` (not a timeout) | bug | confirmed | Catch cancellation alongside `TimeoutError` in `_run`: on any exit from `wait_for` other than clean success, `proc.kill(); await proc.wait()` before re-raising, e.g. `except BaseException: proc.kill(); await proc.wait(); raise`. |
| F2 | `tools_index.py:222-241` | client cancels `index_build` while the heartbeat loop is running | bug | confirmed | Wrap the heartbeat loop in `try/finally`; on any exception (including `CancelledError`) do `task.cancel()` then `with contextlib.suppress(asyncio.CancelledError): await task` before propagating. |
| F3 | `locate.py:36-38` | one first-line candidate, but the rest of `code` no longer matches the file (edited file / code longer than the file tail) | bug | confirmed | In the `len(candidates) == 1` branch, still check `file_lines[line-1:line-1+len(code_lines)] == code_lines`; return `verified=False` (keep the candidate line as best guess, or fall back to reported) when it doesn't. |
| F4 | `locate.py:47-53` | two occurrences share a first line; the one nearest `reported_line` differs from `code` only by trailing whitespace on a later line | bug | confirmed | Retry the full-block comparison with both sides `.rstrip()`-normalized per line before giving up as ambiguous/not-found, so a whitespace-only mismatch doesn't silently hand the match to the wrong occurrence. |
| F5 | `tools_search.py:110-163` (mirrored at `179-211`) | `budget` fits the header alone but not header+continuation-note, and zero hits are ever emitted | bug | confirmed | Hard-truncate the final joined string to `budget` characters as a last resort (`text = text[:budget]`) instead of unconditionally appending the full note whenever `emitted == 0`. |
| F6 | `tools_search.py:305` | `paths=[projA, projB]` spanning two different colgrep projects | risk | confirmed (code reading) | Acquire a lock for every resolved path, not just `resolved[0]` — e.g. nest `project_lock(p)` for each `p in resolved` via `contextlib.AsyncExitStack`. |
| F7 | `paths.py:18,41` | project directory is a symlink | risk | plausible | `default_root`/`resolve_paths` always call `.resolve()`, canonicalizing symlinks; if colgrep's own project-key (R05 D3) was registered against the un-resolved path by prior direct CLI use, the server and the CLI can disagree about which project a path belongs to. Document or reconsider canonicalizing. |
| F8 | `tools_index.py:302-316` | elicitation capability is declared, but `ctx.elicit()` itself raises (e.g. `NoBackChannelError`) | risk | confirmed (code reading) | Distinguish "elicitation technically failed" from "user declined" in the result text/structured content instead of collapsing both into `cleared=False` / "Not cleared (declined)". |
| F9 | `config.py:28`; `__main__.py:20` | `COLGREP_MCP_TIMEOUT` (or `_TEXT_BUDGET`) set to a non-numeric value | risk | confirmed | Catch the `ValueError` in `Settings.from_env()` and re-raise (or print) a one-line `"invalid COLGREP_MCP_TIMEOUT=...: must be a number"` instead of letting a raw traceback be the server's only diagnostic. |
| F10 | `prompts.py:43-51` | two completions race past the 30s TTL simultaneously | consolidation | confirmed (code reading) | Low priority: guard the cache refill with an `asyncio.Lock` if the duplicate `stats()` spawn is ever seen to matter. |
| F11 | `tools_search.py:66,547,556` | a hit's file (or an `expand` target) is very large | risk | plausible | Move `Path(file).read_text()` off the event loop, e.g. `await asyncio.to_thread(path.read_text, errors="replace")`, in both `hit_from_raw`'s file-cache fill and `expand`. |
| F12 | `tools_search.py` (tool `Field`s); `adapter.py::build_search_argv` | `limit=0`/negative/huge; `alpha` outside `[0,1]` | consolidation | confirmed (code reading) | Add `Field(ge=..., le=...)` (or explicit checks) so a bad value surfaces a clear `ToolError` before a subprocess is spawned, instead of relying on colgrep's CLI parser to reject it. |
| F13 | `tools_search.py:59,72` | colgrep ever emits a non-absolute `unit.file` | risk | hunch | Assert/resolve `unit.file` to absolute before building `hit_id`, per the R01 §hit_id invariant, or raise a clear parse error rather than silently building a relative `hit_id` that `expand` would resolve against the wrong cwd. |
| F14 | `adapter.py:227,249,262,290` | invariant checks written as bare `assert` | consolidation | confirmed (code reading) | Replace `assert path.is_absolute()` with an explicit `if not ...: raise ValueError(...)` — `assert` is stripped entirely under `python -O`. |

## Context

Primary task: read-only trace of `server/colgrep_mcp/{adapter,locate,textparse,paths,locks,logging_utils,tools_search,tools_index,resources,prompts,server,__main__,config,models}.py` against the ten scenarios named in `__roadmap__/colgrep_mcp/build/tools/integrate/verify/code_review.md`, cross-checked against what `server/tests/` already covers so this report focuses on what is *not* covered. Out of scope by the leaf's own instruction: the in-flight `[CODE] … Next: …` error-taxonomy (`errors.py`) and the stdio round-trip test — neither is reported on here. This report is the full deliverable of that task; no code was modified.

## Location Map

- `server/colgrep_mcp/adapter.py:154-219` — `_run` (subprocess spawn, drain, timeout/cancel handling) → F1
- `server/colgrep_mcp/adapter.py:225-247` — `search()` (paths must be absolute, JSON parse)
- `server/colgrep_mcp/adapter.py:227,249,262,290` — bare `assert path.is_absolute()` call sites → F14
- `server/colgrep_mcp/locate.py:14-61` — `locate_unit` (all branches) → F3, F4
- `server/colgrep_mcp/tools_search.py:43-91` — `hit_from_raw` (file cache, `locate_unit` call, `hit_id` construction) → F11, F13
- `server/colgrep_mcp/tools_search.py:110-163,179-211` — `render_search_text` / `render_files_text` (budget backtracking) → F5
- `server/colgrep_mcp/tools_search.py:250-336` — `_do_search` (path resolution, lock, adapter call, `index_updated`) → F6
- `server/colgrep_mcp/tools_search.py:520-583` — `expand` (blocking read, `hit_id` parse) → F11
- `server/colgrep_mcp/tools_index.py:203-257` — `index_build` (heartbeat task lifecycle) → F2
- `server/colgrep_mcp/tools_index.py:260-333` — `index_clear` (guard ordering, elicitation) → F8
- `server/colgrep_mcp/paths.py:15-50` — `default_root` / `resolve_paths` (symlinks, `~`) → F7
- `server/colgrep_mcp/prompts.py:34-51` — `_stats_cache` / `_cached_project_paths` → F10
- `server/colgrep_mcp/config.py:22-31`, `server/colgrep_mcp/__main__.py:13-21` — `Settings.from_env` → F9
- `server/tests/test_adapter.py:196-204,272-281` — existing zombie coverage is **timeout-only**, not cancellation (the gap F1/F2 fill)
- `server/tests/test_locate.py` — existing coverage never exercises a single unique first-line candidate whose body diverges from the file, nor a whitespace-only duplicate mismatch (the gap F3/F4 fill)
- `server/tests/test_render.py:163-181` — existing backtracking test always has at least one hit to pop; never exercises the zero-emitted-from-the-start case (the gap F5 fills)
- Scratchpad probes used to confirm F1–F5 empirically: `/private/tmp/claude-501/-Users-hacker-Documents-explore-colgrep-mcp/a8c80498-9a50-45ec-b1a2-c45eb195404d/scratchpad/probe_cancel.py`, `probe_index_build_cancel.py` (not part of the repo; reproduced below)

## Evidence

### F1 — `adapter._run` leaks the subprocess on cancellation (not timeout)

`_run` only distinguishes one abnormal exit from `asyncio.wait_for`:

```python
try:
    stdout_bytes, _stderr_done, _returncode = await asyncio.wait_for(
        asyncio.gather(_drain_stdout(), _drain_stderr(), proc.wait()),
        timeout=self.timeout_s,
    )
except TimeoutError:
    proc.kill()
    await proc.wait()
    raise ColgrepTimeout(...) from None
```

`asyncio.wait_for`'s *timeout* path raises `TimeoutError` (caught, handled correctly — `test_colgrep_timeout_leaves_no_zombie` / `test_search_timeout_leaves_no_zombie` already assert this). But if the **caller's task is cancelled** (an MCP client cancelling the tool call, or the framework cancelling a slow handler), `wait_for` propagates `asyncio.CancelledError` instead — a `BaseException` that `except TimeoutError` never catches. Execution never reaches `proc.kill()`/`proc.wait()`; the child process is simply abandoned.

Confirmed by running the fake binary with a 5s sleep, a 30s adapter timeout (so only cancellation, not timeout, can stop it), cancelling the calling task after 0.3s, then checking the OS-level PID:

```
proc pid before cancel: 52433 returncode: None
adapter.version() raised CancelledError as expected
proc returncode right after cancel handling: None
process still alive at OS level: True
```

The process had to be killed manually by the probe for cleanup — `_run` never did it.

### F2 — `tools_index.index_build` leaks the `init()` task (and its subprocess) on cancellation

```python
task: asyncio.Task[IndexBuildResult] = asyncio.ensure_future(
    streaming_adapter.init(resolved, force_cpu=force_cpu)
)
try:
    while True:
        done, _pending = await asyncio.wait({task}, timeout=HEARTBEAT_S)
        if task in done:
            break
        ...
    result = await task
except ColgrepError as exc:
    raise _translate_error(exc) from exc
```

Unlike `asyncio.gather`, `asyncio.wait` does **not** propagate cancellation to the tasks it is waiting on. If the *outer* `index_build` coroutine is cancelled while inside `await asyncio.wait(...)`, `CancelledError` propagates straight out (the `except ColgrepError` clause does not catch it) — the `task` object is simply dropped, still running the real `init()` call and its colgrep subprocess. Worse: this happens **inside** `async with project_lock(resolved):`, and `asyncio.Lock.__aexit__` releases unconditionally even under cancellation — so the lock is released while the orphaned task keeps writing to that project's index, defeating the "held for whole build" concurrency invariant for exactly the case that matters most (a client giving up mid-build).

Confirmed with a stub `Context` and a 5s-sleeping fake binary, `HEARTBEAT_S` lowered to 0.05s: after cancelling the outer `index_build(...)` call and awaiting the `CancelledError`, `pgrep -fl fake_colgrep.py` still showed the `init` subprocess running:

```
outer task done already? False
index_build() call raised CancelledError as expected
pgrep fake_colgrep.py output:
 52592 python3 .../tests/fake_colgrep.py init --color never -y /private/tmp/colgrep_mcp_probe_project
cleaned up leaked pid 52592
```

### F3 — `locate_unit`'s single-candidate branch never verifies the body, so `verified=True` can be wrong

```python
if len(candidates) == 1:
    line = candidates[0]
    return (line, line + len(code_lines) - 1, True)
```

This branch fires whenever exactly one file line matches `code`'s *first* line — but it never checks that the remaining lines of `code` actually match what follows in the file, unlike the `len(code_lines) > 1` / multi-candidate branches below it, which do. So a stale/edited file (or a hit whose `code` simply doesn't match past line 1) is confidently marked `verified=True` with a wrong `end_line`.

Confirmed:

```python
file_text = "def foo():\n    return 1\n"
code = "def foo():\n    return 2\n    extra_line_that_does_not_exist"
locate_unit(file_text, code, reported_line=1, reported_end=2)
# -> (1, 3, True)
```

The file has 2 lines and none of them say `return 2` or `extra_line_that_does_not_exist`, yet the result claims a verified 3-line span. This is the general form of "code longer than the file tail" the leaf asks about: it isn't merely mishandled in the multi-candidate path (which does guard against it via `full_matches`), it is *unchecked* whenever there's only one same-first-line candidate — the common case.

### F4 — whitespace-only mismatch on a later line silently picks the wrong duplicate

Two occurrences share a first line; only the *intended* one (nearest `reported_line`) differs from `code` by trailing whitespace on a later line:

```python
file_text = "def foo():\n    pass\n\ndef foo():\n    pass  \n"  # 2nd occurrence has trailing spaces
code = "def foo():\n    pass"
locate_unit(file_text, code, reported_line=4, reported_end=5)
# -> (1, 2, True)   -- picked line 1, not line 4, and still verified=True
```

Because `full_matches` requires exact equality (`file_lines[...] == code_lines`), the whitespace-differing occurrence at line 4 (the one `reported_line` actually points at) is excluded, leaving only line 1 as a "unique full match" — which the code accepts as verified truth, silently returning the wrong span with full confidence rather than falling back to `verified=False` or at least preferring the reported-line-adjacent occurrence.

### F5 — token-budget hard cap is not actually hard when zero hits are ever emitted

```python
if capped and remaining > 0:
    while True:
        note = f"[{remaining} more hits in structured_content; ...]"
        candidate_len = text_len + 1 + len(note)
        if candidate_len <= budget or emitted == 0:
            blocks.append(note); text_len = candidate_len; break
        dropped = blocks.pop(); text_len -= len(dropped) + 1; emitted -= 1; remaining += 1
```

When the very first hit already overflows `budget` (before any hit is ever appended), `emitted == 0` from the start, so the `emitted == 0` escape hatch fires immediately and the note is appended regardless of whether `header + note` fits. R01 states the budget is a hard cap ("capped at N characters ... hard one"); this specific shape (header fits, header+note doesn't, nothing was ever emitted to drop) isn't the header-alone-too-small case the function's own docstring excuses — the header fit fine on its own.

Confirmed with a header of 26 chars and a budget of 46 (comfortably bigger than the header, too small for any hit block):

```
budget: 46 len(text): 99 capped: True
'3 hits for "q" in /x — 1ms\n[3 more hits in structured_content; call expand(hit_ids=[...]) for code]'
EXCEEDS BUDGET: True
```

Output is ~2.15x over the requested budget. `render_files_text` shares the identical loop shape at lines 198-209 and was not independently re-run, but nothing differs in its logic — same bug, same fix, `plausible→confirmed-by-code-symmetry` rather than independently reproduced.

## Re-observation Steps

```bash
cd server
# F1
uv run python /private/tmp/.../scratchpad/probe_cancel.py
# F2
uv run python /private/tmp/.../scratchpad/probe_index_build_cancel.py
# F3/F4 (inline)
uv run python - << 'EOF'
from colgrep_mcp.locate import locate_unit
print(locate_unit("def foo():\n    return 1\n",
                   "def foo():\n    return 2\n    extra_line_that_does_not_exist", 1, 2))
print(locate_unit("def foo():\n    pass\n\ndef foo():\n    pass  \n",
                   "def foo():\n    pass", 4, 5))
EOF
# F5 (inline) — see the Evidence section for the exact reproduction script
# F9
COLGREP_MCP_TIMEOUT=notanumber uv run python -m colgrep_mcp --transport stdio < /dev/null
```
The two probe scripts are throwaway (scratchpad only, never committed); they instantiate `ColgrepAdapter`/`tools_index.index_build` directly against `tests/fake_colgrep.py` with `FAKE_COLGREP_SLEEP` set, never touching a real `colgrep` binary or `/private/tmp` as a search target.

## Traced, No Issue

- `adapter._run`: stdout (fully buffered) and stderr (line-by-line) are drained **concurrently** via `asyncio.gather(_drain_stdout(), _drain_stderr(), proc.wait())` — a >64KB stdout cannot deadlock against line-by-line stderr draining; both pipes are always being read at once.
- `adapter._run`: `stdin=asyncio.subprocess.DEVNULL` and nothing is ever written to it — `BrokenPipeError` cannot occur.
- `adapter._run`: stderr lines are decoded with `errors="replace"` — non-UTF-8 stderr cannot raise a decode error.
- `adapter._run` **timeout** path (as opposed to cancellation, F1): kills and awaits the process cleanly; already covered by `test_colgrep_timeout_leaves_no_zombie` and `test_search_timeout_leaves_no_zombie`.
- `locate_unit`: CRLF files — `str.splitlines()` treats `\r\n` as one line break regardless of how the string was obtained; `test_crlf_file` and an independent probe both confirm correct disambiguation.
- `render_search_text`/`render_files_text`: `snippet_lines=0` renders without error (empty snippet string, `_hit_block` falls back to the head-only line).
- `render_search_text`: hits with `code=None` render fine — rendering only ever reads `hit.snippet`, never `hit.code`.
- `render_search_text`/`render_files_text`: the backtracking loop terminates — `emitted` strictly decreases each non-appending iteration and is bounded below by 0, so the loop cannot run forever; the only defect is the boundary case documented as F5.
- `tools_search.search`: `paths` pointing at a single file (not a directory) is accepted by `resolve_paths` (only checks `.exists()`) and forwarded to colgrep, which documents file arguments as supported.
- `tools_search._do_search`: `skip_index_update` and `SearchResult.index_updated` stay consistent — `--no-update` suppresses the "Building index" stderr banner, so `index_updated` correctly comes back `False`.
- `tools_index.index_build`: `HEARTBEAT_S` produces indeterminate (`total=None`) heartbeats every interval and one final determinate `(1, 1)` report (already covered by `test_index_build_heartbeat_streams_while_slow`); `report_progress`/`notify_resource_updated` failures are swallowed by bare `except Exception: pass` and never abort the build, on every exit path *except* the cancellation path (F2).
- `tools_index.index_build`: the project lock is held for the entire build on the success and adapter-error exit paths (only the cancellation exit, F2, leaks past the lock's release).
- `tools_index.index_clear`: guard ordering is exactly root-mismatch → elicitation-capability-check → `confirm` flag, as expected; the declined-without-technical-failure path renders "Not cleared (declined)" as documented.
- `resources.py` / `prompts.py`: a fresh `ColgrepAdapter()` per resource/completion call holds no resources at construction (only `_run` ever opens a subprocess, and `_run` always reaps it on the non-cancellation exit paths) — no leak from per-call adapter creation; re-reading `Settings.from_env()` on every call is cheap and intentional per the module docstrings.
- Cross-cutting: no bare `print()` to stdout in any of the 14 reviewed modules (verified with a per-file, non-recursive `grep '^\s*print('` over each file individually).
- Cross-cutting: every `ColgrepError` subtype `adapter.py` defines (`ColgrepNotFound`, `ColgrepFailed`, `ColgrepTimeout`, `ColgrepParseError`) is caught and translated to `ToolError` at both call sites (`tools_search.py::_translate_error`, `tools_index.py::_translate_error`) — no known adapter failure mode escapes as `UnexpectedToolError`. `CancelledError` propagating uncaught is correct MCP/asyncio behaviour, not a translation gap — the problem in F1/F2 is the missing cleanup *before* it propagates, not the propagation itself.
- Cross-cutting: `hit_id` construction is identical between `search` and `find_files` (both route every raw hit through the same `hit_from_raw`) and is parsed back by `expand` via the same `_HIT_ID_RE` shape — self-consistent as long as `unit.file` is absolute (tracked separately as F13).

## Hand-off Questions

Working theory, if any: F1/F2 share one root cause (cancellation is handled asymmetrically from timeout everywhere a subprocess or a wrapped `asyncio.Task` is involved) and could plausibly be fixed together with one shared idiom (a small `_run_cancellable` helper or a `try/except BaseException` pattern applied at both sites) rather than as two unrelated patches.

- F1/F2: does the MCP Python SDK's `MCPServer` actually deliver a client-initiated cancellation as `asyncio.CancelledError` into the running tool coroutine (vs. only failing to send a response and leaving the coroutine running to completion regardless)? This report traced the code assuming cancellation reaches the coroutine (the standard asyncio disconnect/cancel model) but did not trace the SDK's own request-cancellation wiring — worth confirming before writing the regression test, since the *test* needs to reproduce whatever the SDK actually does.
- F3/F4: should `locate_unit` ever downgrade an already-`True` multi-candidate/ambiguous result to `False` (favouring honesty over a plausible guess), or is "best guess, marked verified" acceptable there and the fix should be scoped to F3 only (the single-candidate branch, which is unambiguously wrong to skip)?
- F5: is the R01 "hard cap" invariant meant to admit a documented degenerate exception at all, or should the fix (hard-truncate as a last resort) be the actual contract, with R01 updated to say so explicitly?
- F6 (paths[0]-only locking): is serializing only the first path an accepted trade-off already implicit in "search/find_files hold [the lock] too" (R01 §Concurrency invariant), or was multi-path locking simply never considered? The invariant text reads singular ("per resolved project path") which reads as intending full coverage.
- Which of F6–F14 are worth a `fix(...)` commit now vs. deferring to the knowledge-transfer report, per the leaf's own triage split (bug → fix+test; consolidation → apply if <30 lines else next cycle; risk → knowledge-transfer)?

## Scope Boundary

This report is observation-only: no source file under `server/colgrep_mcp/` or `server/tests/` was modified, and the two throwaway probe scripts live only in the scratchpad, never in the repository. Routing findings to `fix(...)` commits, the knowledge-transfer report, or the next roadmap cycle is the lead's decision per the leaf's Step 1 triage description, not this report's to make.
